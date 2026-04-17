#!/usr/bin/env python3
"""
E13b: QSE-Rank refinement — why S hurts, what replaces it.

Problem: On E13 new repos, S_POS (0.229) < S_NEG (0.328) — inverted.
         rank(C)+rank(S) loses signal. C alone rpb=+0.688**.

Analysis plan:
  1. Deep look at S behavior across GT, E12, E13
  2. Test many rank combinations: C alone, C+CD, C+PCA, C+M, etc.
  3. Cross-validate on all three datasets
  4. Find the most stable formula
"""

import json
import numpy as np
from scipy import stats
from pathlib import Path
from itertools import combinations

# ── Load all datasets ──────────────────────────────────────────────────
base = Path(__file__).parent.parent / "artifacts"

with open(base / "e10_gt_results.json") as f:
    gt_data = json.load(f)

with open(base / "e12_blind_pilot_results.json") as f:
    e12_data = json.load(f)

with open(base / "e13_fresh_pilot_results.json") as f:
    e13_data = json.load(f)

# Extract metrics from each dataset
def extract(results, cat_key="expected_cat", panel_key=None):
    """Extract metrics array from results. Returns list of dicts with all metrics."""
    out = []
    for r in results:
        if "error" in r:
            continue
        cat = r.get(cat_key, r.get("expected_cat", ""))
        if cat not in ("POS", "NEG"):
            continue
        label = 1 if cat == "POS" else 0
        
        # Handle different JSON structures
        C = r.get("C", r.get("diagnostic", {}).get("C", 0))
        S = r.get("S", r.get("diagnostic", {}).get("S", 0))
        M = r.get("M", r.get("diagnostic", {}).get("M", r.get("track", {}).get("M", 0)))
        A = r.get("A", r.get("diagnostic", {}).get("A", 0))
        CD = r.get("CD", r.get("diagnostic", {}).get("CD", 0))
        PCA = r.get("PCA", r.get("diagnostic", {}).get("PCA", r.get("track", {}).get("PCA", None)))
        LVR = r.get("LVR", r.get("diagnostic", {}).get("LVR", None))
        SH = r.get("SH", None)
        nodes = r.get("nodes", 0)
        
        out.append({
            "repo": r["repo"], "label": label, "cat": cat,
            "C": C, "S": S, "M": M, "A": A, "CD": CD,
            "PCA": float(PCA) if PCA is not None else None,
            "LVR": float(LVR) if LVR is not None else None,
            "SH": float(SH) if SH is not None else None,
            "nodes": nodes,
        })
    return out

# GT: panel >= 6.5 = POS, else NEG
gt_repos = []
for r in gt_data["results"]:
    label = 1 if r["panel"] >= 6.5 else 0
    gt_repos.append({
        "repo": r["repo"], "label": label, "cat": "POS" if label else "NEG",
        "C": r["C"], "S": r["S"], "M": r["M"], "A": r["A"],
        "CD": r["CD"], "PCA": r.get("PCA"), "LVR": r.get("LVR"),
        "SH": r.get("SH"), "nodes": r.get("nodes", 0),
    })

e12_repos = extract(e12_data["results"], cat_key="expected_cat")
e13_repos = extract(e13_data["results"], cat_key="expected_cat")

print("=" * 80)
print("E13b: QSE-RANK REFINEMENT")
print("=" * 80)
print(f"GT: {len(gt_repos)} repos, E12: {len(e12_repos)} repos, E13: {len(e13_repos)} repos")

# ═══════════════════════════════════════════════════════════════════════
# 1. DEEP LOOK AT S BEHAVIOR
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("1. S BEHAVIOR ACROSS DATASETS")
print("=" * 80)

for name, repos in [("GT (n=52)", gt_repos), ("E12 (n=11)", e12_repos), ("E13 (n=13)", e13_repos)]:
    pos = [r for r in repos if r["label"] == 1]
    neg = [r for r in repos if r["label"] == 0]
    
    for metric in ["C", "S", "M", "CD"]:
        pos_vals = [r[metric] for r in pos if r[metric] is not None]
        neg_vals = [r[metric] for r in neg if r[metric] is not None]
        if len(pos_vals) < 2 or len(neg_vals) < 2:
            continue
        
        all_vals = np.array(pos_vals + neg_vals)
        labels = np.array([1]*len(pos_vals) + [0]*len(neg_vals))
        rpb, p = stats.pointbiserialr(labels, all_vals)
        direction = "POS>NEG ✓" if np.mean(pos_vals) > np.mean(neg_vals) else "POS<NEG ✗"
        sig = "**" if p < 0.01 else "*" if p < 0.05 else " "
        print(f"  {name:<15} {metric}: POS={np.mean(pos_vals):.3f} NEG={np.mean(neg_vals):.3f}  "
              f"rpb={rpb:+.3f} p={p:.4f}{sig}  {direction}")
    print()

# ═══════════════════════════════════════════════════════════════════════
# 2. TEST ALL RANK COMBINATIONS
# ═══════════════════════════════════════════════════════════════════════
print("=" * 80)
print("2. RANK COMBINATION SEARCH")
print("=" * 80)

# Build GT benchmark arrays
gt_C = np.array([r["C"] for r in gt_repos])
gt_S = np.array([r["S"] for r in gt_repos])
gt_M = np.array([r["M"] for r in gt_repos])
gt_CD = np.array([r["CD"] for r in gt_repos])
gt_A = np.array([r["A"] for r in gt_repos])

# For PCA — some might be None in E13
gt_PCA = np.array([r.get("PCA") for r in gt_repos if r.get("PCA") is not None])

def percentile_rank(value, benchmark):
    """Percentile of value in benchmark [0, 1]."""
    return float(np.mean(benchmark <= value))

def eval_formula(repos, formula_fn, gt_benchmarks):
    """Evaluate a formula on a dataset. Returns rpb, p, auc."""
    valid = [(r, formula_fn(r, gt_benchmarks)) for r in repos if formula_fn(r, gt_benchmarks) is not None]
    if len(valid) < 5:
        return None, None, None
    
    labels = np.array([r["label"] for r, _ in valid])
    scores = np.array([s for _, s in valid])
    
    if np.std(labels) == 0 or np.std(scores) == 0:
        return None, None, None
    
    rpb, p = stats.pointbiserialr(labels, scores)
    
    pos_scores = scores[labels == 1]
    neg_scores = scores[labels == 0]
    if len(pos_scores) > 0 and len(neg_scores) > 0:
        auc = sum(1.0 if pv > nv else 0.5 if pv == nv else 0.0
                  for pv in pos_scores for nv in neg_scores) / (len(pos_scores) * len(neg_scores))
    else:
        auc = None
    
    return rpb, p, auc

# Define candidate formulas
gt_bench = {"C": gt_C, "S": gt_S, "M": gt_M, "CD": gt_CD, "A": gt_A}

formulas = {}

# Single metrics (raw)
formulas["C_raw"] = lambda r, b: r["C"]
formulas["S_raw"] = lambda r, b: r["S"]
formulas["M_raw"] = lambda r, b: r["M"]
formulas["CD_raw"] = lambda r, b: r["CD"]

# Single ranks
formulas["rank(C)"] = lambda r, b: percentile_rank(r["C"], b["C"])
formulas["rank(S)"] = lambda r, b: percentile_rank(r["S"], b["S"])
formulas["rank(M)"] = lambda r, b: percentile_rank(r["M"], b["M"])
formulas["rank(CD)"] = lambda r, b: percentile_rank(r["CD"], b["CD"])

# Two-metric rank sums
formulas["rank(C)+rank(S)"] = lambda r, b: percentile_rank(r["C"], b["C"]) + percentile_rank(r["S"], b["S"])
formulas["rank(C)+rank(M)"] = lambda r, b: percentile_rank(r["C"], b["C"]) + percentile_rank(r["M"], b["M"])
formulas["rank(C)+rank(CD)"] = lambda r, b: percentile_rank(r["C"], b["C"]) + percentile_rank(r["CD"], b["CD"])
formulas["rank(C)+rank(A)"] = lambda r, b: percentile_rank(r["C"], b["C"]) + percentile_rank(r["A"], b["A"])

# Three-metric rank sums
formulas["rank(C)+rank(S)+rank(M)"] = lambda r, b: (percentile_rank(r["C"], b["C"]) + 
    percentile_rank(r["S"], b["S"]) + percentile_rank(r["M"], b["M"]))
formulas["rank(C)+rank(S)+rank(CD)"] = lambda r, b: (percentile_rank(r["C"], b["C"]) + 
    percentile_rank(r["S"], b["S"]) + percentile_rank(r["CD"], b["CD"]))
formulas["rank(C)+rank(M)+rank(CD)"] = lambda r, b: (percentile_rank(r["C"], b["C"]) + 
    percentile_rank(r["M"], b["M"]) + percentile_rank(r["CD"], b["CD"]))

# Weighted variants
formulas["2*rank(C)+rank(S)"] = lambda r, b: 2*percentile_rank(r["C"], b["C"]) + percentile_rank(r["S"], b["S"])
formulas["rank(C)+0.5*rank(S)"] = lambda r, b: percentile_rank(r["C"], b["C"]) + 0.5*percentile_rank(r["S"], b["S"])
formulas["2*rank(C)+rank(M)"] = lambda r, b: 2*percentile_rank(r["C"], b["C"]) + percentile_rank(r["M"], b["M"])

# AGQ-style
formulas["AGQ_equal"] = lambda r, b: (r["M"] + r["A"] + r["S"] + r["C"]) / 4
formulas["AGQ_v3c_approx"] = lambda r, b: 0.2*r["M"] + 0.2*r["A"] + 0.2*r["S"] + 0.2*r["C"] + 0.2*r["CD"]

# PCA-based (might be None)
def rank_c_pca(r, b):
    pca = r.get("PCA")
    if pca is None:
        return None
    return percentile_rank(r["C"], b["C"]) + pca  # PCA already [0,1]

formulas["rank(C)+PCA"] = rank_c_pca

# C with Track penalty
def c_with_track_penalty(r, b):
    pca = r.get("PCA")
    if pca is None:
        return None
    c_pct = percentile_rank(r["C"], b["C"])
    # Penalty for bad Track metrics
    track_health = min(1.0, pca * (1.0 if r["M"] >= 0.5 else 0.7))
    return c_pct * (0.5 + 0.5 * track_health)

formulas["rank(C)*track_health"] = c_with_track_penalty


# Evaluate all formulas on all datasets
print(f"\n  {'Formula':<30} {'GT rpb':>8} {'GT p':>8} {'GT AUC':>8} | {'E12 rpb':>8} {'E12 p':>8} | {'E13 rpb':>8} {'E13 p':>8} | {'Avg rpb':>8}")
print("  " + "-" * 120)

results_table = []
for name, fn in formulas.items():
    gt_rpb, gt_p, gt_auc = eval_formula(gt_repos, fn, gt_bench)
    e12_rpb, e12_p, _ = eval_formula(e12_repos, fn, gt_bench)
    e13_rpb, e13_p, _ = eval_formula(e13_repos, fn, gt_bench)
    
    # Average rpb across datasets where available
    rpbs = [x for x in [gt_rpb, e12_rpb, e13_rpb] if x is not None]
    avg_rpb = np.mean(rpbs) if rpbs else None
    
    def fmt(v, p=None):
        if v is None:
            return "   ---  "
        sig = "**" if p and p < 0.01 else "* " if p and p < 0.05 else "  "
        return f"{v:>+.3f}{sig}"
    
    gt_str = fmt(gt_rpb, gt_p)
    gt_p_str = f"{gt_p:.4f}" if gt_p is not None else "  ---  "
    gt_auc_str = f"{gt_auc:.3f}" if gt_auc is not None else " ---  "
    e12_str = fmt(e12_rpb, e12_p)
    e12_p_str = f"{e12_p:.4f}" if e12_p is not None else "  ---  "
    e13_str = fmt(e13_rpb, e13_p)
    e13_p_str = f"{e13_p:.4f}" if e13_p is not None else "  ---  "
    avg_str = f"{avg_rpb:>+.3f}" if avg_rpb is not None else "  ---  "
    
    print(f"  {name:<30} {gt_str} {gt_p_str} {gt_auc_str} | {e12_str} {e12_p_str} | {e13_str} {e13_p_str} | {avg_str}")
    
    results_table.append({
        "formula": name,
        "gt_rpb": round(gt_rpb, 4) if gt_rpb is not None else None,
        "gt_p": round(gt_p, 4) if gt_p is not None else None,
        "gt_auc": round(gt_auc, 3) if gt_auc is not None else None,
        "e12_rpb": round(e12_rpb, 4) if e12_rpb is not None else None,
        "e13_rpb": round(e13_rpb, 4) if e13_rpb is not None else None,
        "avg_rpb": round(avg_rpb, 4) if avg_rpb is not None else None,
    })

# ═══════════════════════════════════════════════════════════════════════
# 3. STABILITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("3. STABILITY — SIGN CONSISTENCY")
print("=" * 80)
print("\n  Formula that has POSITIVE rpb on ALL datasets = stable.\n")

stable = []
for name, fn in formulas.items():
    gt_rpb, gt_p, _ = eval_formula(gt_repos, fn, gt_bench)
    e12_rpb, e12_p, _ = eval_formula(e12_repos, fn, gt_bench)
    e13_rpb, e13_p, _ = eval_formula(e13_repos, fn, gt_bench)
    
    rpbs = [x for x in [gt_rpb, e12_rpb, e13_rpb] if x is not None]
    if len(rpbs) >= 2 and all(r > 0 for r in rpbs):
        avg = np.mean(rpbs)
        stable.append((name, avg, gt_rpb or 0, e12_rpb or 0, e13_rpb or 0))

stable.sort(key=lambda x: -x[1])
print(f"  {'Formula':<30} {'Avg rpb':>8} {'GT':>8} {'E12':>8} {'E13':>8}")
print("  " + "-" * 60)
for name, avg, gt_r, e12_r, e13_r in stable:
    print(f"  {name:<30} {avg:>+8.3f} {gt_r:>+8.3f} {e12_r:>+8.3f} {e13_r:>+8.3f}")

# ═══════════════════════════════════════════════════════════════════════
# 4. COMBINED DATASET (GT + E12 + E13)
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("4. COMBINED DATASET (GT + E12 + E13)")
print("=" * 80)

# Merge — but E12 repos might overlap with GT? Check.
gt_repo_set = {r["repo"] for r in gt_repos}
e12_unique = [r for r in e12_repos if r["repo"] not in gt_repo_set]
e13_unique = [r for r in e13_repos if r["repo"] not in gt_repo_set]
combined = gt_repos + e12_unique + e13_unique
print(f"\n  Combined: {len(combined)} repos (GT={len(gt_repos)} + E12={len(e12_unique)} + E13={len(e13_unique)})")

print(f"\n  {'Formula':<30} {'rpb':>8} {'p':>10} {'AUC':>8}")
print("  " + "-" * 60)

for name, fn in formulas.items():
    rpb, p, auc = eval_formula(combined, fn, gt_bench)
    if rpb is None:
        continue
    sig = "**" if p < 0.01 else "*" if p < 0.05 else " "
    print(f"  {name:<30} {rpb:>+8.3f} {p:>10.4f}{sig} {auc:>8.3f}")

# ═══════════════════════════════════════════════════════════════════════
# 5. RECOMMENDATION
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 80)
print("5. RECOMMENDATION")
print("=" * 80)

# Find best stable formula
if stable:
    best = stable[0]
    print(f"\n  Best stable formula: {best[0]}")
    print(f"    Average rpb: {best[1]:+.3f}")
    print(f"    GT:  {best[2]:+.3f}")
    print(f"    E12: {best[3]:+.3f}")
    print(f"    E13: {best[4]:+.3f}")

# Save
output = {
    "experiment": "E13b_rank_refinement",
    "formula_comparison": results_table,
    "stable_formulas": [{"formula": s[0], "avg_rpb": s[1], "gt": s[2], "e12": s[3], "e13": s[4]} for s in stable],
    "recommendation": stable[0][0] if stable else "C_raw",
}

out_path = base / "e13b_rank_refinement.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\n  Saved to {out_path}")
