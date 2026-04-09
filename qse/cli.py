"""QSE command-line interface.

Commands:
    qse agq       - AGQ gate (architecture graph quality)
    qse discover  - auto-discover architectural boundaries
"""

import argparse
import json
import re
import sys
from fnmatch import translate as fnmatch_translate
from typing import List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Constraint checking (formerly in trl4_gate.py)
# ---------------------------------------------------------------------------

def _root_prefix(pattern: str) -> Optional[str]:
    """Return first path segment if no wildcard is present there."""
    clean = pattern.strip("/")
    if not clean:
        return None
    first = clean.split("/", 1)[0]
    if any(ch in first for ch in "*?[]"):
        return None
    return first


def check_constraints_graph(graph, constraints: Sequence[dict]) -> List[dict]:
    """Detect forbidden-edge violations on a module dependency graph."""
    edge_rows = []
    by_root: dict[str, list[Tuple[str, str, str, str]]] = {}
    for src, tgt in graph.edges():
        src_path = src.replace(".", "/")
        tgt_path = tgt.replace(".", "/")
        row = (src, tgt, src_path, tgt_path)
        edge_rows.append(row)
        root = src_path.split("/", 1)[0]
        by_root.setdefault(root, []).append(row)

    compiled = []
    for rule in constraints:
        if rule.get("type") != "forbidden":
            continue
        from_pat = rule["from"]
        to_pat = rule["to"]
        compiled.append(
            (
                rule,
                re.compile(fnmatch_translate(from_pat)),
                re.compile(fnmatch_translate(to_pat)),
                _root_prefix(from_pat),
            )
        )

    violations: List[dict] = []
    for rule, from_re, to_re, root_prefix in compiled:
        candidates = by_root.get(root_prefix, []) if root_prefix is not None else edge_rows
        for src, tgt, src_path, tgt_path in candidates:
            if from_re.fullmatch(src_path) and to_re.fullmatch(tgt_path):
                violations.append({"rule": rule, "source": src, "target": tgt})
    return violations


def compute_constraint_score(graph, violations: Sequence[dict]) -> float:
    total_edges = graph.number_of_edges()
    if total_edges == 0:
        return 1.0
    return max(0.0, 1.0 - (len(violations) / total_edges))


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------

def _load_graph_json(path: str):
    """Load dependency graph from JSON file."""
    import networkx as nx
    with open(path) as f:
        data = json.load(f)
    G = nx.DiGraph()
    for node in data.get("nodes", []):
        if isinstance(node, dict):
            G.add_node(node["id"], internal=node.get("internal", True))
        else:
            G.add_node(node)
    for src, tgt in data.get("edges", []):
        G.add_edge(src, tgt)
    abstract = set(data.get("abstract_modules", []))
    lcom4 = data.get("classes_lcom4", [])
    return G, abstract, lcom4


def _scan_repo(path: str):
    """Scan repository using Rust scanner. Returns (result_dict, AGQMetrics, agq_score)."""
    from _qse_core import scan_and_compute_agq
    from qse.graph_metrics import AGQMetrics
    r = scan_and_compute_agq(path)
    metrics = AGQMetrics(
        modularity=r["modularity"],
        acyclicity=r["acyclicity"],
        stability=r["stability"],
        cohesion=r["cohesion"],
    )
    return r, metrics, r["agq_score"]


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


def _enhanced_str(agq, metrics, nodes, lang_name):
    """Compute enhanced metrics string (fingerprint, z-score, cycles)."""
    try:
        from qse.agq_enhanced import compute_agq_enhanced
        enh = compute_agq_enhanced(
            agq, metrics.modularity, metrics.acyclicity,
            metrics.stability, metrics.cohesion, nodes, lang_name)
        return (f"  [{enh.fingerprint}]"
                f"  z={enh.agq_z:+.2f} ({enh.agq_percentile}%ile)"
                f"  cycles={enh.cycle_severity['severity_level']}")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# qse agq
# ---------------------------------------------------------------------------

def _run_agq(args) -> None:
    """Execute the AGQ gate."""
    from qse.graph_metrics import compute_agq

    if args.graph:
        G, abstract, lcom4 = _load_graph_json(args.graph)

        weights = None
        if args.agq_weights:
            vals = [float(x) for x in args.agq_weights.split(",")]
            if len(vals) != 4:
                print("Error: --weights requires exactly 4 values (mod,acy,stab,coh)",
                      file=sys.stderr)
                sys.exit(1)
            total = sum(vals)
            weights = tuple(v / total for v in vals)

        metrics = compute_agq(G, abstract_modules=set(abstract), classes_lcom4=lcom4,
                              weights=weights or (0.25, 0.25, 0.25, 0.25))
        agq = metrics.agq_score

        failures = []
        if agq < args.threshold:
            failures.append(f"agq_score={agq:.4f} below threshold {args.threshold:.2f}")

        # Constraint checking
        constraint_score = None
        if args.constraints:
            with open(args.constraints) as f:
                cd = json.load(f)
            constraints = cd if isinstance(cd, list) else cd.get("constraints", [])
            violations = check_constraints_graph(G, constraints)
            constraint_score = compute_constraint_score(G, violations)
            if constraint_score < args.min_constraint_score:
                failures.append(
                    f"constraint_score={constraint_score:.4f} below minimum {args.min_constraint_score:.2f}")

        result = {
            "gate": "PASS" if not failures else "FAIL",
            "agq_score": round(agq, 4),
            "threshold": args.threshold,
            "metrics": {k: round(getattr(metrics, k), 4)
                        for k in ("modularity", "acyclicity", "stability", "cohesion")},
            "graph": {"nodes": G.number_of_nodes(), "edges": G.number_of_edges()},
            "failures": failures,
        }
        if constraint_score is not None:
            result["constraint_score"] = round(constraint_score, 4)

        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump(result, f, indent=2)

        enh = _enhanced_str(agq, metrics, G.number_of_nodes(),
                            _detect_repo_language(args.path) if args.path != "." else "Python")
    else:
        # Rust scanner
        r, metrics, agq = _scan_repo(args.path)

        failures = []
        if agq < args.threshold:
            failures.append(f"agq_score={agq:.4f} below threshold {args.threshold:.2f}")

        result = {
            "gate": "PASS" if not failures else "FAIL",
            "agq_score": round(agq, 4),
            "threshold": args.threshold,
            "language": r["language"],
            "metrics": {k: round(r[k], 4)
                        for k in ("modularity", "acyclicity", "stability", "cohesion")},
            "graph": {"nodes": r["nodes"], "edges": r["edges"]},
            "failures": failures,
        }
        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump(result, f, indent=2)

        lang_map = {"Java": "Java", "Go": "Go", "Python": "Python"}
        enh = _enhanced_str(agq, metrics, r["nodes"],
                            lang_map.get(r["language"], "Python"))

    if failures:
        print("AGQ GATE FAIL", file=sys.stderr)
        for fail in failures:
            print(f"  - {fail}", file=sys.stderr)
        sys.exit(1)

    cs = f"  constraints={constraint_score:.2f}" if 'constraint_score' in dir() and constraint_score is not None else ""
    print(f"AGQ GATE PASS  agq={agq:.4f}  "
          f"M={metrics.modularity:.2f} A={metrics.acyclicity:.2f} "
          f"St={metrics.stability:.2f} Co={metrics.cohesion:.2f}"
          f"{enh}{cs}")


# ---------------------------------------------------------------------------
# qse discover
# ---------------------------------------------------------------------------

def _run_discover(args) -> None:
    """Auto-discover architectural boundaries and propose constraints."""
    from qse.discover import discover_policies

    if args.graph:
        G, _, _ = _load_graph_json(args.graph)
    else:
        import networkx as nx
        from _qse_core import scan_to_graph_json
        raw = scan_to_graph_json(args.path)
        data = json.loads(raw)
        G = nx.DiGraph()
        for node in data["nodes"]:
            G.add_node(node["id"], internal=node["internal"])
        for src, tgt in data["edges"]:
            G.add_edge(src, tgt)

    report = discover_policies(G, min_confidence=args.min_confidence)

    print(f"Clusters found: {len(report.clusters)}")
    for c in report.clusters:
        print(f"  {c['label']} ({c['size']} modules)")

    print(f"\nProposed rules: {len(report.proposed_rules)}")
    for r in report.proposed_rules:
        marker = "+" if r.confidence >= 0.7 else "?"
        print(f"  [{marker} {r.confidence:.0%}] forbidden: {r.from_pattern} -> {r.to_pattern}")
        print(f"         {r.rationale}")

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


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="qse",
        description="QSE - Quality Score Engine for architecture validation",
    )
    sub = parser.add_subparsers(dest="command")

    # ── qse agq ──
    agq = sub.add_parser("agq", help="AGQ gate (architecture graph quality)")
    agq.add_argument("path", nargs="?", default=".",
                     help="Path to repo root")
    agq.add_argument("--graph", type=str, default=None, metavar="FILE",
                     help="JSON dependency graph file (skip auto-scan)")
    agq.add_argument("--threshold", type=float, default=0.70, metavar="N",
                     help="Minimum AGQ score (default: 0.70)")
    agq.add_argument("--constraints", type=str, default=None, metavar="FILE",
                     help="JSON file with forbidden-edge constraints")
    agq.add_argument("--min-constraint-score", type=float, default=0.95, metavar="N",
                     help="Minimum constraint score (default: 0.95)")
    agq.add_argument("--output-json", type=str, default=None, metavar="FILE")
    agq.add_argument("--weights", dest="agq_weights", type=str, default=None,
                     metavar="W1,W2,W3,W4",
                     help="Custom weights mod,acy,stab,coh (e.g. 0,0.73,0.05,0.17)")

    # ── qse discover ──
    disc = sub.add_parser("discover",
                          help="Auto-discover architectural boundaries and propose constraints")
    disc.add_argument("path", nargs="?", default=".",
                      help="Path to repo root")
    disc.add_argument("--graph", type=str, default=None, metavar="FILE",
                      help="JSON dependency graph file (skip auto-scan)")
    disc.add_argument("--min-confidence", type=float, default=0.5, metavar="N",
                      help="Minimum confidence for proposed rules (default: 0.5)")
    disc.add_argument("--output-json", type=str, default=None, metavar="FILE")
    disc.add_argument("--output-constraints", type=str, default=None, metavar="FILE",
                      help="Write high-confidence constraints to JSON (ready for --constraints)")

    args = parser.parse_args()

    if args.command == "agq":
        _run_agq(args)
    elif args.command == "discover":
        _run_discover(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
