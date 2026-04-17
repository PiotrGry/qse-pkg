#!/usr/bin/env python3
"""
E12b: Leave-One-Out Cross-Validation of rank(C)+rank(S) on GT (n=52).

For each repo i:
  1. Remove repo i from the dataset
  2. Compute ranks of C and S on remaining n-1 repos
  3. Insert repo i: find its rank position in the n-1 distribution
  4. QSE-Rank_i = rank_position(C_i) + rank_position(S_i)
  5. Compare QSE-Rank predictions with panel scores

This eliminates circularity: each repo is scored against a benchmark
that doesn't include itself.

Also: k-fold (5-fold, 10-fold) and random 50/50 split validation.
"""

import json
import numpy as np
from scipy import stats
from pathlib import Path

# ── Load GT data ──────────────────────────────────────────────
gt_path = Path(__file__).parent.parent / "artifacts" / "e10_gt_results.json"
with open(gt_path) as f:
    gt_data = json.load(f)

results = gt_data["results"]
n = len(results)
panel = np.array([r["panel"] for r in results])
C = np.array([r["C"] for r in results])
S = np.array([r["S"] for r in results])
M = np.array([r["M"] for r in results])
A = np.array([r["A"] for r in results])
CD = np.array([r["CD"] for r in results])
PCA = np.array([r["PCA"] for r in results])
LVR = np.array([r["LVR"] for r in results])

def corr_auc(arr, panel):
    rho, p = stats.spearmanr(arr, panel)
    pos = arr[panel >= 6.5]
    neg = arr[panel < 6.5]
    if len(pos) > 0 and len(neg) > 0:
        auc = sum(1.0 if pv > nv else 0.5 if pv == nv else 0.0 
                  for pv in pos for nv in neg) / (len(pos) * len(neg))
    else:
        auc = float('nan')
    return rho, p, auc

# ═══════════════════════════════════════════════════════════════
# 1. LEAVE-ONE-OUT CROSS-VALIDATION
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("E12b: LEAVE-ONE-OUT CROSS-VALIDATION (LOOCV)")
print("=" * 70)

def percentile_in_others(value, others):
    """Percentile rank of value in the 'others' array (0-1)."""
    return float(np.mean(others <= value))

# For each scoring method, compute LOO predictions
methods = {}

# Method 1: rank(C)+rank(S) — LOO version
loo_qse_rank = np.zeros(n)
for i in range(n):
    others_C = np.delete(C, i)
    others_S = np.delete(S, i)
    c_pct = percentile_in_others(C[i], others_C)
    s_pct = percentile_in_others(S[i], others_S)
    loo_qse_rank[i] = c_pct + s_pct
methods["QSE-Rank LOO"] = loo_qse_rank

# Method 2: 0.5*C + 0.5*S raw — no LOO needed (raw values, no ranking)
methods["0.5*C+0.5*S (raw)"] = 0.5 * C + 0.5 * S

# Method 3: AGQ (M+A+S+C)/4 — no LOO needed
methods["AGQ(M,A,S,C)"] = (M + A + S + C) / 4.0

# Method 4: C alone
methods["C alone"] = C

# Method 5: S alone
methods["S alone"] = S

# Method 6: rank(C)+rank(S) — in-sample (for comparison)
methods["rank(C)+rank(S) in-sample"] = stats.rankdata(C) + stats.rankdata(S)

# Method 7: AGQ v3c
methods["AGQ_v3c"] = np.array([r["agq_v3c"] for r in results])

# Method 8: LOO version of AGQ rank-based
loo_agq_rank = np.zeros(n)
for i in range(n):
    others_M = np.delete(M, i)
    others_A = np.delete(A, i)
    others_S = np.delete(S, i)
    others_C = np.delete(C, i)
    m_pct = percentile_in_others(M[i], others_M)
    a_pct = percentile_in_others(A[i], others_A)
    s_pct = percentile_in_others(S[i], others_S)
    c_pct = percentile_in_others(C[i], others_C)
    loo_agq_rank[i] = m_pct + a_pct + s_pct + c_pct
methods["rank(M+A+S+C) LOO"] = loo_agq_rank

# Method 9: LOO rank(C)+rank(S)+0.25*rank(CD)
loo_cscd = np.zeros(n)
for i in range(n):
    others_C = np.delete(C, i)
    others_S = np.delete(S, i)
    others_CD = np.delete(CD, i)
    c_pct = percentile_in_others(C[i], others_C)
    s_pct = percentile_in_others(S[i], others_S)
    cd_pct = percentile_in_others(CD[i], others_CD)
    loo_cscd[i] = c_pct + s_pct + 0.25 * cd_pct
methods["rank(C+S+0.25CD) LOO"] = loo_cscd

print(f"\nn={n} repos, LOO cross-validation\n")
print(f"  {'Method':<30} {'ρ':>8} {'p':>10} {'AUC':>8} {'note':>10}")
print("  " + "-" * 70)

for name, arr in methods.items():
    rho, p, auc = corr_auc(arr, panel)
    sig = "**" if p < 0.01 else "*" if p < 0.05 else " "
    loo = "LOO" if "LOO" in name else "in-sample"
    print(f"  {name:<30} {rho:>+8.3f} {p:>10.4f}{sig} {auc:>8.3f} {loo:>10}")

# ═══════════════════════════════════════════════════════════════
# 2. K-FOLD CROSS-VALIDATION
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("K-FOLD CROSS-VALIDATION")
print("=" * 70)

np.random.seed(42)

def kfold_rank_cs(C, S, panel, k=5, n_repeats=100):
    """Repeated k-fold CV: rank(C)+rank(S) scored against out-of-fold benchmark."""
    n = len(C)
    all_rhos = []
    
    for rep in range(n_repeats):
        indices = np.random.permutation(n)
        fold_size = n // k
        predictions = np.zeros(n)
        
        for fold in range(k):
            start = fold * fold_size
            end = start + fold_size if fold < k - 1 else n
            test_idx = indices[start:end]
            train_idx = np.setdiff1d(indices, test_idx)
            
            train_C = C[train_idx]
            train_S = S[train_idx]
            
            for i in test_idx:
                c_pct = float(np.mean(train_C <= C[i]))
                s_pct = float(np.mean(train_S <= S[i]))
                predictions[i] = c_pct + s_pct
        
        rho, _ = stats.spearmanr(predictions, panel)
        all_rhos.append(rho)
    
    return all_rhos

for k in [5, 10, 26]:  # 26-fold ≈ LOO for n=52
    rhos = kfold_rank_cs(C, S, panel, k=k, n_repeats=500)
    mean_rho = np.mean(rhos)
    ci = np.percentile(rhos, [2.5, 97.5])
    print(f"  {k}-fold CV (500 repeats): mean ρ = {mean_rho:+.3f}  95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}]")

# Same for AGQ
def kfold_agq(M, A, S, C, panel, k=5, n_repeats=100):
    n = len(C)
    all_rhos = []
    for rep in range(n_repeats):
        indices = np.random.permutation(n)
        fold_size = n // k
        predictions = np.zeros(n)
        for fold in range(k):
            start = fold * fold_size
            end = start + fold_size if fold < k - 1 else n
            test_idx = indices[start:end]
            for i in test_idx:
                predictions[i] = (M[i] + A[i] + S[i] + C[i]) / 4.0
        rho, _ = stats.spearmanr(predictions, panel)
        all_rhos.append(rho)
    return all_rhos

print()
print("  Comparison — AGQ(M,A,S,C) k-fold:")
for k in [5, 10, 26]:
    rhos = kfold_agq(M, A, S, C, panel, k=k, n_repeats=500)
    mean_rho = np.mean(rhos)
    ci = np.percentile(rhos, [2.5, 97.5])
    print(f"  {k}-fold CV (500 repeats): mean ρ = {mean_rho:+.3f}  95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}]")

# ═══════════════════════════════════════════════════════════════
# 3. RANDOM SPLIT VALIDATION (50/50)
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("RANDOM 50/50 SPLIT VALIDATION (1000 repeats)")
print("=" * 70)

def split_validate(C, S, M, A, panel, n_splits=1000):
    n = len(C)
    half = n // 2
    
    qse_rhos = []
    agq_rhos = []
    c_rhos = []
    s_rhos = []
    
    for _ in range(n_splits):
        idx = np.random.permutation(n)
        train, test = idx[:half], idx[half:]
        
        train_C, test_C = C[train], C[test]
        train_S, test_S = S[train], S[test]
        test_panel = panel[test]
        
        # QSE-Rank on test set using train as benchmark
        qse_pred = np.array([
            float(np.mean(train_C <= test_C[i])) + float(np.mean(train_S <= test_S[i]))
            for i in range(len(test))
        ])
        
        # AGQ on test set (no training needed)
        agq_pred = np.array([
            (M[test[i]] + A[test[i]] + S[test[i]] + C[test[i]]) / 4.0
            for i in range(len(test))
        ])
        
        if len(test_panel) >= 5:
            r1, _ = stats.spearmanr(qse_pred, test_panel)
            r2, _ = stats.spearmanr(agq_pred, test_panel)
            r3, _ = stats.spearmanr(test_C, test_panel)
            r4, _ = stats.spearmanr(test_S, test_panel)
            qse_rhos.append(r1)
            agq_rhos.append(r2)
            c_rhos.append(r3)
            s_rhos.append(r4)
    
    return qse_rhos, agq_rhos, c_rhos, s_rhos

qse_r, agq_r, c_r, s_r = split_validate(C, S, M, A, panel, n_splits=1000)

print(f"\n  {'Method':<30} {'mean ρ':>8} {'median ρ':>10} {'95% CI':>25} {'% sig':>8}")
print("  " + "-" * 85)

for name, rhos in [("QSE-Rank rank(C)+rank(S)", qse_r),
                    ("AGQ(M,A,S,C)", agq_r),
                    ("C alone", c_r),
                    ("S alone", s_r)]:
    rhos_arr = np.array(rhos)
    mean_r = np.mean(rhos_arr)
    median_r = np.median(rhos_arr)
    ci = np.percentile(rhos_arr, [2.5, 97.5])
    # Approximate: what fraction of splits have ρ > 0.27 (threshold from n=26, p≈0.05)
    pct_sig = 100 * np.mean(rhos_arr > 0.27)
    print(f"  {name:<30} {mean_r:>+8.3f} {median_r:>+10.3f} [{ci[0]:>+.3f}, {ci[1]:>+.3f}]   {pct_sig:>6.1f}%")

# ═══════════════════════════════════════════════════════════════
# 4. PERMUTATION TEST (is the observed ρ better than chance?)
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("PERMUTATION TEST (10000 permutations)")
print("=" * 70)

n_perm = 10000
observed_rho, _ = stats.spearmanr(stats.rankdata(C) + stats.rankdata(S), panel)

perm_rhos = []
for _ in range(n_perm):
    shuffled_panel = np.random.permutation(panel)
    r, _ = stats.spearmanr(stats.rankdata(C) + stats.rankdata(S), shuffled_panel)
    perm_rhos.append(r)

perm_p = np.mean(np.array(perm_rhos) >= observed_rho)
print(f"\n  Observed ρ = {observed_rho:+.3f}")
print(f"  Permutation p-value = {perm_p:.4f} (fraction of {n_perm} permutations with ρ ≥ observed)")
print(f"  95th percentile of null: {np.percentile(perm_rhos, 95):+.3f}")
print(f"  99th percentile of null: {np.percentile(perm_rhos, 99):+.3f}")

# Also for AGQ
observed_agq, _ = stats.spearmanr((M+A+S+C)/4, panel)
perm_agq = []
for _ in range(n_perm):
    shuffled = np.random.permutation(panel)
    r, _ = stats.spearmanr((M+A+S+C)/4, shuffled)
    perm_agq.append(r)
perm_p_agq = np.mean(np.array(perm_agq) >= observed_agq)
print(f"\n  AGQ observed ρ = {observed_agq:+.3f}")
print(f"  AGQ permutation p = {perm_p_agq:.4f}")

# ═══════════════════════════════════════════════════════════════
# 5. SUMMARY
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUMMARY: IS rank(C)+rank(S) GENUINELY BETTER THAN AGQ?")
print("=" * 70)

print(f"""
  Metric                         In-sample ρ   LOO ρ    50/50 mean ρ   Perm. p
  ──────────────────────────────────────────────────────────────────────────────
  rank(C)+rank(S)                {observed_rho:>+.3f}       {corr_auc(loo_qse_rank, panel)[0]:>+.3f}     {np.mean(qse_r):>+.3f}          {perm_p:.4f}
  AGQ(M,A,S,C)                  {observed_agq:>+.3f}       {observed_agq:>+.3f}     {np.mean(agq_r):>+.3f}          {perm_p_agq:.4f}
  C alone                       {corr_auc(C, panel)[0]:>+.3f}       {corr_auc(C, panel)[0]:>+.3f}     {np.mean(c_r):>+.3f}          ---
  S alone                       {corr_auc(S, panel)[0]:>+.3f}       {corr_auc(S, panel)[0]:>+.3f}     {np.mean(s_r):>+.3f}          ---
""")

# Save results
output = {
    "experiment": "E12b_LOOCV",
    "n": n,
    "loocv": {
        "QSE_Rank_LOO": {"rho": round(float(corr_auc(loo_qse_rank, panel)[0]), 4),
                         "p": round(float(corr_auc(loo_qse_rank, panel)[1]), 4),
                         "auc": round(float(corr_auc(loo_qse_rank, panel)[2]), 3)},
        "AGQ": {"rho": round(float(corr_auc((M+A+S+C)/4, panel)[0]), 4),
                "p": round(float(corr_auc((M+A+S+C)/4, panel)[1]), 4),
                "auc": round(float(corr_auc((M+A+S+C)/4, panel)[2]), 3)},
    },
    "kfold": {
        "QSE_Rank_5fold_mean_rho": round(float(np.mean(kfold_rank_cs(C, S, panel, k=5, n_repeats=500))), 4),
        "AGQ_5fold_mean_rho": round(float(np.mean(kfold_agq(M, A, S, C, panel, k=5, n_repeats=500))), 4),
    },
    "split_50_50": {
        "QSE_Rank_mean_rho": round(float(np.mean(qse_r)), 4),
        "AGQ_mean_rho": round(float(np.mean(agq_r)), 4),
    },
    "permutation": {
        "QSE_Rank_perm_p": round(float(perm_p), 4),
        "AGQ_perm_p": round(float(perm_p_agq), 4),
    }
}

out_path = Path(__file__).parent.parent / "artifacts" / "e12b_loocv_results.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"Results saved to {out_path}")
