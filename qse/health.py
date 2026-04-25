"""qse health — snapshot health report for a repository.

Compares current architectural metrics against the 240-OSS benchmark
distribution per language. Surfaces drift indicators (top hubs, isolated
clusters, cycles) without firing as a gate. Read-only diagnostic.

Output:
  - Human-readable text report (default)
  - JSON (with --json)
  - Optional trend: AGQ over last N commits sampled every K

Not a gate. Doesn't block anything. Designed to be run weekly or quarterly
to spot accumulated drift.
"""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


BENCH_DIR = Path(__file__).resolve().parent.parent / "artifacts" / "benchmark"


@dataclass
class HealthReport:
    path: str
    language: str
    nodes: int
    edges: int
    agq: float
    modularity: float
    acyclicity: float
    stability: float
    cohesion: float
    fingerprint: Optional[str]
    agq_pct: Optional[float]      # percentile vs benchmark
    cohesion_pct: Optional[float]
    cycle_pct: float              # % of nodes in SCCs > 1
    isolated_pct: float
    top_hubs: list[tuple[str, int]]
    top_isolated_clusters: int
    components: dict              # individual percentiles


def _load_bench(language: str) -> Optional[list[dict]]:
    f = BENCH_DIR / f"agq_240_{language}80.json"
    if not f.exists():
        return None
    data = json.loads(f.read_text())
    return [r for r in data["results"] if r.get("agq", {}).get("nodes", 0) > 30]


def _percentile_of(value: float, values: list[float]) -> float:
    """Return percentile of `value` within `values` (0-100)."""
    if not values:
        return 50.0
    s = sorted(values)
    below = sum(1 for v in s if v <= value)
    return 100.0 * below / len(s)


def _top_hubs(G, k: int = 5) -> list[tuple[str, int]]:
    fi = dict(G.in_degree())
    fo = dict(G.out_degree())
    scored = [(n, fi[n] * fo[n]) for n in G.nodes()]
    scored.sort(key=lambda t: -t[1])
    return [(n, s) for n, s in scored[:k] if s > 0]


def _isolated_pct(G) -> float:
    n = G.number_of_nodes()
    if not n:
        return 0.0
    fi = dict(G.in_degree())
    fo = dict(G.out_degree())
    iso = sum(1 for v in G.nodes() if fi[v] == 0 and fo[v] == 0)
    return 100.0 * iso / n


def _cycle_pct(G) -> float:
    import networkx as nx
    n = G.number_of_nodes()
    if not n:
        return 0.0
    in_cycle = sum(len(s) for s in nx.strongly_connected_components(G)
                   if len(s) > 1)
    return 100.0 * in_cycle / n


SKIP_PARTS = {"artifacts", "_vendor", "vendor", "build", "dist",
              "node_modules", ".tox", ".venv", "venv", ".git",
              ".claude", ".gstack", ".pytest_cache"}


def compute_health(path: str, language: Optional[str] = None) -> HealthReport:
    """Compute health snapshot. Python AST scanner + AGQ computation.

    Filters vendored / cloned / build paths from the graph so the report
    reflects the real source tree.
    """
    fp: Optional[str] = None

    from qse.scanner import scan_repo, DEFAULT_EXCLUDES
    from qse.graph_metrics import compute_agq, compute_lcom4

    analysis = scan_repo(path, exclude=DEFAULT_EXCLUDES)
    G = analysis.graph
    drop = [n for n in G.nodes()
            if any(p in SKIP_PARTS for p in n.split("."))]
    G.remove_nodes_from(drop)

    # Real cohesion via LCOM4 from extracted class internals (was bug:
    # earlier path passed empty list → cohesion always 0.75 default).
    classes_lcom4 = [
        compute_lcom4(c.method_attrs)
        for c in analysis.classes.values()
        if c.method_attrs
    ]
    abstract = {c.name for c in analysis.classes.values() if c.is_abstract}
    m = compute_agq(G, abstract_modules=abstract, classes_lcom4=classes_lcom4)
    metrics = {
        "agq":        m.agq_score,
        "modularity": m.modularity,
        "acyclicity": m.acyclicity,
        "stability":  m.stability,
        "cohesion":   m.cohesion,
        "nodes":      G.number_of_nodes(),
        "edges":      G.number_of_edges(),
        "language":   language or "python",
    }

    lang = (language or metrics["language"] or "python").lower()
    bench = _load_bench(lang)

    agq_pct = None
    coh_pct = None
    components: dict = {}
    if bench:
        agqs = [r["agq"]["agq_score"] for r in bench]
        cohs = [r["agq"]["cohesion"] for r in bench]
        agq_pct = _percentile_of(metrics["agq"], agqs)
        coh_pct = _percentile_of(metrics["cohesion"], cohs)
        for k in ("modularity", "acyclicity", "stability", "cohesion"):
            vals = [r["agq"][k] for r in bench if k in r["agq"]]
            components[k] = {
                "value":    metrics[k],
                "pct":      _percentile_of(metrics[k], vals) if vals else None,
                "median":   statistics.median(vals) if vals else None,
            }

    # fingerprint via agq_enhanced if available
    try:
        from qse.agq_enhanced import compute_agq_enhanced
        enh = compute_agq_enhanced(G, lcom4_per_class=[], abstract_modules=set())
        fp = getattr(enh, "fingerprint", None)
    except Exception:
        fp = None

    return HealthReport(
        path=path,
        language=lang,
        nodes=metrics["nodes"],
        edges=metrics["edges"],
        agq=metrics["agq"],
        modularity=metrics["modularity"],
        acyclicity=metrics["acyclicity"],
        stability=metrics["stability"],
        cohesion=metrics["cohesion"],
        fingerprint=fp,
        agq_pct=agq_pct,
        cohesion_pct=coh_pct,
        cycle_pct=_cycle_pct(G),
        isolated_pct=_isolated_pct(G),
        top_hubs=_top_hubs(G),
        top_isolated_clusters=int(_isolated_pct(G) / 100 * G.number_of_nodes()),
        components=components,
    )


def trend(path: str, n_commits: int = 200, step: int = 20,
          language: Optional[str] = None) -> list[dict]:
    """Walk last n_commits sampled every `step`; compute AGQ at each.

    Returns list of {sha, date, agq, cohesion, isolated_pct}.
    """
    import io
    import shutil
    import tarfile
    import tempfile

    log = subprocess.run(
        ["git", "log", "--first-parent", f"-{n_commits}",
         "--format=%H%x09%ci"],
        cwd=path, capture_output=True, text=True, check=True,
    ).stdout
    rows = [l.split("\t") for l in log.splitlines() if l.strip()]
    sampled = rows[::step]

    out = []
    for sha, date in sampled:
        tmp = tempfile.mkdtemp(prefix="qse-health-")
        try:
            r = subprocess.run(
                ["git", "archive", sha, "--format=tar"],
                cwd=path, capture_output=True, check=True,
            )
            with tarfile.open(fileobj=io.BytesIO(r.stdout)) as t:
                t.extractall(tmp)
            try:
                rep = compute_health(tmp, language=language)
                out.append({
                    "sha": sha[:8], "date": date,
                    "agq": rep.agq, "cohesion": rep.cohesion,
                    "isolated_pct": rep.isolated_pct,
                    "cycle_pct": rep.cycle_pct,
                    "nodes": rep.nodes,
                })
            except Exception as e:
                out.append({"sha": sha[:8], "date": date,
                            "error": f"{type(e).__name__}: {e}"})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return list(reversed(out))  # oldest first


def render_text(rep: HealthReport,
                trend_data: Optional[list[dict]] = None) -> str:
    out = []
    out.append("QSE Health Report")
    out.append("=" * 50)
    out.append(f"Path:     {rep.path}")
    out.append(f"Language: {rep.language}")
    out.append(f"Size:     {rep.nodes} modules, {rep.edges} edges")
    out.append("")

    pct_str = f" (p{rep.agq_pct:.0f} of {rep.language} OSS)" if rep.agq_pct else ""
    out.append(f"AGQ score: {rep.agq:.3f}{pct_str}")
    if rep.fingerprint:
        out.append(f"Fingerprint: {rep.fingerprint}")
    out.append("")

    out.append("Components (vs language baseline):")
    for k, d in rep.components.items():
        bar = ""
        if d.get("pct") is not None:
            bar = f"  p{d['pct']:.0f}"
            if d["pct"] < 25:
                bar += " ⚠ below p25"
        out.append(f"  {k:11s} {d['value']:.3f}{bar}")
    out.append("")

    out.append("Topology:")
    out.append(f"  cycle %:    {rep.cycle_pct:.1f}% of nodes in SCC>1")
    out.append(f"  isolated %: {rep.isolated_pct:.1f}% of nodes")
    if rep.top_hubs:
        out.append("  top hubs (fan_in × fan_out):")
        for n, s in rep.top_hubs:
            out.append(f"    {s:6d}  {n}")
    out.append("")

    # Diagnostic flags
    flags = []
    if rep.cycle_pct > 5:
        flags.append(f"  ⚠ cyclic: {rep.cycle_pct:.1f}% of modules in cycles")
    if rep.isolated_pct > 30:
        flags.append(f"  ⚠ archipelago: {rep.isolated_pct:.1f}% isolated "
                     "(possible dead code or test fixtures)")
    if rep.cohesion_pct is not None and rep.cohesion_pct < 25:
        flags.append(f"  ⚠ low cohesion: p{rep.cohesion_pct:.0f} of {rep.language} OSS")
    if flags:
        out.append("Flags:")
        out.extend(flags)
        out.append("")

    if trend_data:
        out.append(f"Trend ({len(trend_data)} sampled commits, oldest → newest):")
        out.append("  date        agq    cohesion  isolated%  cycle%")
        for r in trend_data:
            if "error" in r:
                out.append(f"  {r['date'][:10]}  ERR: {r['error']}")
                continue
            out.append(f"  {r['date'][:10]}  "
                       f"{r['agq']:.3f}  {r['cohesion']:.3f}    "
                       f"{r['isolated_pct']:5.1f}%    {r['cycle_pct']:4.1f}%")
        if len(trend_data) >= 2:
            first = next((r for r in trend_data if "agq" in r), None)
            last = next((r for r in reversed(trend_data) if "agq" in r), None)
            if first and last:
                d_agq = last["agq"] - first["agq"]
                d_coh = last["cohesion"] - first["cohesion"]
                d_iso = last["isolated_pct"] - first["isolated_pct"]
                arrow = lambda d: "↓" if d < -0.01 else "↑" if d > 0.01 else "→"
                out.append("")
                out.append(f"  Δ AGQ:        {d_agq:+.3f} {arrow(d_agq)}")
                out.append(f"  Δ cohesion:   {d_coh:+.3f} {arrow(d_coh)}")
                out.append(f"  Δ isolated:   {d_iso:+.1f}pp {arrow(d_iso)}")

    return "\n".join(out)
