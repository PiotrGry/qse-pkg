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
from pathlib import Path


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
        from qse.scanner import scan_dependency_graph
        return scan_dependency_graph(root, include=include, exclude=exclude)

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
    migration_ref = (_resolve_ref(args.migration_baseline)
                     if args.migration_baseline else None)

    if not args.quiet:
        msg = f"qse gate-diff: scanning {base_ref[:8]}..{head_ref[:8]}"
        if migration_ref:
            msg += f"  (migration baseline: {migration_ref[:8]})"
        print(msg, file=sys.stderr)

    try:
        G_before = _checkout_and_scan(base_ref)
        G_after  = _checkout_and_scan(head_ref)
        G_migration = (_checkout_and_scan(migration_ref)
                       if migration_ref else None)
    except subprocess.CalledProcessError as e:
        print(f"qse gate-diff: git error — {e}", file=sys.stderr)
        return 2

    gate_kwargs = dict(
        language=args.language,
        pc_fail=args.pc_fail,
        pc_delta_fail=args.pc_delta,
        rc_fail=args.rc_fail,
        hub_spike_factor=args.hub_spike,
    )
    base_result = gate_check(G_before, G_after, **gate_kwargs)

    # Migration mode: three-reference policy.
    # Compare HEAD against TWO baselines:
    #   - base_result  — gate(base, HEAD):       regression vs canonical?
    #   - mig_result   — gate(migration, HEAD):  regression vs migration start?
    #
    # Policy outcomes (driving final pass/fail and banner text):
    #   CLEAN_PASS              base PASS + migration PASS (or no migration arg)
    #   IN_MIGRATION_PASS       base FAIL + migration PASS — improving since migration
    #   FAIL_BOTH               base FAIL + migration FAIL — true regression
    #   BASE_PASS_MIG_FAIL      base PASS + migration FAIL — main improved since
    #                           migration; HEAD ≥ main but worse than migration start
    #                           (rare; PASS but warn)
    migration_result = None
    policy_outcome = "CLEAN_PASS" if base_result.passed else "FAIL_BOTH"
    final_passed = base_result.passed
    if G_migration is not None:
        # Sanity: warn if migration_baseline is not an ancestor of head.
        # Mig-baseline ahead of head, or on an unrelated branch, makes the
        # "improving since migration" framing meaningless.
        try:
            anc = subprocess.run(
                ["git", "merge-base", "--is-ancestor", migration_ref, head_ref],
                cwd=repo, capture_output=True, check=False,
            )
            if anc.returncode != 0:
                print(f"qse gate-diff: warning — migration baseline "
                      f"{migration_ref[:8]} is not an ancestor of HEAD; "
                      "policy semantics may be nonsense.", file=sys.stderr)
        except OSError:
            pass

        migration_result = gate_check(G_migration, G_after, **gate_kwargs)
        if base_result.passed and migration_result.passed:
            policy_outcome = "CLEAN_PASS"
            final_passed = True
        elif not base_result.passed and migration_result.passed:
            policy_outcome = "IN_MIGRATION_PASS"
            final_passed = True
        elif not base_result.passed and not migration_result.passed:
            policy_outcome = "FAIL_BOTH"
            final_passed = False
        else:  # base_result.passed and not migration_result.passed
            policy_outcome = "BASE_PASS_MIG_FAIL"
            final_passed = True

    from dataclasses import replace
    result = replace(base_result, passed=final_passed)

    if args.output_json:
        import json as _json
        from dataclasses import asdict
        from qse.gate.gate_check import Violation
        out = {
            "passed": result.passed,
            "violations": [
                asdict(v) if isinstance(v, Violation) else {"rule": "LEGACY", "summary": str(v)}
                for v in result.violations
            ],
            "metrics_before": result.metrics_before,
            "metrics_after": result.metrics_after,
            "base": base_ref,
            "head": head_ref,
        }
        out["base_passed"] = base_result.passed
        out["policy_outcome"] = policy_outcome
        if migration_result:
            out["migration_baseline"] = migration_ref
            out["migration_passed"] = migration_result.passed
            out["migration_violations"] = [
                asdict(v) if isinstance(v, Violation) else {"rule": "LEGACY", "summary": str(v)}
                for v in migration_result.violations
            ]
        with open(args.output_json, "w") as f:
            _json.dump(out, f, indent=2)

    if result.passed:
        if not args.quiet:
            if policy_outcome == "IN_MIGRATION_PASS":
                print("qse gate-diff: PASS (in-migration)")
                print(f"  vs base ({base_ref[:8]}):          FAIL — pre-existing at migration start")
                print(f"  vs migration ({migration_ref[:8]}): PASS — no new regressions since migration")
                print("  Vs-base violations (for reference, NOT blocking this PR):")
                for v in result.violations:
                    print(f"    {v}")
                print("  These need to be fixed before final merge to base.")
            elif policy_outcome == "BASE_PASS_MIG_FAIL":
                print("qse gate-diff: PASS (base improved since migration)")
                print(f"  vs base ({base_ref[:8]}):          PASS")
                print(f"  vs migration ({migration_ref[:8]}): FAIL — base evolved during your migration")
                print("  HEAD is fine vs current base. Migration-relative comparison flags issues "
                      "that base no longer has — likely the base was independently improved while "
                      "you worked. Re-baseline if helpful.")
                if migration_result:
                    print("  Vs-migration violations (informational):")
                    for v in migration_result.violations:
                        print(f"    {v}")
            else:
                print("qse gate-diff: PASS — no architectural regressions detected.")
        return 0
    else:
        print("qse gate-diff: FAIL")
        if migration_result:
            print(f"  vs base ({base_ref[:8]}):          FAIL")
            print(f"  vs migration ({migration_ref[:8]}): FAIL")
            print("  HEAD regresses vs BOTH baselines — real architectural debt added.")
            print()
        for v in result.violations:
            print(f"  {v}")
        return 1


# ── qse archeology ─────────────────────────────────────────────────────────────

def _run_archeology(args) -> int:
    """Retroactive scan: walk the last N commits, run gate_check on each step,
    report which would have fired. The install-decision asset.

    Output: HTML report (default) or JSON.
    """
    import json as _json
    import os
    import shutil
    import subprocess
    import tempfile
    import networkx as nx
    from qse.gate.gate_check import gate_check

    repo = os.path.abspath(args.path)

    # Discover commits to walk
    rev_range = args.range or f"-{args.last}"
    log = subprocess.run(
        ["git", "log", "--reverse", "--first-parent", "--pretty=%H%x09%s",
         rev_range],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    commits = []
    for line in log.stdout.strip().split("\n"):
        if not line.strip():
            continue
        sha, _, subject = line.partition("\t")
        commits.append((sha, subject))

    if len(commits) < 2:
        print("qse archeology: need at least 2 commits to compare.", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"qse archeology: walking {len(commits) - 1} steps "
              f"({commits[0][0][:8]}..{commits[-1][0][:8]})", file=sys.stderr)

    def scan_at_ref(ref: str) -> nx.DiGraph:
        tmp = tempfile.mkdtemp(prefix="qse-arch-")
        try:
            result = subprocess.run(
                ["git", "archive", ref, "--format=tar"],
                cwd=repo, capture_output=True, check=True,
            )
            import io, tarfile
            with tarfile.open(fileobj=io.BytesIO(result.stdout)) as tar:
                tar.extractall(tmp)
            from qse.integrations.pre_commit import _scan_python_dir
            return _scan_python_dir(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # Walk
    findings: list[dict] = []
    G_prev = scan_at_ref(commits[0][0])
    for i in range(1, len(commits)):
        sha, subject = commits[i]
        try:
            G_cur = scan_at_ref(sha)
            r = gate_check(G_prev, G_cur, language=args.language)
            if not r.passed:
                from dataclasses import asdict
                from qse.gate.gate_check import Violation
                findings.append({
                    "commit": sha,
                    "short": sha[:8],
                    "subject": subject,
                    "violations": [
                        asdict(v) if isinstance(v, Violation)
                        else {"rule": "LEGACY", "summary": str(v),
                              "why": "", "fix": "", "culprits": []}
                        for v in r.violations
                    ],
                    "metrics_before": r.metrics_before,
                    "metrics_after": r.metrics_after,
                })
            G_prev = G_cur
        except Exception as e:
            print(f"  warn: failed at {sha[:8]}: {e}", file=sys.stderr)
            continue

        if not args.quiet and i % 10 == 0:
            print(f"  ... {i}/{len(commits) - 1} commits", file=sys.stderr)

    if not args.quiet:
        print(f"qse archeology: scanned {len(commits) - 1} commits, "
              f"found {len(findings)} regressions.", file=sys.stderr)

    # Output
    if args.output_json:
        with open(args.output_json, "w") as f:
            _json.dump({
                "repo": repo,
                "range": rev_range,
                "commits_scanned": len(commits) - 1,
                "regressions_found": len(findings),
                "findings": findings,
            }, f, indent=2, default=str)
        if not args.quiet:
            print(f"  JSON → {args.output_json}", file=sys.stderr)

    if args.output_html:
        _write_archeology_html(args.output_html, repo, rev_range, commits, findings)
        if not args.quiet:
            print(f"  HTML → {args.output_html}", file=sys.stderr)

    if not (args.output_json or args.output_html):
        # Default: print summary table to stdout
        print(f"\n{'='*70}")
        print(f"  Archeology report — {os.path.basename(repo)}")
        print(f"  Range: {rev_range}   Commits scanned: {len(commits) - 1}")
        print(f"  Regressions found: {len(findings)}")
        print('='*70)
        for f in findings[:30]:
            print(f"\n  {f['short']}  {f['subject'][:60]}")
            for v in f["violations"]:
                rule = v.get("rule", "?") if isinstance(v, dict) else "?"
                summary = v.get("summary", "") if isinstance(v, dict) else str(v)
                print(f"    [{rule}] {summary[:100]}")
        if len(findings) > 30:
            print(f"\n  ... and {len(findings) - 30} more (use --output-html for full report)")

    return 0


def _write_archeology_html(out_path: str, repo: str, rev_range: str,
                            commits: list, findings: list) -> None:
    """Single-file HTML report (no external deps)."""
    import os
    rule_counts: dict[str, int] = {}
    for f in findings:
        for v in f["violations"]:
            rule = v.get("rule", "?") if isinstance(v, dict) else str(v).split(":", 1)[0]
            rule_counts[rule] = rule_counts.get(rule, 0) + 1

    rows = []
    for f in findings:
        viol_parts = []
        for v in f["violations"]:
            if isinstance(v, dict):
                rule = v.get("rule", "?")
                summary = v.get("summary", "")
                why = v.get("why", "")
                fix = v.get("fix", "")
                culprits = v.get("culprits", [])
                culprit_html = ""
                if culprits:
                    culprit_html = "<br>" + "<br>".join(
                        f"<small>• {_html_escape(str(c))}</small>" for c in culprits[:5]
                    )
                viol_parts.append(
                    f"<code>{_html_escape(rule)}</code> "
                    f"{_html_escape(summary)}"
                    f"{culprit_html}"
                    f"<br><small><b>Why:</b> {_html_escape(why)}</small>"
                    f"<br><small><b>Fix:</b> {_html_escape(fix)}</small>"
                )
            else:
                viol_parts.append(_html_escape(str(v)))
        viol_html = "<hr style='border:0;border-top:1px dashed #ddd;margin:0.5em 0'>".join(viol_parts)
        rows.append(
            f"<tr><td><code>{f['short']}</code></td>"
            f"<td>{_html_escape(f['subject'])}</td>"
            f"<td>{viol_html}</td></tr>"
        )
    rule_summary = "".join(
        f"<li><b>{r}</b>: {c}</li>"
        for r, c in sorted(rule_counts.items(), key=lambda x: -x[1])
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>QSE Archeology — {_html_escape(os.path.basename(repo))}</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 1100px;
        margin: 2em auto; padding: 0 1em; color: #1d1d1f; }}
h1, h2 {{ font-weight: 600; }}
.stat {{ display: inline-block; padding: 0.5em 1em; margin-right: 1em;
         background: #f5f5f7; border-radius: 8px; }}
.stat b {{ font-size: 1.5em; display: block; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1em; font-size: 0.9em; }}
th, td {{ padding: 0.6em; border-bottom: 1px solid #e5e5ea; text-align: left;
         vertical-align: top; }}
th {{ background: #fafafa; font-weight: 600; }}
code {{ background: #f0f0f0; padding: 0.1em 0.3em; border-radius: 3px;
        font-size: 0.85em; }}
.banner {{ padding: 1em; background: #fff7e6; border-left: 4px solid #ff9500;
           border-radius: 4px; }}
</style></head><body>
<h1>QSE Archeology Report</h1>
<p><b>Repo:</b> <code>{_html_escape(repo)}</code><br>
<b>Range:</b> <code>{_html_escape(rev_range)}</code><br>
<b>Generated:</b> {_now_iso()}</p>

<div class="banner">
<p>Had QSE-Gate been installed at the start of this range, it would have flagged
<b>{len(findings)} commit(s)</b> as architectural regressions.</p>
</div>

<h2>Summary</h2>
<div>
<span class="stat"><b>{len(commits) - 1}</b>commits scanned</span>
<span class="stat"><b>{len(findings)}</b>regressions found</span>
<span class="stat"><b>{len(findings) / max(len(commits) - 1, 1) * 100:.1f}%</b>flag rate</span>
</div>

<h2>Rule breakdown</h2>
<ul>{rule_summary or "<li>None</li>"}</ul>

<h2>Findings</h2>
<table>
<thead><tr><th>Commit</th><th>Subject</th><th>Violations</th></tr></thead>
<tbody>
{''.join(rows) or '<tr><td colspan="3"><i>No regressions in this range. Clean run.</i></td></tr>'}
</tbody>
</table>

<p style="margin-top: 3em; color: #888; font-size: 0.85em;">
Generated by <code>qse archeology</code>. Thresholds:
language preset (delta-based, architecture-style agnostic). See
<a href="https://github.com/PiotrGry/qse-pkg">qse-pkg</a>.
</p>
</body></html>"""
    with open(out_path, "w") as fp:
        fp.write(html)


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


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

def _run_health(args) -> None:
    """Snapshot health report — diagnostic, not a gate."""
    import dataclasses
    from qse.health import compute_health, render_text, trend

    rep = compute_health(args.path, language=args.language)
    trend_data = None
    if args.trend > 0:
        trend_data = trend(args.path, n_commits=args.trend,
                           step=args.trend_step, language=args.language)

    if args.json:
        payload = dataclasses.asdict(rep)
        if trend_data is not None:
            payload["trend"] = trend_data
        out = json.dumps(payload, indent=2)
    else:
        out = render_text(rep, trend_data=trend_data)

    if args.output:
        Path(args.output).write_text(out + "\n")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(out)


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
    gd.add_argument("--migration-baseline", default=None, metavar="REF",
                    help="Long-running refactor mode: tolerate regressions vs "
                         "base (e.g. main) IF HEAD is still better than this "
                         "migration starting point. Use the commit where the "
                         "refactor branch began. Pass only when the diff "
                         "covers a multi-step refactor; ordinary feature "
                         "branches don't need it.")
    gd.add_argument("--output-json", type=str, default=None, metavar="FILE",
                    help="Write gate result to JSON file.")
    gd.add_argument("--quiet", action="store_true",
                    help="Suppress informational output (violations still printed).")

    # qse archeology — retroactive scan over commit history
    arch = sub.add_parser(
        "archeology",
        help="Retroactive gate scan: walk last N commits, report what would have fired.",
    )
    arch.add_argument("path", nargs="?", default=".",
                      help="Repo root (default: current directory).")
    arch.add_argument("--last", type=int, default=200, metavar="N",
                      help="Walk the last N commits (default: 200).")
    arch.add_argument("--range", default=None, metavar="REV",
                      help="Custom git rev range (e.g. main..HEAD), overrides --last.")
    arch.add_argument("--language", default="python", choices=["python", "java", "go"],
                      help="Threshold preset (default: python).")
    arch.add_argument("--output-html", default=None, metavar="FILE",
                      help="Write HTML report to file.")
    arch.add_argument("--output-json", default=None, metavar="FILE",
                      help="Write JSON report to file.")
    arch.add_argument("--quiet", action="store_true",
                      help="Suppress progress output.")

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

    # qse health — snapshot health report vs language baseline
    health = sub.add_parser("health",
                            help="Snapshot health report (drift/debt diagnostic).")
    health.add_argument("path", nargs="?", default=".",
                        help="Repo root.")
    health.add_argument("--language", choices=["python", "java", "go"],
                        default=None,
                        help="Override autodetected language.")
    health.add_argument("--trend", type=int, default=0, metavar="N",
                        help="Sample last N commits and show AGQ trend.")
    health.add_argument("--trend-step", type=int, default=20, metavar="K",
                        help="When --trend N is set, sample every K commits "
                             "(default: 20).")
    health.add_argument("--json", action="store_true",
                        help="Emit JSON instead of human-readable text.")
    health.add_argument("--output", type=str, default=None, metavar="FILE",
                        help="Write report to FILE.")

    args = parser.parse_args()

    if args.command == "gate":
        sys.exit(_run_gate(args, args.gate_args))
    if args.command == "gate-diff":
        sys.exit(_run_gate_diff(args))
    if args.command == "archeology":
        sys.exit(_run_archeology(args))
    if args.command == "agq":
        _run_agq(args)
        return
    if args.command == "discover":
        _run_discover(args)
        return
    if args.command == "health":
        _run_health(args)
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
