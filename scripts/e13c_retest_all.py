#!/usr/bin/env python3
"""
E13c: Re-test ALL pilot repos with new three-layer QSE framework.

Rescans E12 (14 repos) and E13 (14 repos) from scratch using:
  - java_scanner (direct API, not CLI)
  - New formula: 2*rank(C)+rank(S) [0, 3]
  - Full three-layer output: QSE-Rank, QSE-Track, QSE-Diagnostic

Also recalculates GT (n=52) with new formula for comparison.
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
    compute_agq,
    compute_structural_health,
    compute_qse_rank,
    compute_qse_track,
    compute_qse_diagnostic,
    GT_BENCHMARK_C,
    GT_BENCHMARK_S,
)

# ── All repos to (re)scan ─────────────────────────────────────────────
# E12 repos
E12_REPOS = [
    ("eventuate-tram/eventuate-tram-core", "POS", "Event-driven microservices, clean DDD"),
    ("jmolecules/jmolecules", "POS", "DDD building blocks for Java"),
    ("Netflix/zuul", "POS", "Netflix API gateway"),
    ("eclipse-vertx/vert.x", "POS", "Reactive toolkit, modular architecture"),
    ("apache/kafka", "POS", "Distributed streaming platform"),
    ("projectlombok/lombok", "POS", "Annotation processor, focused library"),
    ("apache/maven", "POS", "Build tool, mature project"),
    ("AntennaPod/AntennaPod", "NEG", "Android podcast app, spaghetti"),
    ("signalapp/Signal-Android", "NEG", "Messaging app, complex Android monolith"),
    ("TeamNewPipe/NewPipe", "NEG", "YouTube client, Android legacy"),
    ("iluwatar/java-design-patterns", "NEG", "Design pattern collection, not architecture"),
    ("alibaba/nacos", "NEG", "Config/discovery, complex coupling"),
    ("alibaba/Sentinel", "NEG", "Flow control, tight coupling"),
    ("eclipse/jetty.project", "AMB", "Servlet container, mature but monolithic"),
    ("hibernate/hibernate-orm", "AMB", "ORM, complex but well-structured"),
]

# E13 repos
E13_REPOS = [
    ("AxonFramework/AxonFramework", "POS", "CQRS/ES framework, bounded contexts"),
    ("camunda/camunda-bpm-platform", "POS", "Process engine, modular"),
    ("apache/flink", "POS", "Stream processing, layered"),
    ("dropwizard/dropwizard", "POS", "REST framework, focused modules"),
    ("micronaut-projects/micronaut-core", "POS", "Modern DI framework"),
    ("quarkusio/quarkus", "POS", "Cloud-native Java framework"),
    ("eclipse-store/store", "POS", "Object graph persistence"),
    ("elastic/elasticsearch", "NEG", "Massive monolith, god classes"),
    ("TheAlgorithms/Java", "NEG", "Algorithm collection, no architecture"),
    ("Anuken/Mindustry", "NEG", "Game monolith, global state"),
    ("dbeaver/dbeaver", "NEG", "Eclipse-based, plugin spaghetti"),
    ("NationalSecurityAgency/ghidra", "NEG", "Massive legacy codebase"),
    ("termux/termux-app", "NEG", "Android terminal, messy"),
    ("ReactiveX/RxJava", "AMB", "Reactive library, complex internals"),
]


def scan_one(repo_slug: str) -> dict:
    """Clone, scan, return three-layer results."""
    safe = repo_slug.replace("/", "_")
    dest = f"/tmp/e13c_{safe}"
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

        # Layer 1: QSE-Rank (new formula: 2*rank(C)+rank(S))
        qse_rank_score = compute_qse_rank(agq, GT_BENCHMARK_C, GT_BENCHMARK_S)
        c_pct = float(np.mean(np.array(GT_BENCHMARK_C) <= agq.cohesion))
        s_pct = float(np.mean(np.array(GT_BENCHMARK_S) <= agq.stability))

        # Old formula for comparison
        old_rank = c_pct + s_pct

        # Layer 2: QSE-Track
        track = compute_qse_track(graph, scan.internal_nodes, scan.packages)

        # Layer 3: QSE-Diagnostic
        diagnostic = compute_qse_diagnostic(
            graph, agq, GT_BENCHMARK_C, GT_BENCHMARK_S,
            scan.internal_nodes, scan.packages
        )

        return {
            "qse_rank": round(qse_rank_score, 4),
            "qse_rank_old": round(old_rank, 4),
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


def run_batch(name, repos):
    """Scan a batch of repos, return results list."""
    print(f"\n{'=' * 80}")
    print(f"SCANNING: {name} ({len(repos)} repos)")
    print(f"{'=' * 80}\n")

    results = []
    for repo_slug, expected_cat, desc in repos:
        print(f"  [{expected_cat}] {repo_slug}...", end=" ", flush=True)
        metrics = scan_one(repo_slug)

        result = {"repo": repo_slug, "expected_cat": expected_cat, "desc": desc}

        if "error" in metrics:
            result["error"] = metrics["error"]
            print(f"ERROR: {metrics['error'][:60]}")
        else:
            result.update(metrics)
            t = metrics["track"]
            print(f"Rank={metrics['qse_rank']:.2f} (old={metrics['qse_rank_old']:.2f})  "
                  f"M={t['M']:.2f} PCA={t['PCA']:.2f} dip={t['dip_violations']} scc={t['largest_scc']}  "
                  f"nodes={metrics['nodes']}")

        results.append(result)
    return results


# ── Also recalculate GT with new formula ───────────────────────────────
def recalc_gt():
    """Recalculate GT dataset with new 2*rank(C)+rank(S)."""
    gt_path = Path(__file__).parent.parent / "artifacts" / "e10_gt_results.json"
    with open(gt_path) as f:
        gt_data = json.load(f)

    gt_C = np.array(GT_BENCHMARK_C)
    gt_S = np.array(GT_BENCHMARK_S)

    results = []
    for r in gt_data["results"]:
        c_pct = float(np.mean(gt_C <= r["C"]))
        s_pct = float(np.mean(gt_S <= r["S"]))
        new_rank = 2.0 * c_pct + s_pct
        old_rank = c_pct + s_pct
        results.append({
            "repo": r["repo"],
            "panel": r["panel"],
            "label": 1 if r["panel"] >= 6.5 else 0,
            "qse_rank_new": round(new_rank, 4),
            "qse_rank_old": round(old_rank, 4),
            "C": r["C"], "S": r["S"], "M": r["M"],
        })
    return results


# ── Main ───────────────────────────────────────────────────────────────
print("=" * 80)
print("E13c: RE-TEST ALL PILOT REPOS WITH THREE-LAYER QSE")
print(f"Date: {datetime.now(timezone.utc).isoformat()}")
print(f"Formula: 2*rank(C)+rank(S) [0, 3]")
print("=" * 80)

e12_results = run_batch("E12 repos", E12_REPOS)
e13_results = run_batch("E13 repos", E13_REPOS)
gt_recalc = recalc_gt()

# ═══════════════════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def analyze(name, results, threshold=1.5):
    """Analyze one batch."""
    valid = [r for r in results if "error" not in r and r["expected_cat"] in ("POS", "NEG")]
    pos = [r for r in valid if r["expected_cat"] == "POS"]
    neg = [r for r in valid if r["expected_cat"] == "NEG"]

    print(f"\n{'=' * 80}")
    print(f"RESULTS: {name} (POS={len(pos)}, NEG={len(neg)})")
    print(f"{'=' * 80}")

    if len(pos) < 2 or len(neg) < 2:
        print("  Too few repos for statistics")
        return

    # Stats for each metric
    for metric_name, key in [("QSE-Rank new", "qse_rank"), ("QSE-Rank old", "qse_rank_old"),
                               ("AGQ_v3c", "agq_v3c"), ("C alone", "C")]:
        pos_vals = [r[key] for r in pos if key in r]
        neg_vals = [r[key] for r in neg if key in r]
        if len(pos_vals) < 2 or len(neg_vals) < 2:
            continue

        all_v = np.array(pos_vals + neg_vals)
        labels = np.array([1]*len(pos_vals) + [0]*len(neg_vals))
        mw = stats.mannwhitneyu(pos_vals, neg_vals, alternative="greater")
        rpb, p = stats.pointbiserialr(labels, all_v)
        auc = sum(1.0 if p > n else 0.5 if p == n else 0.0
                  for p in pos_vals for n in neg_vals) / (len(pos_vals) * len(neg_vals))
        sig = "**" if mw.pvalue < 0.01 else "* " if mw.pvalue < 0.05 else "  "
        print(f"  {metric_name:<20} POS={np.mean(pos_vals):.3f} NEG={np.mean(neg_vals):.3f}  "
              f"MW p={mw.pvalue:.4f}{sig} rpb={rpb:+.3f} AUC={auc:.3f}")

    # Classification table
    print(f"\n  {'Repo':<40} {'Cat':>4} {'Rank':>6} {'Old':>6} {'AGQ':>6} {'Pred':>5} {'OK':>3} "
          f"{'M':>5} {'PCA':>5} {'dip':>4} {'scc':>5} {'Problems'}")
    print("  " + "-" * 130)

    correct_new = 0
    correct_old = 0
    for r in sorted(valid, key=lambda x: x["qse_rank"], reverse=True):
        pred_new = "POS" if r["qse_rank"] >= threshold else "NEG"
        pred_old = "POS" if r["qse_rank_old"] >= 1.0 else "NEG"
        ok_new = "✓" if pred_new == r["expected_cat"] else "✗"
        if pred_new == r["expected_cat"]:
            correct_new += 1
        if pred_old == r["expected_cat"]:
            correct_old += 1

        t = r["track"]
        probs = r["diagnostic"]["problems"]
        prob_str = ", ".join(probs[:3]) if probs else "-"
        print(f"  {r['repo']:<40} {r['expected_cat']:>4} {r['qse_rank']:>6.2f} {r['qse_rank_old']:>6.2f} "
              f"{r['agq_v3c']:>6.3f} {pred_new:>5} {ok_new:>3} "
              f"{t['M']:>5.2f} {t['PCA']:>5.2f} {t['dip_violations']:>4} {t['largest_scc']:>5} {prob_str}")

    print(f"\n  Accuracy (new, thr={threshold}): {correct_new}/{len(valid)} = {correct_new/len(valid):.1%}")
    print(f"  Accuracy (old, thr=1.0):  {correct_old}/{len(valid)} = {correct_old/len(valid):.1%}")

    # AMB repos
    amb = [r for r in results if "error" not in r and r["expected_cat"] == "AMB"]
    if amb:
        print(f"\n  Ambiguous repos:")
        for r in amb:
            t = r["track"]
            probs = r["diagnostic"]["problems"]
            print(f"    {r['repo']:<40} Rank={r['qse_rank']:.2f} M={t['M']:.2f} PCA={t['PCA']:.2f} [{', '.join(probs) or '-'}]")

    return {
        "correct_new": correct_new, "correct_old": correct_old, "total": len(valid),
    }


# GT with new formula
print(f"\n{'=' * 80}")
print("GT RECALCULATION (n=52)")
print(f"{'=' * 80}")

gt_labels = np.array([r["label"] for r in gt_recalc])
gt_new = np.array([r["qse_rank_new"] for r in gt_recalc])
gt_old = np.array([r["qse_rank_old"] for r in gt_recalc])
gt_panel = np.array([r["panel"] for r in gt_recalc])

rho_new, p_new = stats.spearmanr(gt_new, gt_panel)
rho_old, p_old = stats.spearmanr(gt_old, gt_panel)
rpb_new, rpb_p_new = stats.pointbiserialr(gt_labels, gt_new)
rpb_old, rpb_p_old = stats.pointbiserialr(gt_labels, gt_old)

print(f"  2*rank(C)+rank(S): Spearman ρ={rho_new:+.3f} (p={p_new:.4f}), rpb={rpb_new:+.3f}")
print(f"    rank(C)+rank(S): Spearman ρ={rho_old:+.3f} (p={p_old:.4f}), rpb={rpb_old:+.3f}")

# E12 and E13
stats_e12 = analyze("E12 repos (re-scanned)", e12_results, threshold=1.5)
stats_e13 = analyze("E13 repos (re-scanned)", e13_results, threshold=1.5)

# ── Combined ───────────────────────────────────────────────────────────
all_pilot = [r for r in e12_results + e13_results if "error" not in r and r["expected_cat"] in ("POS", "NEG")]
if len(all_pilot) >= 10:
    print(f"\n{'=' * 80}")
    print(f"COMBINED E12+E13 (n={len(all_pilot)})")
    print(f"{'=' * 80}")
    
    for key, label in [("qse_rank", "QSE-Rank new"), ("qse_rank_old", "QSE-Rank old"),
                        ("agq_v3c", "AGQ_v3c"), ("C", "C alone")]:
        vals = np.array([r[key] for r in all_pilot])
        labs = np.array([1 if r["expected_cat"] == "POS" else 0 for r in all_pilot])
        rpb, p = stats.pointbiserialr(labs, vals)
        sig = "**" if p < 0.01 else "* " if p < 0.05 else "  "
        print(f"  {label:<20} rpb={rpb:+.3f} p={p:.4f}{sig}")

# ── Save ───────────────────────────────────────────────────────────────
output = {
    "experiment": "E13c_retest_three_layer",
    "date": datetime.now(timezone.utc).isoformat(),
    "formula": "2*rank(C)+rank(S)",
    "gt_recalc": {
        "spearman_new": round(rho_new, 4),
        "spearman_old": round(rho_old, 4),
    },
    "e12_results": e12_results,
    "e13_results": e13_results,
}

out_path = Path(__file__).parent.parent / "artifacts" / "e13c_retest_results.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\nResults saved to {out_path}")
