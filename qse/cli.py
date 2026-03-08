"""QSE command-line interface."""

import argparse
import json
import sys

import numpy as np

from qse.presets.ddd.config import QSEConfig
from qse.presets.ddd.pipeline import analyze_repo
from qse.presets.ddd.report import format_json, format_table
from qse.trl4_gate import TRL4Rules, run_trl4_gate

DEFECT_TYPES = ["anemic_entity", "fat_service", "zombie_entity", "layer_violation"]


def _build_config(args) -> QSEConfig:
    config = QSEConfig.from_file(args.config) if args.config else QSEConfig()
    if args.no_trace:
        config.enable_trace = False
    if hasattr(args, "weights") and args.weights:
        vals = [float(x) for x in args.weights.split(",")]
        if len(vals) != 5:
            print("Error: --weights requires exactly 5 values", file=sys.stderr)
            sys.exit(1)
        config.weights = np.array(vals)
    return config


def _load_graph_json(path: str):
    """Load dependency graph from JSON.

    Expected format:
        {"nodes": ["mod_a", "mod_b", ...],
         "edges": [["mod_a", "mod_b"], ...],
         "abstract_modules": ["mod_b"],       // optional
         "classes_lcom4": [1, 2, 1]}          // optional
    """
    import networkx as nx
    with open(path) as f:
        data = json.load(f)
    G = nx.DiGraph()
    for node in data.get("nodes", []):
        G.add_node(node)
    for src, tgt in data.get("edges", []):
        G.add_edge(src, tgt)
    abstract = set(data.get("abstract_modules", []))
    lcom4 = data.get("classes_lcom4", [])
    return G, abstract, lcom4


def _detect_repo_language(path: str) -> str:
    """Detect primary language of a repository by file count."""
    import os
    counts = {"py": 0, "java": 0, "go": 0}
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'target']
        for f in files:
            ext = f.rsplit('.', 1)[-1] if '.' in f else ''
            if ext in counts:
                counts[ext] += 1
        if sum(counts.values()) > 100:
            break
    return max(counts, key=counts.get) if any(counts.values()) else "py"


def _run_agq(args) -> None:
    """Execute the language-agnostic AGQ gate.

    Auto-detects language: Python uses scanner.py, Java/Go use Rust qse-core.
    """
    from qse.graph_metrics import compute_agq

    if args.graph:
        G, abstract, lcom4 = _load_graph_json(args.graph)
        metrics = compute_agq(G, abstract_modules=set(abstract), classes_lcom4=lcom4)
    else:
        # Auto-detect language
        lang = _detect_repo_language(args.path)

        if lang in ("java", "go"):
            # Use Rust scanner for Java/Go
            try:
                from _qse_core import scan_and_compute_agq
                r = scan_and_compute_agq(args.path)
                from qse.graph_metrics import AGQMetrics
                metrics = AGQMetrics(
                    modularity=r["modularity"],
                    acyclicity=r["acyclicity"],
                    stability=r["stability"],
                    cohesion=r["cohesion"],
                )
                agq = r["agq_score"]

                result = {
                    "gate": "PASS",
                    "agq_score": round(agq, 4),
                    "threshold": args.threshold,
                    "language": r["language"],
                    "metrics": {k: round(r[k], 4) for k in
                                ["modularity","acyclicity","stability","cohesion"]},
                    "graph": {"nodes": r["nodes"], "edges": r["edges"]},
                    "failures": [],
                }
                if agq < args.threshold:
                    result["gate"] = "FAIL"
                    result["failures"].append(
                        f"agq_score={agq:.4f} below threshold {args.threshold:.2f}")

                if args.output_json:
                    with open(args.output_json, "w") as f:
                        json.dump(result, f, indent=2)

                if result["failures"]:
                    print("AGQ GATE FAIL", file=sys.stderr)
                    for fail in result["failures"]:
                        print(f"  - {fail}", file=sys.stderr)
                    sys.exit(1)

                try:
                    from qse.agq_enhanced import compute_agq_enhanced
                    lang_map = {"Java": "Java", "Go": "Go", "Python": "Python"}
                    enh = compute_agq_enhanced(
                        agq, metrics.modularity, metrics.acyclicity,
                        metrics.stability, metrics.cohesion,
                        r["nodes"], lang_map.get(r["language"], "Python"))
                    fp_str = f"  [{enh.fingerprint}]"
                    z_str = f"  z={enh.agq_z:+.2f} ({enh.agq_percentile}%ile)"
                    cyc_str = f"  cycles={enh.cycle_severity['severity_level']}"
                except Exception:
                    fp_str = z_str = cyc_str = ""

                print(f"AGQ GATE PASS  agq={agq:.4f}  "
                      f"M={metrics.modularity:.2f} A={metrics.acyclicity:.2f} "
                      f"St={metrics.stability:.2f} Co={metrics.cohesion:.2f}  "
                      f"lang={r['language']}{fp_str}{z_str}{cyc_str}")
                sys.exit(0)
            except ImportError:
                print(f"[warn] Rust qse-core not available, falling back to Python scanner",
                      file=sys.stderr)

        # Python scanner (default)
        from qse.scanner import scan_repo
        from qse.graph_metrics import compute_lcom4 as _compute_lcom4
        analysis = scan_repo(args.path)
        G = analysis.graph
        abstract = {c.name for c in analysis.classes.values() if c.is_abstract}
        lcom4 = [
            _compute_lcom4(c.method_attrs)
            for c in analysis.classes.values()
            if c.method_attrs
        ]

    weights = None
    if hasattr(args, "agq_weights") and args.agq_weights:
        import numpy as np
        vals = [float(x) for x in args.agq_weights.split(",")]
        if len(vals) != 4:
            print("Error: --weights requires exactly 4 values (mod,acy,stab,coh)",
                  file=sys.stderr)
            sys.exit(1)
        total = sum(vals)
        weights = tuple(v / total for v in vals)  # normalize to sum=1

    metrics = compute_agq(G, abstract_modules=abstract, classes_lcom4=lcom4,
                          weights=weights if weights else (0.25, 0.25, 0.25, 0.25))
    agq = metrics.agq_score

    failures = []
    if agq < args.threshold:
        failures.append(f"agq_score={agq:.4f} below threshold {args.threshold:.2f}")

    # Constraint checking (policy-as-a-service)
    constraint_score = None
    constraint_violations = []
    if args.constraints:
        from qse.trl4_gate import check_constraints_graph, compute_constraint_score
        with open(args.constraints) as f:
            constraints_data = json.load(f)
        constraints = (constraints_data if isinstance(constraints_data, list)
                       else constraints_data.get("constraints", []))
        constraint_violations = check_constraints_graph(G, constraints)
        constraint_score = compute_constraint_score(G, constraint_violations)
        min_cs = args.min_constraint_score
        if constraint_score < min_cs:
            failures.append(
                f"constraint_score={constraint_score:.4f} below minimum {min_cs:.2f}"
            )

    result = {
        "gate": "PASS" if not failures else "FAIL",
        "agq_score": round(agq, 4),
        "threshold": args.threshold,
        "metrics": {
            "modularity": round(metrics.modularity, 4),
            "acyclicity": round(metrics.acyclicity, 4),
            "stability": round(metrics.stability, 4),
            "cohesion": round(metrics.cohesion, 4),
        },
        "graph": {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
        },
        "failures": failures,
    }
    if constraint_score is not None:
        result["constraint_score"] = round(constraint_score, 4)
        result["constraint_violations"] = [
            {"rule": v["rule"], "source": v["source"], "target": v["target"]}
            for v in constraint_violations
        ]

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(result, f, indent=2)

    if failures:
        print("AGQ GATE FAIL", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)

    # Enhanced metrics
    try:
        from qse.agq_enhanced import compute_agq_enhanced
        detected_lang = _detect_repo_language(args.path)
        lang_map = {"java": "Java", "go": "Go", "py": "Python"}
        lang_name = lang_map.get(detected_lang, "Python")
        enh = compute_agq_enhanced(agq, metrics.modularity, metrics.acyclicity,
                                   metrics.stability, metrics.cohesion,
                                   G.number_of_nodes(), lang_name)
        fp_str = f"  [{enh.fingerprint}]"
        z_str = f"  z={enh.agq_z:+.2f} ({enh.agq_percentile}%ile)"
        cyc_str = f"  cycles={enh.cycle_severity['severity_level']}"
    except Exception:
        fp_str = z_str = cyc_str = ""

    parts = [f"AGQ GATE PASS  agq={agq:.4f}  "
             f"M={metrics.modularity:.2f} A={metrics.acyclicity:.2f} "
             f"St={metrics.stability:.2f} Co={metrics.cohesion:.2f}"
             f"{fp_str}{z_str}{cyc_str}"]
    if constraint_score is not None:
        parts.append(f"  constraints={constraint_score:.2f}")
    print("".join(parts))
    sys.exit(0)


def _run_discover(args) -> None:
    """Auto-discover architectural boundaries and propose constraints."""
    from qse.discover import discover_policies

    if args.graph:
        G, _, _ = _load_graph_json(args.graph)
    else:
        from qse.scanner import scan_repo
        analysis = scan_repo(args.path)
        G = analysis.graph

    report = discover_policies(G, min_confidence=args.min_confidence)

    # Console output
    print(f"Clusters found: {len(report.clusters)}")
    for c in report.clusters:
        print(f"  {c['label']} ({c['size']} modules)")

    print(f"\nProposed rules: {len(report.proposed_rules)}")
    for r in report.proposed_rules:
        marker = "+" if r.confidence >= 0.7 else "?"
        print(f"  [{marker} {r.confidence:.0%}] forbidden: {r.from_pattern} -> {r.to_pattern}")
        print(f"         {r.rationale}")

    # JSON outputs
    if args.output_json:
        with open(args.output_json, "w") as f:
            f.write(report.to_json())
        print(f"\nFull report written to {args.output_json}")

    if args.output_constraints:
        constraints = [r.to_constraint() for r in report.proposed_rules
                       if r.confidence >= 0.7]
        with open(args.output_constraints, "w") as f:
            json.dump(constraints, f, indent=2)
        print(f"Constraints ({len(constraints)} rules) written to {args.output_constraints}")
        print(f"Use with: qse agq --constraints {args.output_constraints}")


def main():
    parser = argparse.ArgumentParser(
        prog="qse",
        description="QSE — Quality Score Engine for architecture validation",
    )
    sub = parser.add_subparsers(dest="command")

    # ── qse scan ──────────────────────────────────────────────────────────────
    scan = sub.add_parser("scan", help="Analyze a repository and print report")
    scan.add_argument("path", help="Path to the repository root")
    scan.add_argument("--format", choices=["table", "json"], default="table")
    scan.add_argument("--output-json", type=str, default=None, metavar="FILE")
    scan.add_argument("--no-trace", action="store_true")
    scan.add_argument("--weights", type=str, default=None)
    scan.add_argument("--config", type=str, default=None)

    # ── qse gate ──────────────────────────────────────────────────────────────
    gate = sub.add_parser("gate", help="Run QSE and exit non-zero if gate fails")
    gate.add_argument("path", help="Path to the repository root")
    gate.add_argument("--threshold", type=float, default=0.80, metavar="N",
                      help="Minimum QSE total score (default: 0.80)")
    gate.add_argument("--fail-on-defects", type=str, default=None, metavar="LIST",
                      help=f"Comma-separated defect types that must be zero. "
                           f"Available: {', '.join(DEFECT_TYPES)}")
    gate.add_argument("--output-json", type=str, default=None, metavar="FILE")
    gate.add_argument("--no-trace", action="store_true")
    gate.add_argument("--config", type=str, default=None)

    # ── qse trl4 ──────────────────────────────────────────────────────────────
    trl4 = sub.add_parser("trl4", help="Run TRL4 gate (QSE + constraints + ratchet)")
    trl4.add_argument("path", help="Path to the repository root")
    trl4.add_argument("--config", type=str, default=None, help="JSON config path")
    trl4.add_argument("--output-json", type=str, default=None, metavar="FILE")
    trl4.add_argument("--threshold", type=float, default=None,
                      help="Override QSE threshold from config/default")
    trl4.add_argument("--min-constraint-score", type=float, default=None,
                      help="Override minimum constraints score from config/default")
    trl4.add_argument("--ratchet", action="store_true", help="Force enable ratchet")
    trl4.add_argument("--no-ratchet", action="store_true", help="Force disable ratchet")
    trl4.add_argument("--baseline-file", type=str, default=None,
                      help="Ratchet baseline JSON file path")
    trl4.add_argument("--no-trace", action="store_true")

    # ── qse agq ──────────────────────────────────────────────────────────────
    agq = sub.add_parser("agq",
                         help="Language-agnostic AGQ gate (graph metrics + optional constraints)")
    agq.add_argument("path", nargs="?", default=".",
                     help="Path to repo root (used for Python auto-scan if --graph not given)")
    agq.add_argument("--graph", type=str, default=None, metavar="FILE",
                     help="JSON dependency graph file (language-agnostic input)")
    agq.add_argument("--threshold", type=float, default=0.70, metavar="N",
                     help="Minimum AGQ score (default: 0.70)")
    agq.add_argument("--constraints", type=str, default=None, metavar="FILE",
                     help="JSON file with forbidden-edge constraints (policy-as-a-service)")
    agq.add_argument("--min-constraint-score", type=float, default=0.95, metavar="N",
                     help="Minimum constraint score (default: 0.95)")
    agq.add_argument("--output-json", type=str, default=None, metavar="FILE")
    agq.add_argument("--weights", dest="agq_weights", type=str, default=None,
                     metavar="W1,W2,W3,W4",
                     help="Custom weights for mod,acy,stab,coh (auto-normalized, "
                          "e.g. --weights 0,0.73,0.05,0.17 for churn-calibrated)")

    # ── qse discover ────────────────────────────────────────────────────────
    disc = sub.add_parser("discover",
                          help="Auto-discover architectural boundaries and propose constraints")
    disc.add_argument("path", nargs="?", default=".",
                      help="Path to repo root (Python auto-scan if --graph not given)")
    disc.add_argument("--graph", type=str, default=None, metavar="FILE",
                      help="JSON dependency graph file (language-agnostic input)")
    disc.add_argument("--min-confidence", type=float, default=0.5, metavar="N",
                      help="Minimum confidence for proposed rules (default: 0.5)")
    disc.add_argument("--output-json", type=str, default=None, metavar="FILE",
                      help="Write full discovery report to JSON file")
    disc.add_argument("--output-constraints", type=str, default=None, metavar="FILE",
                      help="Write high-confidence constraints to JSON file (ready for --constraints)")

    args = parser.parse_args()

    if args.command == "discover":
        _run_discover(args)
        return

    if args.command == "agq":
        _run_agq(args)
        return

    if args.command not in ("scan", "gate", "trl4"):
        parser.print_help()
        sys.exit(1)

    config = _build_config(args)
    if args.command == "trl4":
        rules = TRL4Rules.from_file(args.config) if args.config else TRL4Rules()
        if args.threshold is not None:
            rules.threshold = args.threshold
        if args.min_constraint_score is not None:
            rules.min_constraint_score = args.min_constraint_score
        if args.ratchet:
            rules.ratchet_enabled = True
        if args.no_ratchet:
            rules.ratchet_enabled = False
        if args.baseline_file:
            rules.ratchet_baseline_file = args.baseline_file

        result = run_trl4_gate(args.path, rules=rules, qse_config=config)
        payload = result.to_dict()

        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump(payload, f, indent=2)

        if result.passed:
            print(f"TRL4 GATE PASS  qse_total={result.qse_total:.4f}  constraint_score={result.constraint_score:.4f}")
            sys.exit(0)

        print("TRL4 GATE FAIL", file=sys.stderr)
        for failure in result.failures:
            print(f"  - {failure}", file=sys.stderr)
        sys.exit(1)

    report = analyze_repo(args.path, config)

    # ── scan ──────────────────────────────────────────────────────────────────
    if args.command == "scan":
        output = format_json(report) if args.format == "json" else format_table(report)
        print(output)
        if args.output_json:
            with open(args.output_json, "w") as f:
                f.write(format_json(report))
        sys.exit(0)

    # ── gate ──────────────────────────────────────────────────────────────────
    failures = []
    qse_total = report.qse_total

    if qse_total < args.threshold:
        failures.append(f"qse_total={qse_total:.4f} below threshold {args.threshold:.2f}")

    if args.fail_on_defects:
        for dtype in args.fail_on_defects.split(","):
            dtype = dtype.strip()
            count = len(report.defects.get(dtype, set()))
            if count > 0:
                files = sorted(report.defects[dtype])
                failures.append(f"{dtype}: {count} instance(s) — {', '.join(files)}")

    result = {
        "gate":       "PASS" if not failures else "FAIL",
        "qse_total":  round(qse_total, 4),
        "threshold":  args.threshold,
        "failures":   failures,
        "report":     report.to_dict(),
    }

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(result, f, indent=2)

    if failures:
        print("QSE GATE FAIL", file=sys.stderr)
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        sys.exit(1)

    print(f"QSE GATE PASS  qse_total={qse_total:.4f}")
    sys.exit(0)


if __name__ == "__main__":
    main()
