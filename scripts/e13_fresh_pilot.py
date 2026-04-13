#!/usr/bin/env python3
"""
E13: Fresh pilot with three-layer QSE framework.

New repos NOT in GT (n=52) or E12 (n=14).
Uses java_scanner directly (not CLI) for proper multi-module support.

Three-layer output per repo:
  1. QSE-Rank:       rank(C)+rank(S) vs GT benchmark
  2. QSE-Track:      M, PCA, dip_violations, largest_scc
  3. QSE-Diagnostic: full decomposition + problem flags
"""

import json
import os
import sys
import subprocess
import shutil
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent))

from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
from qse.graph_metrics import (
    AGQMetrics,
    compute_agq,
    compute_structural_health,
    compute_qse_rank,
    compute_qse_track,
    compute_qse_diagnostic,
    GT_BENCHMARK_C,
    GT_BENCHMARK_S,
)

# ── New repos ──────────────────────────────────────────────────────────
NEW_REPOS = [
    # POS — well-architected
    ("AxonFramework/AxonFramework", "POS",
     "CQRS/ES framework, explicit bounded contexts, clean module separation"),
    ("camunda/camunda-bpm-platform", "POS",
     "Process engine, modular architecture, well-defined API layers"),
    ("apache/flink", "POS",
     "Stream processing engine, clear layered architecture, modular runtime"),
    ("dropwizard/dropwizard", "POS",
     "REST framework, small focused modules, clean separation of concerns"),
    ("micronaut-projects/micronaut-core", "POS",
     "Modern DI framework, compile-time processing, well-layered modules"),
    ("quarkusio/quarkus", "POS",
     "Cloud-native Java framework, extension-based architecture"),
    ("eclipse-store/store", "POS",
     "Java-native object graph persistence, clean API design"),
    # NEG — known architectural problems
    ("elastic/elasticsearch", "NEG",
     "Massive monolith, deep coupling, god classes"),
    ("TheAlgorithms/Java", "NEG",
     "Algorithm collection, no real architecture, flat utility classes"),
    ("Anuken/Mindustry", "NEG",
     "Game engine monolith, tight coupling, global state"),
    ("dbeaver/dbeaver", "NEG",
     "Eclipse-based DB tool, plugin spaghetti, deep inheritance"),
    ("NationalSecurityAgency/ghidra", "NEG",
     "Reverse engineering tool, massive legacy codebase"),
    ("termux/termux-app", "NEG",
     "Android terminal, messy Android patterns, tight coupling"),
    # AMB — ambiguous
    ("ReactiveX/RxJava", "AMB",
     "Reactive library, focused but complex internal operator graph"),
]


def scan_one(repo_slug: str) -> dict:
    """Clone, scan, return three-layer QSE results."""
    safe = repo_slug.replace("/", "_")
    dest = f"/tmp/e13_scan_{safe}"
    if os.path.exists(dest):
        shutil.rmtree(dest)

    try:
        url = f"https://git-agent-proxy.perplexity.ai/{repo_slug}"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, dest],
            capture_output=True, text=True, timeout=180
        )
        if result.returncode != 0:
            return {"error": f"clone_failed: {result.stderr[:200]}"}

        scan = scan_java_repo(dest)
        if not scan or scan.graph.number_of_nodes() < 5:
            n = scan.graph.number_of_nodes() if scan else 0
            return {"error": f"too_few_nodes ({n})"}

        graph, abstract_modules, lcom4 = scan_result_to_agq_inputs(scan)
        agq = compute_agq(graph, abstract_modules, lcom4)
        health = compute_structural_health(graph, scan.internal_nodes, scan.packages)

        n_nodes = graph.number_of_nodes()
        n_edges = graph.number_of_edges()
        n_pkgs = len(scan.packages)

        # ── Layer 1: QSE-Rank ──
        qse_rank_score = compute_qse_rank(agq, GT_BENCHMARK_C, GT_BENCHMARK_S)
        c_pct = float(np.mean(np.array(GT_BENCHMARK_C) <= agq.cohesion))
        s_pct = float(np.mean(np.array(GT_BENCHMARK_S) <= agq.stability))

        # ── Layer 2: QSE-Track ──
        track = compute_qse_track(graph, scan.internal_nodes, scan.packages)

        # ── Layer 3: QSE-Diagnostic ──
        diagnostic = compute_qse_diagnostic(
            graph, agq, GT_BENCHMARK_C, GT_BENCHMARK_S,
            scan.internal_nodes, scan.packages
        )

        return {
            "qse_rank": round(qse_rank_score, 4),
            "c_pct": round(c_pct, 4),
            "s_pct": round(s_pct, 4),
            "track": track,
            "diagnostic": diagnostic,
            "agq_raw": round((agq.modularity + agq.acyclicity + agq.stability + agq.cohesion) / 4, 4),
            "agq_v3c": round(agq.agq_v3c, 4),
            "M": round(agq.modularity, 4),
            "A": round(agq.acyclicity, 4),
            "S": round(agq.stability, 4),
            "C": round(agq.cohesion, 4),
            "CD": round(agq.coupling_density, 4),
            "PCA": health['pca'],
            "LVR": health['lvr'],
            "SH": health['combined'],
            "nodes": n_nodes, "edges": n_edges, "n_packages": n_pkgs,
        }
    except Exception as e:
        return {"error": str(e)[:300]}
    finally:
        if os.path.exists(dest):
            shutil.rmtree(dest, ignore_errors=True)


# ── Main ───────────────────────────────────────────────────────────────

print("=" * 80)
print("E13: FRESH PILOT — THREE-LAYER QSE FRAMEWORK")
print("=" * 80)
print(f"Date: {datetime.now(timezone.utc).isoformat()}")
print(f"New repos: {len(NEW_REPOS)}")
print(f"GT benchmark: n={len(GT_BENCHMARK_C)}")
print()

results = []
for repo_slug, expected_cat, desc in NEW_REPOS:
    print(f"[{expected_cat}] Scanning {repo_slug}...", flush=True)
    metrics = scan_one(repo_slug)

    result = {
        "repo": repo_slug,
        "expected_cat": expected_cat,
        "desc": desc,
    }

    if "error" in metrics:
        result["error"] = metrics["error"]
        print(f"  ERROR: {metrics['error'][:80]}")
    else:
        result.update(metrics)
        diag = metrics["diagnostic"]
        probs = diag["problems"]
        prob_str = ", ".join(probs) if probs else "none"
        print(f"  QSE-Rank={metrics['qse_rank']:.3f}  AGQ={metrics['agq_v3c']:.3f}  "
              f"Track: M={metrics['track']['M']:.2f} PCA={metrics['track']['PCA']:.2f} "
              f"dip={metrics['track']['dip_violations']} scc={metrics['track']['largest_scc']}  "
              f"nodes={metrics['nodes']}  [{prob_str}]")

    results.append(result)

# ── Analysis ───────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

valid = [r for r in results if "error" not in r and r["expected_cat"] in ("POS", "NEG")]
pos = [r for r in valid if r["expected_cat"] == "POS"]
neg = [r for r in valid if r["expected_cat"] == "NEG"]
print(f"\nValid POS/NEG: {len(valid)} (POS={len(pos)}, NEG={len(neg)})")

if len(pos) >= 2 and len(neg) >= 2:
    for metric_name, key in [("QSE-Rank", "qse_rank"), ("AGQ_v3c", "agq_v3c"),
                               ("C alone", "C"), ("S alone", "S")]:
        pos_vals = [r[key] for r in pos]
        neg_vals = [r[key] for r in neg]
        all_vals = np.array([r[key] for r in valid])
        labels = np.array([1 if r["expected_cat"] == "POS" else 0 for r in valid])

        mw = stats.mannwhitneyu(pos_vals, neg_vals, alternative="greater")
        rpb, p_rpb = stats.pointbiserialr(labels, all_vals)
        auc_val = sum(1.0 if p > n else 0.5 if p == n else 0.0
                      for p in pos_vals for n in neg_vals) / (len(pos_vals) * len(neg_vals))
        sig = "**" if mw.pvalue < 0.01 else "*" if mw.pvalue < 0.05 else " "

        print(f"\n  {metric_name}:")
        print(f"    POS mean={np.mean(pos_vals):.3f}  NEG mean={np.mean(neg_vals):.3f}")
        print(f"    MW p={mw.pvalue:.4f}{sig}  rpb={rpb:+.3f} (p={p_rpb:.4f})  AUC={auc_val:.3f}")

    # ── Classification table ──
    print(f"\n  {'Repo':<42} {'Cat':>4} {'QSE-R':>7} {'AGQ':>6} {'Pred':>5} {'OK?':>4} {'Track':<30} {'Problems'}")
    print("  " + "-" * 120)

    correct = 0
    for r in sorted(valid, key=lambda x: x["qse_rank"], reverse=True):
        pred = "POS" if r["qse_rank"] >= 1.0 else "NEG"
        ok = "✓" if pred == r["expected_cat"] else "✗"
        if pred == r["expected_cat"]:
            correct += 1
        t = r["track"]
        track_str = f"M={t['M']:.2f} PCA={t['PCA']:.2f} dip={t['dip_violations']} scc={t['largest_scc']}"
        probs = r["diagnostic"]["problems"]
        prob_str = ", ".join(probs[:3]) if probs else "-"
        print(f"  {r['repo']:<42} {r['expected_cat']:>4} {r['qse_rank']:>7.3f} {r['agq_v3c']:>6.3f} {pred:>5} {ok:>4} {track_str:<30} {prob_str}")

    print(f"\n  Accuracy (threshold=1.0): {correct}/{len(valid)} = {correct/len(valid):.1%}")

# ── AMB repos ──
amb = [r for r in results if "error" not in r and r["expected_cat"] == "AMB"]
if amb:
    print(f"\n  Ambiguous repos:")
    for r in amb:
        probs = r["diagnostic"]["problems"]
        print(f"    {r['repo']:<42} QSE-Rank={r['qse_rank']:.3f} AGQ={r['agq_v3c']:.3f} [{', '.join(probs) or '-'}]")

# ── Save ───────────────────────────────────────────────────────────────
output = {
    "experiment": "E13_fresh_pilot_three_layer",
    "date": datetime.now(timezone.utc).isoformat(),
    "gt_benchmark_n": len(GT_BENCHMARK_C),
    "new_repos_scanned": len(NEW_REPOS),
    "framework": {
        "layer_1": "QSE-Rank = rank(C)+rank(S) vs GT benchmark",
        "layer_2": "QSE-Track = M + PCA + dip_violations + largest_scc",
        "layer_3": "QSE-Diagnostic = full component breakdown + problem flags",
    },
    "results": results,
}

out_path = Path(__file__).parent.parent / "artifacts" / "e13_fresh_pilot_results.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\nResults saved to {out_path}")
