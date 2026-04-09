#!/usr/bin/env python3
"""
experiment_total.py — Benchmark totalny AGQ, iteracja 3+

Pipeline per repo:
  1. Klonuj (--depth 1)
  2. qse agq → AGQ score + składowe
  3. Nowe metryki z graph_metrics.py:
       compute_graph_density, compute_scc_entropy, compute_hub_ratio
  4. Bug fix lead time z GitHub Issues
  5. Churn z git log
  6. Korelacje Spearmana wszystkich par predyktor × ground truth
  7. Raport + commit na branch perplexity

Użycie (od zera):
  python3 scripts/experiment_total.py \
    --repos scripts/repos_experiment_total.json \
    --repos-dir ~/qse_total_bench \
    --output-dir artifacts/experiment_total \
    --iter 3

Użycie (kontynuacja — pomija już sklonowane):
  python3 scripts/experiment_total.py ... --no-reclone
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Naukowe ────────────────────────────────────────────────────────────────
try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False
    print("[warn] networkx missing — install: pip install networkx")

try:
    import numpy as np
    HAS_NP = True
except ImportError:
    HAS_NP = False

try:
    from scipy import stats as sp_stats
    HAS_SP = True
except ImportError:
    HAS_SP = False

# ── QSE własne metryki (jeśli pakiet zainstalowany) ───────────────────────
try:
    from qse.graph_metrics import (
        compute_graph_density, compute_density_score,
        compute_scc_entropy, compute_scc_entropy_score,
        compute_hub_ratio, compute_hub_score,
    )
    HAS_QSE_METRICS = True
except ImportError:
    HAS_QSE_METRICS = False
    print("[warn] qse.graph_metrics not importable — using built-in fallback")


# ═══════════════════════════════════════════════════════════════════════════
# KLONOWANIE
# ═══════════════════════════════════════════════════════════════════════════

def clone_repo(url: str, dest: Path, timeout: int = 300) -> bool:
    if dest.exists():
        return True
    print(f"    clone {url.split('/')[-1]}...", end="", flush=True)
    r = subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", url, str(dest)],
        capture_output=True, timeout=timeout
    )
    ok = r.returncode == 0
    print(" ok" if ok else f" FAIL ({r.stderr[:80].decode(errors='ignore')})")
    return ok


# ═══════════════════════════════════════════════════════════════════════════
# AGQ — qse agq CLI
# ═══════════════════════════════════════════════════════════════════════════

def run_agq(repo_path: Path, lang: str, timeout: int = 180) -> Optional[Dict]:
    """Uruchamia qse agq i zwraca dict z metrykami.

    qse agq API:
      qse agq <path> [--output-json FILE] [--threshold N]
      Nie ma --lang — skaner Rust auto-wykrywa język.
      Output JSON zapisywany do pliku (nie do stdout).
    """
    import tempfile
    t0 = time.time()

    # Zapisz JSON output do pliku tymczasowego
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        json_out = tf.name

    try:
        r = subprocess.run(
            [sys.executable, "-m", "qse", "agq", str(repo_path),
             "--output-json", json_out, "--threshold", "0.0"],
            capture_output=True, text=True, timeout=timeout
        )
        elapsed_ms = round((time.time() - t0) * 1000)

        # Próba odczytu JSON
        json_path = Path(json_out)
        if json_path.exists() and json_path.stat().st_size > 0:
            try:
                d = json.loads(json_path.read_text())
                # Normalizuj strukturę — qse agq zwraca metrics jako sub-dict
                result = {
                    "agq_score":  d.get("agq_score"),
                    "language":   d.get("language", lang),
                    "nodes":      d.get("graph", {}).get("nodes", 0),
                    "edges":      d.get("graph", {}).get("edges", 0),
                    "modularity": d.get("metrics", {}).get("modularity"),
                    "acyclicity": d.get("metrics", {}).get("acyclicity"),
                    "stability":  d.get("metrics", {}).get("stability"),
                    "cohesion":   d.get("metrics", {}).get("cohesion"),
                    "runtime_ms": elapsed_ms,
                    "gate":       d.get("gate"),
                }
                if result["agq_score"] is not None:
                    return result
            except Exception:
                pass

        # Fallback: parsowanie tekstu ze stdout+stderr
        text = r.stdout + r.stderr
        if text.strip():
            return _parse_agq_text(text, elapsed_ms, lang)

        return None

    finally:
        try:
            Path(json_out).unlink(missing_ok=True)
        except Exception:
            pass


def _parse_agq_text(text: str, elapsed_ms: int, lang: str) -> Optional[Dict]:
    patterns = {
        "agq_score":  r"AGQ[=:\s]+([0-9.]+)",
        "modularity": r"[Mm]odularity[=:\s]+([0-9.]+)",
        "acyclicity": r"[Aa]cyclicity[=:\s]+([0-9.]+)",
        "stability":  r"[Ss]tability[=:\s]+([0-9.]+)",
        "cohesion":   r"[Cc]ohesion[=:\s]+([0-9.]+)",
        "nodes":      r"[Nn]odes?[=:\s]+([0-9]+)",
        "edges":      r"[Ee]dges?[=:\s]+([0-9]+)",
    }
    result: Dict = {"runtime_ms": elapsed_ms, "language": lang}
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            result[key] = float(m.group(1))
    return result if "agq_score" in result else None


# ═══════════════════════════════════════════════════════════════════════════
# NOWE METRYKI — graph_metrics.py (z fallbackiem)
# ═══════════════════════════════════════════════════════════════════════════

def build_import_graph(repo_path: Path) -> Optional["nx.DiGraph"]:
    """Buduje graf importów Python z repo."""
    if not HAS_NX:
        return None
    py_files = list(repo_path.rglob("*.py"))
    if len(py_files) < 5:
        return None

    G = nx.DiGraph()
    pkg = repo_path.name.replace("-", "_").replace(".", "_").lower()
    dirs = {p.name.replace("-", "_").lower()
            for p in repo_path.iterdir() if p.is_dir()}
    imp_re = re.compile(r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)

    for f in py_files[:800]:
        rel = str(f.relative_to(repo_path)).replace("/", ".")
        if rel.endswith(".py"):
            rel = rel[:-3]
        G.add_node(rel)
        try:
            src = f.read_text(errors="ignore")
        except Exception:
            continue
        for m in imp_re.finditer(src):
            dep = (m.group(1) or m.group(2) or "").strip()
            root = dep.split(".")[0].lower()
            if dep and (root == pkg or root in dirs):
                G.add_edge(rel, dep)

    return G if G.number_of_nodes() >= 5 else None


def compute_new_metrics(repo_path: Path, lang: str) -> Optional[Dict]:
    """
    Oblicza GraphDensity, SCCEntropy, HubRatio i ich znormalizowane scores.
    Używa qse.graph_metrics jeśli dostępne, inaczej fallback wbudowany.
    """
    # Tylko Python na razie (skaner grafowy wymaga parsowania importów)
    if lang not in ("Python",):
        return None

    G = build_import_graph(repo_path)
    if G is None:
        return None

    n = G.number_of_nodes()
    e = G.number_of_edges()

    if HAS_QSE_METRICS:
        # Używaj zwalidowanych funkcji z qse.graph_metrics
        density     = compute_graph_density(G)
        d_score     = compute_density_score(density)
        scc_h       = compute_scc_entropy(G)
        scc_score   = compute_scc_entropy_score(G)
        hub_r       = compute_hub_ratio(G)
        hub_s       = compute_hub_score(hub_r)
    else:
        # Fallback — wbudowane obliczenia
        density = round(e / (n * (n - 1)), 6) if n > 1 else 0.0
        d_score = round(max(0.0, 1.0 - min(1.0, density / 0.020)), 4)

        sccs    = list(nx.strongly_connected_components(G))
        probs   = [len(c) / n for c in sccs]
        scc_h   = round(-sum(p * math.log2(p) for p in probs if p > 0), 4)
        max_h   = math.log2(max(n, 2))
        scc_score = round(min(1.0, scc_h / max_h), 4) if max_h > 0 else 1.0

        in_deg  = [d for _, d in G.in_degree()]
        mean_in = sum(in_deg) / n if n > 0 else 0.0
        hub_r   = round(sum(1 for d in in_deg if d > 2 * mean_in) / n, 4)
        hub_s   = round(1.0 - hub_r, 4)

    # ProcessRisk (wagi z kalibracji pilotażu iter-2)
    W_D, W_S, W_H = 0.4136, 0.3005, 0.2859
    process_quality = W_D * d_score + W_S * scc_score + W_H * hub_s
    process_risk    = round(1.0 - process_quality, 4)

    return {
        "graph_density":     density,
        "density_score":     d_score,
        "scc_entropy":       scc_h,
        "scc_entropy_score": scc_score,
        "hub_ratio":         hub_r,
        "hub_score":         hub_s,
        "process_risk":      process_risk,
        "n_nodes":           n,
        "n_edges":           e,
    }


# ═══════════════════════════════════════════════════════════════════════════
# GROUND TRUTH — GitHub Issues + git churn
# ═══════════════════════════════════════════════════════════════════════════

def get_bug_lead_time(full_name: str, limit: int = 100) -> Optional[Dict]:
    r = subprocess.run(
        ["gh", "api", f"repos/{full_name}/issues",
         "-X", "GET", "-f", "state=closed", "-f", "labels=bug",
         "-f", f"per_page={limit}",
         "--jq",
         "[.[] | select(.pull_request == null) | "
         "{c:.created_at, cl:.closed_at}]"],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        issues = json.loads(r.stdout)
    except Exception:
        return None
    if not issues:
        return None

    fmt = "%Y-%m-%dT%H:%M:%SZ"
    lead_times = []
    for issue in issues:
        try:
            from datetime import datetime as _dt
            c  = _dt.strptime(issue["c"],  fmt)
            cl = _dt.strptime(issue["cl"], fmt)
            lead_times.append((cl - c).days)
        except Exception:
            pass

    if not lead_times:
        return None

    lt = sorted(lead_times)
    n  = len(lt)
    return {
        "n_bugs":           n,
        "mean_lead_days":   round(statistics.mean(lt), 1),
        "median_lead_days": round(statistics.median(lt), 1),
        "p75_lead_days":    round(lt[int(n * 0.75)], 1),
        "p90_lead_days":    round(lt[min(int(n * 0.90), n - 1)], 1),
    }


def get_churn(repo_path: Path, since: str = "2 years ago") -> Optional[Dict]:
    r = subprocess.run(
        ["git", "-C", str(repo_path), "log",
         "--since", since, "--name-only", "--pretty=format:--COMMIT--"],
        capture_output=True, text=True, timeout=90
    )
    if r.returncode != 0:
        return None

    test_re = re.compile(
        r"(^|/)tests?/|test_.*\.(py|go|java)$|_test\.(py|go|java)$|Test\.java$")
    counts: Dict[str, int] = {}
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line or line == "--COMMIT--":
            continue
        if test_re.search(line):
            continue
        counts[line] = counts.get(line, 0) + 1

    if not counts:
        return None

    vals = list(counts.values())
    mean_c = sum(vals) / len(vals)
    hotspot = sum(1 for v in vals if v > mean_c * 2) / len(vals)
    sv = sorted(vals)
    n  = len(sv)
    cum = sum((i + 1) * v for i, v in enumerate(sv))
    gini = (2 * cum) / (n * sum(sv)) - (n + 1) / n if sum(sv) > 0 else 0.0

    return {
        "hotspot_ratio": round(hotspot, 4),
        "churn_gini":    round(gini, 4),
        "n_files":       n,
        "mean_churn":    round(mean_c, 3),
    }


# ═══════════════════════════════════════════════════════════════════════════
# KORELACJE
# ═══════════════════════════════════════════════════════════════════════════

def spearman_r(xs: List[float], ys: List[float]) -> Tuple[float, float]:
    if HAS_SP:
        r, p = sp_stats.spearmanr(xs, ys)
        return round(float(r), 4), round(float(p), 4)
    # Fallback ręczny
    n = len(xs)
    def rank(v):
        sv = sorted(enumerate(v), key=lambda x: x[1])
        r = [0.0] * n
        i = 0
        while i < len(sv):
            j = i
            while j + 1 < len(sv) and sv[j+1][1] == sv[i][1]: j += 1
            rv = (i + j + 2) / 2.0
            for k in range(i, j+1): r[sv[k][0]] = rv
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx = sum(rx)/n; my = sum(ry)/n
    num = sum((a-mx)*(b-my) for a, b in zip(rx, ry))
    dx  = math.sqrt(sum((a-mx)**2 for a in rx))
    dy  = math.sqrt(sum((b-my)**2 for b in ry))
    r_s = num / (dx * dy) if dx * dy > 0 else 0.0
    t = r_s * math.sqrt((n-2) / max(1e-10, 1 - r_s**2))
    # p ≈ via normal approximation for large n
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return round(r_s, 4), round(p, 4)


def compute_all_correlations(results: List[Dict]) -> List[Dict]:
    def extract(key: str, src: str) -> List[Optional[float]]:
        out = []
        for r in results:
            if src == "agq":
                v = (r.get("agq") or {}).get(key)
            elif src == "new":
                v = (r.get("new_metrics") or {}).get(key)
            elif src == "churn":
                v = (r.get("churn") or {}).get(key)
            elif src == "bug":
                v = (r.get("bug_lead_time") or {}).get(key)
            else:
                v = None
            out.append(v)
        return out

    PREDICTORS = [
        ("agq_score",        "agq", "AGQ"),
        ("modularity",       "agq", "Modularity"),
        ("acyclicity",       "agq", "Acyclicity"),
        ("stability",        "agq", "Stability"),
        ("cohesion",         "agq", "Cohesion"),
        ("graph_density",    "new", "GraphDensity   [NEW]"),
        ("density_score",    "new", "DensityScore   [NEW]"),
        ("scc_entropy",      "new", "SCCEntropy     [NEW]"),
        ("scc_entropy_score","new", "SCCEntScore    [NEW]"),
        ("hub_ratio",        "new", "HubRatio       [NEW]"),
        ("hub_score",        "new", "HubScore       [NEW]"),
        ("process_risk",     "new", "ProcessRisk    [NEW]"),
    ]

    TARGETS = [
        ("churn_gini",       "churn", "churn_gini"),
        ("hotspot_ratio",    "churn", "hotspot_ratio"),
        ("median_lead_days", "bug",   "bug_median_days"),
        ("mean_lead_days",   "bug",   "bug_mean_days"),
    ]

    corrs = []
    for pk, ps, pl in PREDICTORS:
        for tk, ts, tl in TARGETS:
            xs_raw = extract(pk, ps)
            ys_raw = extract(tk, ts)
            pairs  = [
                (x, y) for x, y in zip(xs_raw, ys_raw)
                if x is not None and y is not None
                and not math.isnan(float(x)) and not math.isnan(float(y))
            ]
            if len(pairs) < 5:
                continue
            xs, ys = zip(*pairs)
            r_s, p = spearman_r(list(xs), list(ys))
            if math.isnan(r_s):
                continue
            corrs.append({
                "predictor": pl,
                "target":    tl,
                "r_s":       r_s,
                "p":         p,
                "n":         len(pairs),
                "sig":       bool(p < 0.05),
                "abs_r":     abs(r_s),
                "strength": (
                    "strong"    if abs(r_s) >= 0.7 else
                    "moderate"  if abs(r_s) >= 0.5 else
                    "weak"      if abs(r_s) >= 0.3 else
                    "very_weak"
                ),
            })

    return sorted(corrs, key=lambda x: x["abs_r"], reverse=True)


# ═══════════════════════════════════════════════════════════════════════════
# MARKDOWN RAPORT
# ═══════════════════════════════════════════════════════════════════════════

def make_markdown(report: Dict) -> str:
    iter_n = report["iter"]
    corrs  = report["correlations"]
    lines  = [
        f"# Eksperyment Totalny — Iteracja {iter_n}",
        "",
        f"- generated: `{report['generated_at']}`",
        f"- repos_ok: `{report['repos_ok']}`",
        f"- langs: `{report['langs']}`",
        f"- AGQ mean: `{report.get('agq_mean', 'n/a')}`",
        f"- repos z nowymi metrykami: `{report.get('repos_with_new_metrics', 0)}`",
        f"- repos z bug lead time: `{report.get('repos_with_bug_lt', 0)}`",
        "",
        "## Najsilniejsze korelacje (top 20)",
        "",
        "| Predyktor | → Cel | r_s | p | n | Siła |",
        "|---|---|---:|---:|---:|---|",
    ]
    for c in corrs[:20]:
        sig = " *" if c["sig"] else ""
        new = " ◄" if "[NEW]" in c["predictor"] else ""
        lines.append(
            f"| {c['predictor'].strip()}{new} | {c['target']} "
            f"| {c['r_s']}{sig} | {c['p']} | {c['n']} | {c['strength']} |"
        )

    lines += [
        "",
        "## Wyniki per repo",
        "",
        "| Repo | Lang | AGQ | Acy | Stab | Coh | Density | SCCEnt | HubR | ProcessRisk | ChurnGini | BugMedian |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(
        report["results"],
        key=lambda x: (x.get("agq") or {}).get("agq_score", 0),
        reverse=True
    ):
        a  = r.get("agq") or {}
        nm = r.get("new_metrics") or {}
        c  = r.get("churn") or {}
        b  = r.get("bug_lead_time") or {}
        lines.append(
            f"| {r['name']} | {r['lang']} "
            f"| {a.get('agq_score', '-')} "
            f"| {a.get('acyclicity', '-')} "
            f"| {a.get('stability', '-')} "
            f"| {a.get('cohesion', '-')} "
            f"| {nm.get('graph_density', '-')} "
            f"| {nm.get('scc_entropy', '-')} "
            f"| {nm.get('hub_ratio', '-')} "
            f"| {nm.get('process_risk', '-')} "
            f"| {c.get('churn_gini', '-')} "
            f"| {b.get('median_lead_days', '-')} |"
        )
    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    p = argparse.ArgumentParser(description="QSE Benchmark Totalny")
    p.add_argument("--repos",         default="scripts/repos_experiment_total.json")
    p.add_argument("--repos-dir",     default=str(Path.home() / "qse_total_bench"))
    p.add_argument("--output-dir",    default="artifacts/experiment_total")
    p.add_argument("--iter",          type=int, default=3)
    p.add_argument("--lang",          default=None, help="Filtruj język: Python/Java/Go/TypeScript")
    p.add_argument("--limit",         type=int, default=None, help="Max repo do przeskanowania")
    p.add_argument("--no-reclone",    action="store_true", help="Pomiń klonowanie (używaj istniejących)")
    p.add_argument("--no-lead-time",  action="store_true", help="Pomiń GitHub Issues API")
    p.add_argument("--workers",       type=int, default=1, help="Równoległa praca (eksperymentalne)")
    args = p.parse_args()

    repos_dir  = Path(args.repos_dir)
    output_dir = Path(args.output_dir) / f"iter_{args.iter}"
    repos_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Wczytaj listę repo
    repos_file = Path(args.repos)
    if not repos_file.exists():
        print(f"BŁĄD: {repos_file} nie istnieje")
        sys.exit(1)

    repo_list = json.loads(repos_file.read_text())
    if args.lang:
        repo_list = [r for r in repo_list if r.get("lang", "Python") == args.lang]
    if args.limit:
        repo_list = repo_list[: args.limit]

    print("=" * 65)
    print(f"QSE Benchmark Totalny — iteracja {args.iter}")
    print("=" * 65)
    print(f"Repos: {len(repo_list)} | Lang: {args.lang or 'all'}")
    print(f"Repos dir: {repos_dir}")
    print(f"Output:    {output_dir}")
    print(f"QSE metrics: {'qse.graph_metrics' if HAS_QSE_METRICS else 'built-in fallback'}")
    print()

    results = []
    failed  = []

    for i, repo in enumerate(repo_list):
        name      = repo["name"]
        url       = repo["url"]
        lang      = repo.get("lang", "Python")
        full_name = repo.get("full_name", url.replace("https://github.com/", ""))
        layer     = repo.get("layer", "B")
        dest      = repos_dir / name

        print(f"[{i+1:4}/{len(repo_list)}] {name} ({lang}, Layer={layer})")

        # 1. Klonuj
        if not args.no_reclone:
            if not clone_repo(url, dest):
                failed.append(name)
                continue
        elif not dest.exists():
            print(f"    skip (not cloned, use without --no-reclone)")
            continue

        # 2. AGQ
        agq = run_agq(dest, lang)
        if not agq:
            print(f"    AGQ: FAIL")
            failed.append(name)
            continue
        print(f"    AGQ={agq.get('agq_score', '?'):.4f}  "
              f"A={agq.get('acyclicity', '?'):.3f}  "
              f"S={agq.get('stability', '?'):.3f}  "
              f"C={agq.get('cohesion', '?'):.3f}  "
              f"({agq.get('runtime_ms', '?')}ms)")

        # 3. Nowe metryki grafowe
        new_m = compute_new_metrics(dest, lang)
        if new_m:
            print(f"    density={new_m['graph_density']:.5f}  "
                  f"scc_H={new_m['scc_entropy']:.3f}  "
                  f"hub={new_m['hub_ratio']:.3f}  "
                  f"risk={new_m['process_risk']:.3f}")

        # 4. Churn
        churn = get_churn(dest)
        if churn:
            print(f"    churn_gini={churn['churn_gini']}  "
                  f"hotspot={churn['hotspot_ratio']}")

        # 5. Bug lead time
        bug_lt = None
        if not args.no_lead_time and "/" in full_name:
            bug_lt = get_bug_lead_time(full_name)
            if bug_lt:
                print(f"    bug_median={bug_lt['median_lead_days']}d  "
                      f"n={bug_lt['n_bugs']}")

        results.append({
            "name":          name,
            "lang":          lang,
            "layer":         layer,
            "full_name":     full_name,
            "agq":           agq,
            "new_metrics":   new_m,
            "churn":         churn,
            "bug_lead_time": bug_lt,
        })

    # Korelacje
    print(f"\n{'='*65}")
    print(f"Obliczam korelacje ({len(results)} repo)...")
    correlations = compute_all_correlations(results)

    # Wydruk top korelacji
    print(f"\n{'Predyktor':30} {'→ Cel':22} {'r_s':>7} {'p':>7} {'n':>4}  Siła")
    print("-" * 80)
    for c in correlations[:15]:
        sig = "***" if c["p"] < 0.001 else "** " if c["p"] < 0.01 else "*  " if c["p"] < 0.05 else "   "
        new = " ◄" if "[NEW]" in c["predictor"] else ""
        print(f"  {c['predictor'].strip():28} {c['target']:22} "
              f"{c['r_s']:+7.4f} {c['p']:7.4f} {c['n']:4}  {sig} {c['strength']}{new}")

    # Zapisz
    agq_vals = [r["agq"]["agq_score"] for r in results
                if (r.get("agq") or {}).get("agq_score") is not None]
    langs    = sorted(set(r["lang"] for r in results))

    report = {
        "generated_at":          datetime.now(timezone.utc).isoformat(),
        "iter":                  args.iter,
        "repos_ok":              len(results),
        "repos_failed":          len(failed),
        "langs":                 ", ".join(langs),
        "agq_mean":              round(statistics.mean(agq_vals), 4) if agq_vals else None,
        "agq_std":               round(statistics.pstdev(agq_vals), 4) if agq_vals else None,
        "repos_with_new_metrics":sum(1 for r in results if r.get("new_metrics")),
        "repos_with_bug_lt":     sum(1 for r in results if r.get("bug_lead_time")),
        "correlations":          correlations,
        "results":               results,
        "failed":                failed,
    }

    (output_dir / "results.json").write_text(json.dumps(report, indent=2))
    (output_dir / "results.md").write_text(make_markdown(report))
    (output_dir / "correlations.json").write_text(
        json.dumps(correlations, indent=2))

    # Podsumowanie
    print(f"\n{'='*65}")
    print("PODSUMOWANIE")
    print(f"{'='*65}")
    print(f"  Repos OK:      {len(results)}")
    print(f"  Repos FAILED:  {len(failed)}")
    print(f"  Z AGQ:         {len(agq_vals)}")
    print(f"  Z nowymi mtr.: {report['repos_with_new_metrics']}")
    print(f"  Z bug lead:    {report['repos_with_bug_lt']}")
    if agq_vals:
        print(f"  AGQ mean:      {statistics.mean(agq_vals):.4f}")

    sig_new = [c for c in correlations if c["sig"] and "[NEW]" in c["predictor"]]
    if sig_new:
        print(f"\n  Istotne nowe metryki (p<0.05):")
        for c in sig_new[:5]:
            print(f"    {c['predictor'].strip():28} → {c['target']:18} "
                  f"r={c['r_s']:+.4f} p={c['p']:.4f}")

    print(f"\n  JSON:  {output_dir}/results.json")
    print(f"  MD:    {output_dir}/results.md")
    print(f"\n  Aby wrzucić na GitHub:")
    print(f"    git add artifacts/experiment_total/")
    print(f"    git commit -m 'experiment: iter {args.iter} results — {len(results)} repos'")
    print(f"    git push origin perplexity")


if __name__ == "__main__":
    main()
