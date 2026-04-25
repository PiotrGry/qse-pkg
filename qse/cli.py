"""QSE command-line interface.

Sprint 0 Slice 2b: decoupled from DDD preset. Three subcommands:

    qse gate <path>      AI-Drift Firewall rules gate (proxy to qse.gate.runner).
    qse agq  <path>      Advisory AGQ score (modularity + acyclicity + stability + cohesion).
    qse discover <path>  Auto-discover architectural boundaries, propose constraints.

The older `scan` / `trl4` subcommands and the DDD-based `qse gate` were removed.
The DDD variants are preserved in git history and the module in
`_obsolete/qse_trl4_gate_module/`.
"""

from __future__ import annotations

import argparse
import json
import sys


def _load_graph_json(path: str):
    """Load dependency graph from JSON.

    Expected shape:
        {"nodes": [...], "edges": [[src, tgt], ...],
         "abstract_modules": [...],  # optional
         "classes_lcom4":    [...]}  # optional
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


# ── qse gate-diff ──────────────────────────────────────────────────────────────

def _run_gate_diff(args) -> int:
    """Delta-based architectural gate: compare HEAD vs base ref.

    Builds the dependency graph at two git refs and runs gate_check().
    Exit 0 = clean. Exit 1 = violations found. Exit 2 = infrastructure error.
    """
    import os
    import shutil
    import subprocess
    import tempfile
    import networkx as nx
    from qse.gate.gate_check import gate_check

    repo = os.path.abspath(args.path)

    def _checkout_and_scan(ref: str) -> nx.DiGraph:
        """Checkout ref into a temp dir and scan Python files."""
        tmp = tempfile.mkdtemp(prefix="qse-gate-diff-")
        try:
            subprocess.run(
                ["git", "archive", ref, "--format=tar"],
                cwd=repo, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            result = subprocess.run(
                ["git", "archive", ref, "--format=tar"],
                cwd=repo, capture_output=True, check=True,
            )
            import tarfile, io
            with tarfile.open(fileobj=io.BytesIO(result.stdout)) as tar:
                tar.extractall(tmp)
            return _scan_python_dir(tmp, args.include, args.exclude)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _scan_python_dir(root: str, include: list[str], exclude: list[str]) -> nx.DiGraph:
        import ast as _ast
        from pathlib import Path
        import re

        def _glob_to_re(pat: str) -> str:
            """Convert glob pattern to regex (supports **, *, ?, [...])."""
            i, n, res = 0, len(pat), ""
            while i < n:
                c = pat[i]
                if c == "*":
                    if pat[i:i+3] == "**/":
                        res += "(.+/)?"; i += 3; continue
                    if pat[i:i+2] == "**":
                        res += ".*"; i += 2; continue
                    res += "[^/]*"
                elif c == "?":
                    res += "[^/]"
                elif c == "[":
                    j = pat.find("]", i)
                    res += pat[i:j+1] if j != -1 else re.escape(c)
                    i = j+1 if j != -1 else i+1; continue
                else:
                    res += re.escape(c)
                i += 1
            return res + "$"

        inc_res = [re.compile(_glob_to_re(p)) for p in (include or ["**/*.py"])]
        exc_res = [re.compile(_glob_to_re(p)) for p in (exclude or ["**/__pycache__/**"])]

        def keep(rel: str) -> bool:
            if not any(rx.match(rel) for rx in inc_res):
                return False
            if any(rx.match(rel) for rx in exc_res):
                return False
            return True

        rootp = Path(root)
        py_files = [p for p in rootp.rglob("*.py")
                    if p.name != "__init__.py"
                    and "__pycache__" not in str(p)
                    and keep(str(p.relative_to(rootp)))]

        nodes: dict[str, Path] = {}
        for p in py_files:
            rel = p.relative_to(rootp).with_suffix("")
            mod = ".".join(rel.parts)
            nodes[mod] = p

        G = nx.DiGraph()
        for mod in nodes:
            G.add_node(mod, file=str(nodes[mod]))

        for mod, path in nodes.items():
            try:
                src = path.read_text(errors="replace")
            except OSError:
                continue
            try:
                tree = _ast.parse(src)
            except SyntaxError:
                continue
            pkg = ".".join(mod.split(".")[:-1])
            for node in _ast.walk(tree):
                if isinstance(node, _ast.ImportFrom) and node.module:
                    dep = (node.module if node.level == 0 else (
                        ".".join(pkg.split(".")[:max(0, len(pkg.split(".")) - node.level + 1)])
                        + "." + node.module).lstrip("."))
                    if dep in nodes:
                        G.add_edge(mod, dep)
                    for a in node.names:
                        full = f"{dep}.{a.name}"
                        if full in nodes:
                            G.add_edge(mod, full)
                elif isinstance(node, _ast.Import):
                    for a in node.names:
                        if a.name in nodes:
                            G.add_edge(mod, a.name)
        return G

    # Resolve refs
    def _resolve_ref(ref: str) -> str:
        r = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=repo, capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(f"qse gate-diff: cannot resolve ref '{ref}'", file=sys.stderr)
            sys.exit(2)
        return r.stdout.strip()

    base_ref = _resolve_ref(args.base)
    head_ref = _resolve_ref(args.head)

    if not args.quiet:
        print(f"qse gate-diff: scanning {base_ref[:8]}..{head_ref[:8]}", file=sys.stderr)

    try:
        G_before = _checkout_and_scan(base_ref)
        G_after  = _checkout_and_scan(head_ref)
    except subprocess.CalledProcessError as e:
        print(f"qse gate-diff: git error — {e}", file=sys.stderr)
        return 2

    result = gate_check(
        G_before, G_after,
        language=args.language,
        pc_fail=args.pc_fail,
        pc_delta_fail=args.pc_delta,
        rc_fail=args.rc_fail,
        hub_spike_factor=args.hub_spike,
    )

    if args.output_json:
        import json as _json
        out = {
            "passed": result.passed,
            "violations": result.violations,
            "metrics_before": result.metrics_before,
            "metrics_after": result.metrics_after,
            "base": base_ref,
            "head": head_ref,
        }
        with open(args.output_json, "w") as f:
            _json.dump(out, f, indent=2)

    if result.passed:
        if not args.quiet:
            print("qse gate-diff: PASS — no architectural regressions detected.")
        return 0
    else:
        print("qse gate-diff: FAIL")
        for v in result.violations:
            print(f"  {v}")
        return 1


# ── qse agq ────────────────────────────────────────────────────────────────────

def _run_agq(args) -> None:
    """Language-agnostic AGQ gate (advisory per Sprint 0 R-AGQ-1)."""
    from qse.graph_metrics import compute_agq, AGQMetrics

    abstract: set = set()
    lcom4: list = []

    if args.graph:
        G, abstract, lcom4 = _load_graph_json(args.graph)
    else:
        lang = _detect_repo_language(args.path)

        # Prefer Rust qse-core when available
        try:
            from _qse_core import scan_and_compute_agq
            r = scan_and_compute_agq(args.path)
            metrics = AGQMetrics(
                modularity=r["modularity"],
                acyclicity=r["acyclicity"],
                stability=r["stability"],
                cohesion=r["cohesion"],
            )
            agq = r["agq_score"]
            _finalize_agq_output(args, agq, metrics,
                                 nodes=r["nodes"], edges=r["edges"],
                                 language=r["language"], G=None)
            return
        except ImportError:
            if lang in ("java", "go"):
                print("[warn] Rust qse-core not installed — Java/Go require it.",
                      file=sys.stderr)
                sys.exit(2)
            # Python fallback below

        from qse.scanner import scan_repo
        from qse.graph_metrics import compute_lcom4 as _compute_lcom4
        analysis = scan_repo(args.path)
        G = analysis.graph
        abstract = {c.name for c in analysis.classes.values() if c.is_abstract}
        lcom4 = [_compute_lcom4(c.method_attrs)
                 for c in analysis.classes.values() if c.method_attrs]

    weights = None
    if getattr(args, "agq_weights", None):
        vals = [float(x) for x in args.agq_weights.split(",")]
        if len(vals) != 4:
            print("error: --weights requires exactly 4 values (mod,acy,stab,coh)",
                  file=sys.stderr)
            sys.exit(1)
        total = sum(vals) or 1.0
        weights = tuple(v / total for v in vals)

    metrics = compute_agq(G, abstract_modules=abstract, classes_lcom4=lcom4,
                          weights=weights or (0.25, 0.25, 0.25, 0.25))
    _finalize_agq_output(args, metrics.agq_score, metrics,
                         nodes=G.number_of_nodes(), edges=G.number_of_edges(),
                         language=_detect_repo_language(args.path), G=G)


def _finalize_agq_output(args, agq: float, metrics, *, nodes: int, edges: int,
                         language: str, G) -> None:
    failures = []
    if agq < args.threshold:
        failures.append(f"agq_score={agq:.4f} below threshold {args.threshold:.2f}")

    constraint_score = None
    constraint_violations: list = []
    if getattr(args, "constraints", None):
        if G is None:
            print("error: --constraints requires the Python fallback scanner (graph object). "
                  "Use --graph <json> instead.", file=sys.stderr)
            sys.exit(2)
        from qse.constraints import check_constraints_graph, compute_constraint_score
        with open(args.constraints) as f:
            constraints_data = json.load(f)
        constraints = (constraints_data if isinstance(constraints_data, list)
                       else constraints_data.get("constraints", []))
        constraint_violations = check_constraints_graph(G, constraints)
        constraint_score = compute_constraint_score(G, constraint_violations)
        min_cs = getattr(args, "min_constraint_score", 0.95)
        if constraint_score < min_cs:
            failures.append(
                f"constraint_score={constraint_score:.4f} below minimum {min_cs:.2f}"
            )

    result = {
        "gate": "PASS" if not failures else "FAIL",
        "agq_score": round(agq, 4),
        "threshold": args.threshold,
        "language": language,
        "metrics": {
            "modularity": round(metrics.modularity, 4),
            "acyclicity": round(metrics.acyclicity, 4),
            "stability":  round(metrics.stability, 4),
            "cohesion":   round(metrics.cohesion, 4),
        },
        "graph": {"nodes": nodes, "edges": edges},
        "failures": failures,
    }
    if constraint_score is not None:
        result["constraint_score"] = round(constraint_score, 4)
        result["constraint_violations"] = [
            {"rule": v["rule"], "source": v["source"], "target": v["target"]}
            for v in constraint_violations
        ]

    if getattr(args, "output_json", None):
        with open(args.output_json, "w") as f:
            json.dump(result, f, indent=2)

    if failures:
        print("AGQ GATE FAIL", file=sys.stderr)
        for msg in failures:
            print(f"  - {msg}", file=sys.stderr)
        sys.exit(1)

    # Optional enhanced diagnostics
    extras = ""
    try:
        from qse.agq_enhanced import compute_agq_enhanced
        lang_map = {"java": "Java", "go": "Go", "py": "Python",
                    "Java": "Java", "Go": "Go", "Python": "Python"}
        enh = compute_agq_enhanced(
            agq, metrics.modularity, metrics.acyclicity,
            metrics.stability, metrics.cohesion, nodes,
            lang_map.get(language, "Python"))
        extras = (f"  [{enh.fingerprint}]  z={enh.agq_z:+.2f} "
                  f"({enh.agq_percentile}%ile)  cycles={enh.cycle_severity['severity_level']}")
    except Exception:
        pass

    line = (f"AGQ GATE PASS  agq={agq:.4f}  "
            f"M={metrics.modularity:.2f} A={metrics.acyclicity:.2f} "
            f"St={metrics.stability:.2f} Co={metrics.cohesion:.2f}{extras}")
    if constraint_score is not None:
        line += f"  constraints={constraint_score:.2f}"
    print(line)
    sys.exit(0)


# ── qse discover ───────────────────────────────────────────────────────────────

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


# ── qse gate ───────────────────────────────────────────────────────────────────

def _run_gate(args, forwarded: list[str]) -> int:
    """Delegate `qse gate ...` to the axiom-backed rules gate."""
    # argparse can't route --help past our REMAINDER sink, so intercept here.
    if any(a in ("-h", "--help") for a in forwarded) or not forwarded:
        from qse.gate.runner import build_arg_parser
        build_arg_parser().print_help()
        return 0 if forwarded else 1
    from qse.gate.runner import main as gate_main
    return gate_main(forwarded)


# ── entry ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="qse",
        description="QSE — Quality Score Engine for architecture validation.",
    )
    sub = parser.add_subparsers(dest="command")

    # qse gate — AI-Drift Firewall rules gate (proxy to qse.gate.runner)
    gate = sub.add_parser(
        "gate",
        help="AI-Drift Firewall: axiom-backed rules gate (CYCLE_NEW, LAYER_VIOLATION, BOUNDARY_LEAK).",
        add_help=False,  # defer --help to the underlying runner so flags stay in one place
    )
    gate.add_argument("gate_args", nargs=argparse.REMAINDER,
                      help="Arguments forwarded to qse-gate (see `qse-gate --help`).")

    # qse agq — advisory AGQ score
    agq = sub.add_parser("agq", help="Advisory AGQ score (graph metrics).")
    agq.add_argument("path", nargs="?", default=".",
                     help="Repo root (Python auto-scan if --graph not given).")
    agq.add_argument("--graph", type=str, default=None, metavar="FILE",
                     help="JSON dependency graph (language-agnostic input).")
    agq.add_argument("--threshold", type=float, default=0.70, metavar="N",
                     help="Minimum AGQ score (default: 0.70).")
    agq.add_argument("--constraints", type=str, default=None, metavar="FILE",
                     help="JSON file with forbidden-edge constraints (policy-as-a-service).")
    agq.add_argument("--min-constraint-score", type=float, default=0.95, metavar="N",
                     help="Minimum constraint score (default: 0.95).")
    agq.add_argument("--output-json", type=str, default=None, metavar="FILE")
    agq.add_argument("--weights", dest="agq_weights", type=str, default=None,
                     metavar="W1,W2,W3,W4",
                     help="Custom weights for mod,acy,stab,coh (auto-normalized).")

    # qse gate-diff — delta-based architectural gate (CI use)
    gd = sub.add_parser(
        "gate-diff",
        help="Delta-based architectural gate: compare two git refs for regressions.",
    )
    gd.add_argument("path", nargs="?", default=".",
                    help="Repo root (default: current directory).")
    gd.add_argument("--language", default="python", choices=["python", "java", "go"],
                    help="Language preset for thresholds (default: python).")
    gd.add_argument("--base", default="HEAD~1", metavar="REF",
                    help="Base git ref (default: HEAD~1).")
    gd.add_argument("--head", default="HEAD", metavar="REF",
                    help="Head git ref (default: HEAD).")
    gd.add_argument("--include", nargs="*", default=None, metavar="GLOB",
                    help="File globs to include (default: **/*.py).")
    gd.add_argument("--exclude", nargs="*", default=None, metavar="GLOB",
                    help="File globs to exclude.")
    gd.add_argument("--pc-fail", type=float, default=None, metavar="N",
                    help="Propagation Cost threshold (overrides language preset).")
    gd.add_argument("--pc-delta", type=float, default=None, metavar="N",
                    help="Max allowed PC increase per commit (overrides language preset).")
    gd.add_argument("--rc-fail", type=float, default=None, metavar="N",
                    help="Relative Cyclicity threshold %% (overrides language preset).")
    gd.add_argument("--hub-spike", type=float, default=None, metavar="N",
                    help="Max hub_score growth factor (overrides language preset).")
    gd.add_argument("--output-json", type=str, default=None, metavar="FILE",
                    help="Write gate result to JSON file.")
    gd.add_argument("--quiet", action="store_true",
                    help="Suppress informational output (violations still printed).")

    # qse discover — boundary discovery
    disc = sub.add_parser("discover",
                          help="Auto-discover architectural boundaries and propose constraints.")
    disc.add_argument("path", nargs="?", default=".",
                      help="Repo root (Python auto-scan if --graph not given).")
    disc.add_argument("--graph", type=str, default=None, metavar="FILE",
                      help="JSON dependency graph (language-agnostic input).")
    disc.add_argument("--min-confidence", type=float, default=0.5, metavar="N",
                      help="Minimum confidence for proposed rules (default: 0.5).")
    disc.add_argument("--output-json", type=str, default=None, metavar="FILE",
                      help="Write full discovery report to JSON.")
    disc.add_argument("--output-constraints", type=str, default=None, metavar="FILE",
                      help="Write high-confidence constraints to JSON.")

    args = parser.parse_args()

    if args.command == "gate":
        sys.exit(_run_gate(args, args.gate_args))
    if args.command == "gate-diff":
        sys.exit(_run_gate_diff(args))
    if args.command == "agq":
        _run_agq(args)
        return
    if args.command == "discover":
        _run_discover(args)
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
