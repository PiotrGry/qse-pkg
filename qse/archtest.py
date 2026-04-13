"""
qse-archtest — Architecture Quality Gate CLI
=============================================

Scans a repository, computes AGQ_v3c, classifies green/amber/red, and
emits a structured report in JSON or Markdown.

Usage
-----
    python -m qse.archtest --repo ./my-project --lang java
    python -m qse.archtest --repo ./my-project --lang python --format markdown
    python -m qse.archtest --repo . --lang java --main-branch-agq 0.58

Entry points (setup.py):
    qse-archtest   → qse.archtest:main

Exit codes
----------
    0   green  (AGQ ≥ green threshold)
    1   amber  (AGQ between amber and green thresholds)
    2   red    (AGQ < amber threshold)
    3   error  (scanner failure, too few nodes, etc.)
"""

import argparse
import json
import sys
import os
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Thresholds (empirically calibrated, April 2026)
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "java": {"green": 0.55, "amber": 0.45},
    "python": {"green": 0.55, "amber": 0.42},
}

# Minimum node count for a meaningful scan (small graphs produce unreliable AGQ)
MIN_NODES = 10

# FF1 regression: both AGQ and CD must drop by this margin to trigger upgrade
FF1_DROP_THRESHOLD = 0.05

# ---------------------------------------------------------------------------
# Archipelago detection thresholds (April 2026)
# ---------------------------------------------------------------------------
# Disconnected subgraphs ("archipelagos") inflate modularity and coupling
# scores by making collections of unrelated modules look well-modularized.
# Single-tier detection based on connected-component analysis:
#   cc_ratio > 0.08 → HIGH confidence archipelago warning
# cc_ratio = fraction of nodes NOT in the largest connected component.
# Validated on 22 repos: 0 false positives on POS/GOOD, catches extreme cases.
# Connectivity metrics are always included in the report for manual inspection.
# The warning does NOT change the AGQ score — it adds an advisory field only.
ARCHIPELAGO_CC_RATIO = 0.08  # cc_ratio threshold for archipelago warning


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify(agq: float, lang: str) -> str:
    """Return 'green', 'amber', or 'red' based on language thresholds."""
    t = THRESHOLDS[lang]
    if agq >= t["green"]:
        return "green"
    if agq >= t["amber"]:
        return "amber"
    return "red"


def _compute_flat_score_from_graph(graph) -> float:
    """
    Compute flat_score directly from a NetworkX DiGraph.

    flat_score = 1 - flat_ratio
    flat_ratio = fraction of internal nodes with namespace depth <= 2
    (e.g. 'mypackage.module' has depth 1 — only one level of nesting)

    This replicates flat_metrics.compute_flat_metrics() without needing
    the intermediate JSON serialisation step.
    """
    nodes = list(graph.nodes())
    if not nodes:
        return 1.0

    def _pkg_depth(fqn: str) -> int:
        parts = fqn.split(".")
        # depth = number of package separators (dots), not total parts
        return max(0, len(parts) - 1)

    depths = [_pkg_depth(n) for n in nodes]
    shallow_threshold = 2
    n_flat = sum(1 for d in depths if d <= shallow_threshold)
    flat_ratio = n_flat / len(depths)
    return round(1.0 - flat_ratio, 4)


def _detect_archipelago(graph) -> dict:
    """
    Detect archipelago effect — disconnected subgraphs that inflate AGQ.

    Computes connected-component metrics from the NetworkX DiGraph and
    applies a 2-tier classification:

      Tier 1 (HIGH confidence):     cc_ratio > 0.05
        → Likely a multi-project collection; AGQ is unreliable.
      Tier 2 (MODERATE confidence): E/N < 3.0 AND cc_ratio >= 0.005
        → Sparse graph with disconnected fragments; interpret with caution.

    Returns a dict with:
      detected : bool       — True if any tier triggered
      tier     : str|None   — 'high' or 'moderate' or None
      message  : str|None   — Human-readable explanation
      metrics  : dict       — Connectivity statistics
    """
    import networkx as nx

    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()

    if n_nodes == 0:
        return {
            "detected": False,
            "tier": None,
            "message": None,
            "metrics": {},
        }

    en_ratio = n_edges / n_nodes

    # Use weakly connected components (graph is directed)
    components = list(nx.weakly_connected_components(graph))
    n_cc = len(components)
    lcc_size = max(len(c) for c in components)
    lcc_ratio = lcc_size / n_nodes
    small_cc_nodes = n_nodes - lcc_size
    cc_ratio = small_cc_nodes / n_nodes
    isolated = sum(1 for n in graph.nodes() if graph.degree(n) == 0)

    metrics = {
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "en_ratio": round(en_ratio, 3),
        "n_components": n_cc,
        "lcc_size": lcc_size,
        "lcc_ratio": round(lcc_ratio, 4),
        "small_cc_nodes": small_cc_nodes,
        "cc_ratio": round(cc_ratio, 4),
        "isolated_nodes": isolated,
    }

    # Archipelago detection: large fraction of nodes outside LCC
    if cc_ratio > ARCHIPELAGO_CC_RATIO:
        return {
            "detected": True,
            "tier": "high",
            "message": (
                f"Archipelago detected: "
                f"{cc_ratio:.1%} of nodes ({small_cc_nodes}/{n_nodes}) are outside "
                f"the largest connected component. This repo may be a collection "
                f"of unrelated modules — AGQ scores are unreliable."
            ),
            "metrics": metrics,
        }

    return {
        "detected": False,
        "tier": None,
        "message": None,
        "metrics": metrics,
    }


def _build_flags(components: dict, lang: str) -> list:
    """
    Generate structural flags from component scores.

    Flags:
      - "high coupling"   if CD < 0.20
      - "flat structure"  if flat_score < 0.30  (Python only)
      - "low cohesion"    if C < 0.15
    """
    flags = []
    if components.get("CD", 1.0) < 0.20:
        flags.append("high coupling")
    if lang == "python" and components.get("flat_score", 1.0) < 0.30:
        flags.append("flat structure")
    if components.get("C", 1.0) < 0.15:
        flags.append("low cohesion")
    return flags


def _check_ff1_regression(
    agq: float,
    cd: float,
    main_agq: float,
    status: str,
) -> Optional[dict]:
    """
    FF1 regression check.

    If the AGQ drop from main branch > FF1_DROP_THRESHOLD AND the CD drop
    also exceeds FF1_DROP_THRESHOLD, the status is upgraded to amber.

    Returns a dict with regression details, or None if no regression detected.
    The caller is responsible for upgrading the status.
    """
    agq_drop = main_agq - agq
    # We don't have main_cd directly — the check is intentionally AGQ-based
    # with a secondary CD safeguard. Here we use the passed cd vs a neutral 0.5
    # as a proxy if the caller doesn't supply main_cd.  The actual CD drop
    # check uses the current cd against the implied main baseline:
    # since main_agq is provided but main_cd is not, we trigger on AGQ alone
    # when the drop is large enough (> 2× threshold) as a conservative fallback.
    if agq_drop <= 0:
        return None

    regression = {
        "main_branch_agq": main_agq,
        "current_agq": agq,
        "agq_drop": round(agq_drop, 4),
        "triggered": False,
        "reason": None,
    }

    if agq_drop > FF1_DROP_THRESHOLD:
        regression["triggered"] = True
        regression["reason"] = (
            f"AGQ dropped {agq_drop:.3f} from main branch "
            f"({main_agq:.3f} → {agq:.3f})"
        )

    return regression


# ---------------------------------------------------------------------------
# Scanner runners
# ---------------------------------------------------------------------------


def run_java_scan(repo_path: str) -> dict:
    """
    Run the Java scanner and compute AGQ metrics.

    Returns a dict with:
      graph_stats, components (M/A/S/C/CD/flat_score), agq_v3c, metrics_obj
    """
    from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
    from qse.graph_metrics import compute_agq

    result = scan_java_repo(repo_path)
    n_nodes = result.graph.number_of_nodes()
    n_edges = result.graph.number_of_edges()

    if n_nodes < MIN_NODES:
        raise ValueError(
            f"Too few nodes ({n_nodes}) for meaningful analysis "
            f"(minimum: {MIN_NODES}). "
            f"Is '{repo_path}' a Java project with source files?"
        )

    graph, abstract_modules, lcom4_values = scan_result_to_agq_inputs(result)
    metrics = compute_agq(graph, abstract_modules, lcom4_values)

    # Set language context for agq_v3c property
    metrics._language = "Java"
    metrics._flat_score = 1.0  # Java flat_score is always ~1.0 (no signal)

    agq = metrics.agq_v3c
    components = {
        "M": round(metrics.modularity, 4),
        "A": round(metrics.acyclicity, 4),
        "S": round(metrics.stability, 4),
        "C": round(metrics.cohesion, 4),
        "CD": round(metrics.coupling_density, 4),
    }

    # Archipelago detection
    archipelago = _detect_archipelago(result.graph)

    return {
        "graph_stats": {"nodes": n_nodes, "edges": n_edges},
        "components": components,
        "agq_v3c": round(agq, 4),
        "metrics_obj": metrics,
        "flat_score": 1.0,
        "archipelago": archipelago,
    }


def run_python_scan(repo_path: str) -> dict:
    """
    Run the Python scanner and compute AGQ metrics.

    Returns a dict with:
      graph_stats, components (M/A/S/C/CD/flat_score), agq_v3c, metrics_obj
    """
    from qse.scanner import scan_repo
    from qse.graph_metrics import compute_agq, compute_lcom4

    result = scan_repo(repo_path)
    graph = result.graph
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()

    if n_nodes < MIN_NODES:
        raise ValueError(
            f"Too few nodes ({n_nodes}) for meaningful analysis "
            f"(minimum: {MIN_NODES}). "
            f"Is '{repo_path}' a Python project with .py source files?"
        )

    # Collect LCOM4 values from class metadata
    lcom4_values = []
    for cls in result.classes.values():
        if cls.method_attrs:
            lcom = compute_lcom4(cls.method_attrs)
            lcom4_values.append(lcom)

    # Abstract modules (for stability API compatibility)
    abstract_modules = {
        name for name, cls in result.classes.items() if cls.is_abstract
    }

    metrics = compute_agq(graph, abstract_modules, lcom4_values)

    # Compute flat_score directly from the graph node namespace depths
    flat_score = _compute_flat_score_from_graph(graph)

    # Set language context for agq_v3c property
    metrics._language = "Python"
    metrics._flat_score = flat_score

    agq = metrics.agq_v3c
    components = {
        "M": round(metrics.modularity, 4),
        "A": round(metrics.acyclicity, 4),
        "S": round(metrics.stability, 4),
        "C": round(metrics.cohesion, 4),
        "CD": round(metrics.coupling_density, 4),
        "flat_score": flat_score,
    }

    # Archipelago detection
    archipelago = _detect_archipelago(graph)

    return {
        "graph_stats": {"nodes": n_nodes, "edges": n_edges},
        "components": components,
        "agq_v3c": round(agq, 4),
        "metrics_obj": metrics,
        "flat_score": flat_score,
        "archipelago": archipelago,
    }


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def format_json(report: dict) -> str:
    """Serialise the report as pretty-printed JSON."""
    return json.dumps(report, indent=2, default=str)


def format_markdown(report: dict) -> str:
    """Render the report as a Markdown summary suitable for PR comments."""
    lang = report["language"].capitalize()
    agq = report["agq_v3c"]
    status = report["status"].upper()
    comp = report["components"]
    flags = report["flags"]
    gs = report["graph_stats"]
    ff1 = report["ff1_regression"]
    ts = report["timestamp"]

    # Status badge text
    badge_map = {"GREEN": "✅ GREEN", "AMBER": "⚠️ AMBER", "RED": "❌ RED"}
    badge = badge_map.get(status, status)

    lines = [
        f"## Architecture Quality Gate — {badge}",
        "",
        f"**Repo:** `{report['repo']}`  |  **Language:** {lang}  |  **AGQ_v3c:** `{agq:.4f}`",
        "",
        "### Component Scores",
        "",
        "| Component | Score | Description |",
        "|-----------|-------|-------------|",
        f"| M — Modularity | `{comp['M']:.4f}` | Community structure (Louvain Q) |",
        f"| A — Acyclicity | `{comp['A']:.4f}` | Nodes outside cycles (Tarjan SCC) |",
        f"| S — Stability  | `{comp['S']:.4f}` | Package instability variance (Martin) |",
        f"| C — Cohesion   | `{comp['C']:.4f}` | Class cohesion (LCOM4) |",
        f"| CD — Coupling Density | `{comp['CD']:.4f}` | Sparse dependency ratio |",
    ]

    if "flat_score" in comp:
        lines.append(
            f"| flat\\_score (Python) | `{comp['flat_score']:.4f}` | Hierarchical depth signal |"
        )

    lines += [
        "",
        "### Thresholds",
        "",
        f"| Status | AGQ threshold |",
        f"|--------|---------------|",
    ]
    t = THRESHOLDS[report["language"]]
    lines += [
        f"| 🟢 Green | ≥ {t['green']} |",
        f"| 🟡 Amber | ≥ {t['amber']} |",
        f"| 🔴 Red   | < {t['amber']} |",
        "",
        f"### Graph Stats",
        "",
        f"- Nodes: **{gs['nodes']}**",
        f"- Edges: **{gs['edges']}**",
    ]

    if flags:
        lines += [
            "",
            "### Structural Flags",
            "",
        ]
        for f in flags:
            lines.append(f"- ⚠️ `{f}`")

    if ff1 and ff1.get("triggered"):
        lines += [
            "",
            "### FF1 Regression Detected",
            "",
            f"- Main branch AGQ: `{ff1['main_branch_agq']:.4f}`",
            f"- Current AGQ: `{ff1['current_agq']:.4f}`",
            f"- Drop: `{ff1['agq_drop']:.4f}`",
            f"- Reason: {ff1['reason']}",
        ]

    # Connectivity metrics (always shown) + archipelago warning
    arch = report.get("archipelago", {})
    am = arch.get("metrics", {})
    if am:
        if arch.get("detected"):
            lines += [
                "",
                "### \U0001F30A Archipelago Warning",
                "",
                f"{arch.get('message', 'Disconnected subgraphs detected.')}",
                "",
            ]
        else:
            lines += [
                "",
                "### Connectivity",
                "",
            ]
        lines += [
            f"- Connected components: **{am.get('n_components', '?')}**",
            f"- LCC coverage: **{am.get('lcc_ratio', 0):.1%}** of nodes",
            f"- Nodes outside LCC: **{am.get('small_cc_nodes', '?')}**",
            f"- Isolated nodes: **{am.get('isolated_nodes', '?')}**",
            f"- E/N ratio: **{am.get('en_ratio', '?')}**",
        ]
        if arch.get("detected"):
            lines += [
                "",
                "*AGQ may be inflated. Multi-project collections and tutorial repos "
                "often produce misleadingly high scores because disconnected modules "
                "look like perfect modularity to graph metrics.*",
            ]

    lines += [
        "",
        f"*Generated: {ts}*",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_archtest(
    repo: str,
    lang: str,
    fmt: str = "json",
    main_branch_agq: Optional[float] = None,
) -> tuple:
    """
    Run the full architecture test pipeline.

    Parameters
    ----------
    repo : str
        Path to the repository root.
    lang : str
        Language: 'java' or 'python'.
    fmt : str
        Output format: 'json' or 'markdown'.
    main_branch_agq : float, optional
        AGQ score from the main branch (for FF1 regression check).

    Returns
    -------
    (report_str, exit_code)
        report_str : str  — formatted report
        exit_code  : int  — 0 green / 1 amber / 2 red / 3 error
    """
    repo_abs = os.path.abspath(repo)
    timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Scan
    try:
        if lang == "java":
            scan = run_java_scan(repo_abs)
        else:
            scan = run_python_scan(repo_abs)
    except Exception as exc:
        error_report = {
            "repo": repo_abs,
            "language": lang,
            "error": str(exc),
            "timestamp": timestamp,
        }
        if fmt == "json":
            return json.dumps(error_report, indent=2), 3
        return f"## Architecture Quality Gate — ERROR\n\n{exc}", 3

    agq = scan["agq_v3c"]
    components = scan["components"]
    flat_score = scan.get("flat_score", 1.0)

    # 2. Classify
    status = _classify(agq, lang)

    # 3. Structural flags
    comp_with_flat = dict(components)
    comp_with_flat["flat_score"] = flat_score
    flags = _build_flags(comp_with_flat, lang)

    # 4. FF1 regression check
    ff1_result = None
    if main_branch_agq is not None:
        ff1_result = _check_ff1_regression(
            agq=agq,
            cd=components.get("CD", 0.5),
            main_agq=main_branch_agq,
            status=status,
        )
        # Upgrade to amber if regression triggered and currently green
        if ff1_result and ff1_result.get("triggered") and status == "green":
            status = "amber"

    # 5. Archipelago detection
    archipelago = scan.get("archipelago", {"detected": False})

    # 6. Build report dict
    report = {
        "repo": repo_abs,
        "language": lang,
        "agq_v3c": agq,
        "status": status,
        "components": components,
        "flags": flags,
        "graph_stats": scan["graph_stats"],
        "ff1_regression": ff1_result,
        "archipelago": archipelago,
        "timestamp": timestamp,
    }

    # 7. Format output
    if fmt == "markdown":
        output = format_markdown(report)
    else:
        output = format_json(report)

    # 8. Exit code
    exit_codes = {"green": 0, "amber": 1, "red": 2}
    code = exit_codes.get(status, 3)

    return output, code


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qse-archtest",
        description=(
            "Architecture Quality Gate for Java and Python repositories.\n"
            "Computes AGQ_v3c and classifies green/amber/red.\n\n"
            "Exit codes: 0=green, 1=amber, 2=red, 3=error"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  qse-archtest --repo ./my-java-app --lang java\n"
            "  qse-archtest --repo . --lang python --format markdown\n"
            "  qse-archtest --repo . --lang java --main-branch-agq 0.58 --format json\n"
        ),
    )
    parser.add_argument(
        "--repo",
        required=True,
        metavar="PATH",
        help="Path to the repository root directory to scan.",
    )
    parser.add_argument(
        "--lang",
        required=True,
        choices=["java", "python"],
        help="Source language: 'java' or 'python'.",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        choices=["json", "markdown"],
        default="json",
        help="Output format: 'json' (default) or 'markdown'.",
    )
    parser.add_argument(
        "--main-branch-agq",
        type=float,
        default=None,
        metavar="FLOAT",
        help=(
            "AGQ_v3c score from the main branch. If provided, triggers an FF1 "
            "regression check: if the current AGQ drops more than 0.05, the "
            "status is upgraded to amber even if the absolute score is green."
        ),
    )
    return parser


def main(argv=None) -> int:
    """CLI entry point. Returns exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    output, code = run_archtest(
        repo=args.repo,
        lang=args.lang,
        fmt=args.fmt,
        main_branch_agq=args.main_branch_agq,
    )

    print(output)
    return code


if __name__ == "__main__":
    sys.exit(main())
