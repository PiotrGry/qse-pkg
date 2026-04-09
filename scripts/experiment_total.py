#!/usr/bin/env python3
"""
experiment_total.py — Eksperyment totalny AGQ.

Pipeline:
  1. Klonuj repo z listy (--depth 1)
  2. Uruchom qse agq → zbierz metryki
  3. Zbierz ground truth z GitHub (bug lead time, PR revert rate)
  4. Oblicz nowe deskryptory (fan_in_gini, scc_entropy, fiedler)
  5. Korelacje → raport
  6. Powtarzaj per iteracja (--iter N)

Użycie:
  python3 experiment_total.py \
    --repos scripts/repos_experiment_total.json \
    --repos-dir /tmp/qse_total_bench \
    --output-dir artifacts/experiment_total \
    --iter 1 \
    --lang Python \
    --limit 50

Każda iteracja zapisuje:
  artifacts/experiment_total/iter_N/results.json
  artifacts/experiment_total/iter_N/results.md
  artifacts/experiment_total/iter_N/correlations.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ── opcjonalne importy naukowe ──────────────────────────────────────────────
try:
    import networkx as nx
    HAS_NX = True
except ImportError:
    HAS_NX = False
    print("[warn] networkx not available — structural descriptors disabled")

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


# ═══════════════════════════════════════════════════════════════════════════
# KLONOWANIE
# ═══════════════════════════════════════════════════════════════════════════

def clone(url: str, dest: Path, timeout: int = 300) -> bool:
    if dest.exists():
        return True
    print(f"  clone {url.split('/')[-1]}...", end="", flush=True)
    r = subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", url, str(dest)],
        capture_output=True, timeout=timeout
    )
    ok = r.returncode == 0
    print(" ok" if ok else " FAIL")
    return ok


# ═══════════════════════════════════════════════════════════════════════════
# AGQ — uruchomienie qse agq
# ═══════════════════════════════════════════════════════════════════════════

def run_agq(repo_path: Path, lang: str, timeout: int = 120) -> Optional[Dict]:
    """Uruchamia qse agq i parsuje wynik JSON."""
    t0 = time.time()
    r = subprocess.run(
        ["python3", "-m", "qse", "agq", str(repo_path),
         "--lang", lang, "--json"],
        capture_output=True, text=True, timeout=timeout
    )
    elapsed = round((time.time() - t0) * 1000)

    if r.returncode != 0:
        # Próba bez --json (starsze API)
        r2 = subprocess.run(
            ["python3", "-m", "qse", "agq", str(repo_path)],
            capture_output=True, text=True, timeout=timeout
        )
        if r2.returncode != 0:
            return None
        return _parse_agq_text(r2.stdout, elapsed, lang)

    try:
        data = json.loads(r.stdout)
        data["runtime_ms"] = elapsed
        data["language"] = lang
        return data
    except json.JSONDecodeError:
        return _parse_agq_text(r.stdout, elapsed, lang)


def _parse_agq_text(text: str, elapsed: int, lang: str) -> Optional[Dict]:
    """Parsuje tekstowy output qse agq."""
    import re
    patterns = {
        "agq_score":  r"AGQ[=:\s]+([0-9.]+)",
        "modularity": r"Modularity[=:\s]+([0-9.]+)",
        "acyclicity": r"Acyclicity[=:\s]+([0-9.]+)",
        "stability":  r"Stability[=:\s]+([0-9.]+)",
        "cohesion":   r"Cohesion[=:\s]+([0-9.]+)",
        "nodes":      r"[Nn]odes?[=:\s]+([0-9]+)",
    }
    result = {"runtime_ms": elapsed, "language": lang}
    for key, pat in patterns.items():
        m = re.search(pat, text)
        if m:
            result[key] = float(m.group(1))
    return result if "agq_score" in result else None


# ═══════════════════════════════════════════════════════════════════════════
# GROUND TRUTH — GitHub API
# ═══════════════════════════════════════════════════════════════════════════

def get_bug_lead_time(full_name: str, limit: int = 50) -> Optional[Dict]:
    """Pobiera czas naprawy bugów z GitHub Issues."""
    r = subprocess.run(
        ["gh", "api",
         f"repos/{full_name}/issues",
         "-X", "GET",
         "-f", "state=closed",
         "-f", "labels=bug",
         "-f", f"per_page={limit}",
         "--jq",
         "[.[] | select(.pull_request == null) | "
         "{created: .created_at, closed: .closed_at, "
         "comments: .comments}]"],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        issues = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    if not issues:
        return None

    lead_times = []
    for issue in issues:
        if issue.get("created") and issue.get("closed"):
            try:
                from datetime import datetime
                fmt = "%Y-%m-%dT%H:%M:%SZ"
                created = datetime.strptime(issue["created"], fmt)
                closed  = datetime.strptime(issue["closed"],  fmt)
                lead_times.append((closed - created).days)
            except Exception:
                pass

    if not lead_times:
        return None

    return {
        "n_bugs":          len(lead_times),
        "mean_lead_days":  round(statistics.mean(lead_times), 1),
        "median_lead_days":round(statistics.median(lead_times), 1),
        "p90_lead_days":   round(sorted(lead_times)[int(len(lead_times)*0.9)], 1),
    }


def get_churn(repo_path: Path, since: str = "2 years ago") -> Optional[Dict]:
    """Oblicza churn z git log."""
    r = subprocess.run(
        ["git", "-C", str(repo_path), "log", "--since", since,
         "--name-only", "--pretty=format:--COMMIT--"],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        return None
    counts: Dict[str, int] = {}
    import re
    test_re = re.compile(r"(^|/)tests?/|test_.*\.py$|_test\.(py|go|java)$|Test\.java$")
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
    n = len(sv)
    cum = sum((i+1)*v for i, v in enumerate(sv))
    gini = (2*cum)/(n*sum(sv)) - (n+1)/n if sum(sv) > 0 else 0.0
    return {
        "hotspot_ratio": round(hotspot, 4),
        "churn_gini":    round(gini, 4),
        "n_files":       n,
        "mean_churn":    round(mean_c, 3),
    }


# ═══════════════════════════════════════════════════════════════════════════
# NOWE DESKRYPTORY STRUKTURALNE
# ═══════════════════════════════════════════════════════════════════════════

def compute_structural_descriptors(repo_path: Path) -> Optional[Dict]:
    """
    Oblicza nowe deskryptory matematyczne na grafie zależności.
    Wymaga networkx. Graf budowany przez parsowanie importów Python.
    """
    if not HAS_NX:
        return None

    # Buduj graf importów Python
    G = nx.DiGraph()
    py_files = list(repo_path.rglob("*.py"))
    if len(py_files) < 5:
        return None

    import re
    import_re = re.compile(r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)

    pkg_root = repo_path.name
    for f in py_files[:500]:  # cap dla szybkości
        rel = str(f.relative_to(repo_path)).replace("/", ".").replace(".py", "")
        G.add_node(rel)
        try:
            src = f.read_text(errors="ignore")
        except Exception:
            continue
        for m in import_re.finditer(src):
            dep = (m.group(1) or m.group(2) or "").strip()
            if dep and dep.startswith(pkg_root.replace("-","_")):
                G.add_edge(rel, dep)

    n = G.number_of_nodes()
    if n < 5:
        return None

    # 1. Fan-in Gini (koncentracja zależności)
    in_degrees = [d for _, d in G.in_degree()]
    in_degrees_sorted = sorted(in_degrees)
    cum = sum((i+1)*v for i,v in enumerate(in_degrees_sorted))
    s = sum(in_degrees_sorted)
    fan_in_gini = (2*cum)/(n*s) - (n+1)/n if s > 0 else 0.0

    # 2. SCC Entropy
    sccs = list(nx.strongly_connected_components(G))
    scc_probs = [len(s)/n for s in sccs if len(s) > 0]
    scc_entropy = -sum(p*math.log2(p) for p in scc_probs if p > 0)
    scc_max_size = max(len(s) for s in sccs)
    n_cyclic_sccs = sum(1 for s in sccs if len(s) > 1)

    # 3. Fiedler value (λ₂) — algebraiczna łączność
    fiedler = None
    if HAS_NP and n <= 500:
        try:
            U = G.to_undirected()
            L = nx.laplacian_matrix(U).toarray().astype(float)
            eigenvalues = sorted(np.linalg.eigvalsh(L))
            fiedler = round(float(eigenvalues[1]), 6) if len(eigenvalues) > 1 else 0.0
        except Exception:
            pass

    # 4. Max betweenness centrality
    max_betweenness = None
    if n <= 300:
        try:
            bc = nx.betweenness_centrality(G, normalized=True)
            max_betweenness = round(max(bc.values()), 4) if bc else None
        except Exception:
            pass

    return {
        "fan_in_gini":      round(fan_in_gini, 4),
        "scc_entropy":      round(scc_entropy, 4),
        "scc_max_size":     scc_max_size,
        "n_cyclic_sccs":    n_cyclic_sccs,
        "fiedler_value":    fiedler,
        "max_betweenness":  max_betweenness,
        "graph_n_nodes":    n,
        "graph_n_edges":    G.number_of_edges(),
    }


# ═══════════════════════════════════════════════════════════════════════════
# KORELACJE
# ═══════════════════════════════════════════════════════════════════════════

def spearman(xs, ys):
    if len(xs) != len(ys) or len(xs) < 5:
        return None, None
    if HAS_SP:
        r, p = sp_stats.spearmanr(xs, ys)
        return round(float(r), 4), round(float(p), 4)
    # Fallback ręczny
    def rank(v):
        sv = sorted(enumerate(v), key=lambda x: x[1])
        r = [0.0]*len(v)
        i = 0
        while i < len(sv):
            j = i
            while j+1 < len(sv) and sv[j+1][1] == sv[i][1]: j += 1
            rv = (i+j+2)/2.0
            for k in range(i, j+1): r[sv[k][0]] = rv
            i = j+1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(rx)
    mx = sum(rx)/n; my = sum(ry)/n
    num = sum((a-mx)*(b-my) for a,b in zip(rx,ry))
    dx = math.sqrt(sum((a-mx)**2 for a in rx))
    dy = math.sqrt(sum((b-my)**2 for b in ry))
    r_s = num/(dx*dy) if dx*dy > 0 else 0.0
    # p aproximacja
    t = r_s * math.sqrt((n-2)/(1-r_s**2+1e-10))
    p = 2 * (1 - _t_cdf(abs(t), n-2))
    return round(r_s, 4), round(p, 4)

def _t_cdf(t, df):
    """Przybliżona CDF rozkładu t."""
    x = df / (df + t*t)
    # regularized incomplete beta
    a, b = df/2, 0.5
    return 1 - 0.5 * _betainc(x, a, b)

def _betainc(x, a, b):
    """Bardzo uproszczone przybliżenie."""
    return x**a * (1-x)**b / (a * __import__('math').gamma(a) * __import__('math').gamma(b) / __import__('math').gamma(a+b))


def compute_correlations(results: List[Dict]) -> Dict:
    """Oblicza korelacje Spearmana wszystkich par metryk."""
    # Zbierz pary
    agq_metrics = ["agq_score", "modularity", "acyclicity", "stability", "cohesion"]
    new_metrics  = ["fan_in_gini", "scc_entropy", "fiedler_value", "max_betweenness"]
    gt_metrics   = ["churn_gini", "hotspot_ratio", "mean_lead_days", "median_lead_days"]

    corr = {}

    def extract(key, source="agq"):
        vals = []
        for r in results:
            if source == "agq":
                v = r.get("agq", {}).get(key)
            elif source == "desc":
                v = r.get("descriptors", {}).get(key)
            elif source == "gt":
                c = r.get("churn") or {}
                b = r.get("bug_lead_time") or {}
                v = c.get(key) or b.get(key)
            else:
                v = None
            vals.append(v)
        return vals

    predictors = {
        **{k: ("agq", k) for k in agq_metrics},
        **{k: ("desc", k) for k in new_metrics},
    }
    targets = {k: ("gt", k) for k in gt_metrics}

    for pred_name, (pred_src, pred_key) in predictors.items():
        for tgt_name, (tgt_src, tgt_key) in targets.items():
            xs_raw = extract(pred_key, pred_src)
            ys_raw = extract(tgt_key, tgt_src)
            # Filtruj pary gdzie oba są dostępne
            pairs = [(x, y) for x, y in zip(xs_raw, ys_raw)
                     if x is not None and y is not None]
            if len(pairs) < 5:
                continue
            xs, ys = zip(*pairs)
            r_s, p = spearman(list(xs), list(ys))
            if r_s is not None:
                key = f"{pred_name} → {tgt_name}"
                corr[key] = {
                    "r_s": r_s, "p": p, "n": len(pairs),
                    "sig": p < 0.05 if p is not None else False,
                    "strength": _strength(r_s),
                }

    return corr

def _strength(r):
    a = abs(r)
    if a >= 0.7: return "strong"
    if a >= 0.5: return "moderate"
    if a >= 0.3: return "weak"
    return "very_weak"


# ═══════════════════════════════════════════════════════════════════════════
# RAPORT MARKDOWN
# ═══════════════════════════════════════════════════════════════════════════

def make_markdown(report: Dict, iter_n: int) -> str:
    lines = [
        f"# Eksperyment Totalny — Iteracja {iter_n}",
        "",
        f"- generated: `{report['generated_at']}`",
        f"- repos_ok: `{report['repos_ok']}`",
        f"- języki: {report['langs']}",
        f"- AGQ mean: `{report.get('agq_mean', 'n/a')}`",
        "",
        "## Najsilniejsze korelacje",
        "",
        "| Predyktor | Cel | r_s | p | n | Siła |",
        "|---|---|---:|---:|---:|---|",
    ]
    corr = report.get("correlations", {})
    # Posortuj po |r_s|
    sorted_corr = sorted(corr.items(), key=lambda x: abs(x[1]["r_s"]), reverse=True)
    for pair, c in sorted_corr[:20]:
        sig = " *" if c["sig"] else ""
        lines.append(
            f"| {pair.split(' → ')[0]} | {pair.split(' → ')[1]} | "
            f"{c['r_s']}{sig} | {c['p']} | {c['n']} | {c['strength']} |"
        )

    lines += [
        "",
        "## Wyniki per repo",
        "",
        "| Repo | Lang | AGQ | Acy | Stab | Coh | FanInGini | SCCEntropy | LeadDays | ChurnGini |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(report["results"], key=lambda x: x.get("agq", {}).get("agq_score", 0), reverse=True):
        a = r.get("agq", {})
        d = r.get("descriptors") or {}
        c = r.get("churn") or {}
        b = r.get("bug_lead_time") or {}
        lines.append(
            f"| {r['name']} | {r['lang']} "
            f"| {a.get('agq_score', 'n/a')} "
            f"| {a.get('acyclicity', 'n/a')} "
            f"| {a.get('stability', 'n/a')} "
            f"| {a.get('cohesion', 'n/a')} "
            f"| {d.get('fan_in_gini', 'n/a')} "
            f"| {d.get('scc_entropy', 'n/a')} "
            f"| {b.get('median_lead_days', 'n/a')} "
            f"| {c.get('churn_gini', 'n/a')} |"
        )
    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos",       default="scripts/repos_experiment_total.json")
    parser.add_argument("--repos-dir",   default="/tmp/qse_total_bench")
    parser.add_argument("--output-dir",  default="artifacts/experiment_total")
    parser.add_argument("--iter",        type=int, default=1)
    parser.add_argument("--lang",        default=None, help="Filtruj po języku")
    parser.add_argument("--limit",       type=int, default=None)
    parser.add_argument("--no-clone",    action="store_true")
    parser.add_argument("--no-lead-time",action="store_true", help="Pomiń GitHub Issues API")
    args = parser.parse_args()

    repos_dir = Path(args.repos_dir)
    repos_dir.mkdir(parents=True, exist_ok=True)
    output_dir = Path(args.output_dir) / f"iter_{args.iter}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Wczytaj listę repo
    repos_list = json.loads(Path(args.repos).read_text())
    if args.lang:
        repos_list = [r for r in repos_list if r.get("lang", "Python") == args.lang]
    if args.limit:
        repos_list = repos_list[:args.limit]

    print(f"Eksperyment totalny — iteracja {args.iter}")
    print(f"Repos: {len(repos_list)} | Lang: {args.lang or 'all'}")
    print(f"Output: {output_dir}")
    print("="*60)

    results = []
    for i, repo in enumerate(repos_list):
        name = repo["name"]
        url  = repo["url"]
        lang = repo.get("lang", "Python")
        full_name = repo.get("full_name", url.replace("https://github.com/",""))

        print(f"\n[{i+1}/{len(repos_list)}] {name} ({lang})")

        # 1. Klonuj
        dest = repos_dir / name
        if not args.no_clone:
            if not clone(url, dest):
                continue

        if not dest.exists():
            print(f"  skip (not cloned)")
            continue

        # 2. AGQ
        agq = run_agq(dest, lang)
        if not agq:
            print(f"  AGQ: FAIL")
            continue
        print(f"  AGQ: {agq.get('agq_score','?')} (A={agq.get('acyclicity','?')} S={agq.get('stability','?')} C={agq.get('cohesion','?')})")

        # 3. Churn
        churn = get_churn(dest)
        if churn:
            print(f"  Churn: gini={churn['churn_gini']} hotspot={churn['hotspot_ratio']}")

        # 4. Bug lead time (GitHub API)
        bug_lt = None
        if not args.no_lead_time and full_name and '/' in full_name:
            bug_lt = get_bug_lead_time(full_name)
            if bug_lt:
                print(f"  BugLT: median={bug_lt['median_lead_days']}d n={bug_lt['n_bugs']}")

        # 5. Nowe deskryptory strukturalne
        desc = None
        if lang == "Python":
            desc = compute_structural_descriptors(dest)
            if desc:
                print(f"  Desc: gini={desc['fan_in_gini']} scc_H={desc['scc_entropy']} fiedler={desc.get('fiedler_value','?')}")

        results.append({
            "name": name,
            "full_name": full_name,
            "lang": lang,
            "layer": repo.get("layer", "B"),
            "agq": agq,
            "churn": churn,
            "bug_lead_time": bug_lt,
            "descriptors": desc,
        })

    # 6. Korelacje
    print(f"\n{'='*60}")
    print(f"Obliczam korelacje na {len(results)} repo...")
    correlations = compute_correlations(results)

    # Wydrukuj top korelacje
    top = sorted(correlations.items(), key=lambda x: abs(x[1]["r_s"]), reverse=True)[:15]
    print("\nTop korelacje:")
    for pair, c in top:
        sig = " ***" if c["p"] < 0.001 else (" *" if c["p"] < 0.05 else "")
        print(f"  {pair:45} r={c['r_s']:+.3f} p={c['p']:.3f}{sig} [{c['strength']}]")

    # 7. Zapisz wyniki
    agq_vals = [r["agq"]["agq_score"] for r in results if r.get("agq",{}).get("agq_score")]
    langs = list(set(r["lang"] for r in results))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "iter": args.iter,
        "repos_ok": len(results),
        "langs": ", ".join(sorted(langs)),
        "agq_mean": round(statistics.mean(agq_vals), 4) if agq_vals else None,
        "agq_std":  round(statistics.pstdev(agq_vals), 4) if agq_vals else None,
        "correlations": correlations,
        "results": results,
    }

    (output_dir / "results.json").write_text(json.dumps(report, indent=2))
    (output_dir / "results.md").write_text(make_markdown(report, args.iter))
    (output_dir / "correlations.json").write_text(json.dumps(correlations, indent=2))

    print(f"\nZapisano: {output_dir}/results.{{json,md}}")
    print(f"Repos OK: {len(results)}")
    if agq_vals:
        print(f"AGQ: mean={statistics.mean(agq_vals):.4f} std={statistics.pstdev(agq_vals):.4f}")


if __name__ == "__main__":
    main()
