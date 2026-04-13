#!/usr/bin/env python3
"""
E11: Test all 4 literature approaches (A, B, C, D)
Phase 1: Cross-repo analysis on GT (n=52)
  A1-A3: Percentile normalization
  B1-B2: Dual-mode AGQ definition + benchmark validation
  C1-C2: Count-based metrics + correlation
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
print(f"Loaded GT data: n={n} repos\n")

# Extract arrays
repos   = [r["repo"] for r in results]
panel   = np.array([r["panel"] for r in results])
M_arr   = np.array([r["M"] for r in results])
A_arr   = np.array([r["A"] for r in results])
S_arr   = np.array([r["S"] for r in results])
C_arr   = np.array([r["C"] for r in results])
CD_arr  = np.array([r["CD"] for r in results])
PCA_arr = np.array([r["PCA"] for r in results])
LVR_arr = np.array([r["LVR"] for r in results])
SH_arr  = np.array([r["SH"] for r in results])
nodes   = np.array([r["nodes"] for r in results])
n_pkgs  = np.array([r["n_packages"] for r in results])

# Helper: compute Spearman + AUC
def compute_metrics(metric_arr, panel_arr, name):
    """Compute Spearman ρ and AUC for binary POS/NEG classification."""
    rho, p = stats.spearmanr(metric_arr, panel_arr)
    
    # AUC: POS = panel >= 6.5, NEG = panel < 6.5
    pos_mask = panel_arr >= 6.5
    neg_mask = panel_arr < 6.5
    n_pos = pos_mask.sum()
    n_neg = neg_mask.sum()
    
    if n_pos == 0 or n_neg == 0:
        auc = float('nan')
    else:
        pos_vals = metric_arr[pos_mask]
        neg_vals = metric_arr[neg_mask]
        # AUC = P(pos > neg)
        auc = 0.0
        for pv in pos_vals:
            for nv in neg_vals:
                if pv > nv:
                    auc += 1.0
                elif pv == nv:
                    auc += 0.5
        auc /= (n_pos * n_neg)
    
    return rho, p, auc

# Helper: percentile rank (0-1)
def percentile_rank(arr):
    """Convert raw values to percentile ranks (0=worst, 1=best within sample)."""
    ranks = stats.rankdata(arr, method='average')
    return (ranks - 1) / (len(arr) - 1)

# ═══════════════════════════════════════════════════════════════
# A: PERCENTILE NORMALIZATION (SIG-style)
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("A: PERCENTILE NORMALIZATION")
print("=" * 70)

# A1: Compute percentile ranks
PCA_pct = percentile_rank(PCA_arr)
LVR_pct = percentile_rank(LVR_arr)
SH_pct  = percentile_rank(SH_arr)

# Also percentile-normalize existing metrics for fair comparison
S_pct   = percentile_rank(S_arr)
C_pct   = percentile_rank(C_arr)
M_pct   = percentile_rank(M_arr)

print("\nA1: Percentile distributions")
for name, raw, pct in [("PCA", PCA_arr, PCA_pct), ("LVR", LVR_arr, LVR_pct), 
                         ("SH", SH_arr, SH_pct)]:
    print(f"  {name}: raw range [{raw.min():.4f}, {raw.max():.4f}], "
          f"pct range [{pct.min():.4f}, {pct.max():.4f}], "
          f"raw ceiling (>0.99): {(raw > 0.99).sum()}/{n}")

# A2: Correlation of percentile-normalized metrics with panel
print("\nA2: Correlation with expert panel")
print(f"  {'Metric':<15} {'ρ':>8} {'p-value':>10} {'AUC':>8}  {'vs raw ρ':>10}")
print("  " + "-" * 55)

raw_metrics = {
    "PCA_raw": PCA_arr, "LVR_raw": LVR_arr, "SH_raw": SH_arr,
    "S_raw": S_arr, "C_raw": C_arr,
}
pct_metrics = {
    "PCA_pct": PCA_pct, "LVR_pct": LVR_pct, "SH_pct": SH_pct,
    "S_pct": S_pct, "C_pct": C_pct,
}

# First show raw
for name, arr in raw_metrics.items():
    rho, p, auc = compute_metrics(arr, panel, name)
    print(f"  {name:<15} {rho:>8.3f} {p:>10.4f} {auc:>8.3f}")

print()
# Then show percentile
for name, arr in pct_metrics.items():
    rho, p, auc = compute_metrics(arr, panel, name)
    # Get raw counterpart
    raw_name = name.replace("_pct", "_raw")
    raw_rho, _, _ = compute_metrics(raw_metrics[raw_name], panel, raw_name)
    delta = rho - raw_rho
    print(f"  {name:<15} {rho:>8.3f} {p:>10.4f} {auc:>8.3f}  Δρ={delta:>+.3f}")

# A3: AGQ variants with percentile components
print("\nA3: AGQ with percentile variants")

def agq_formula(m, a, s, c):
    """AGQ = mean(M, A, S, C)"""
    return (m + a + s + c) / 4.0

agq_current = agq_formula(M_arr, A_arr, S_arr, C_arr)
agq_pca_pct = agq_formula(M_arr, A_arr, PCA_pct, C_arr)  # replace S with PCA_pct
agq_lvr_pct = agq_formula(M_arr, A_arr, LVR_pct, C_arr)  # replace S with LVR_pct
agq_sh_pct  = agq_formula(M_arr, A_arr, SH_pct, C_arr)   # replace S with SH_pct
agq_s_pct   = agq_formula(M_arr, A_arr, S_pct, C_arr)     # S itself percentile-normalized

print(f"  {'AGQ variant':<25} {'ρ':>8} {'p-value':>10} {'AUC':>8}")
print("  " + "-" * 55)
for name, arr in [("AGQ(M,A,S,C) current", agq_current),
                   ("AGQ(M,A,S_pct,C)", agq_s_pct),
                   ("AGQ(M,A,PCA_pct,C)", agq_pca_pct),
                   ("AGQ(M,A,LVR_pct,C)", agq_lvr_pct),
                   ("AGQ(M,A,SH_pct,C)", agq_sh_pct)]:
    rho, p, auc = compute_metrics(arr, panel, name)
    print(f"  {name:<25} {rho:>8.3f} {p:>10.4f} {auc:>8.3f}")


# ═══════════════════════════════════════════════════════════════
# B: DUAL-MODE AGQ (Huawei SAI-style)  
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("B: DUAL-MODE AGQ")
print("=" * 70)

# B1: Define two modes
print("\nB1: AGQ mode definitions")
print("  AGQ-benchmark = mean(M, A, S, C)  -- for cross-repo ranking")
print("  AGQ-track     = mean(PCA, LVR, C) -- for within-repo improvement tracking")
print("  (A excluded from track: always 1.0 within repo)")
print("  (S excluded from track: dead within-repo, S=0 in all pilots)")
print("  (M excluded from track: too noisy for small changes)")

agq_benchmark = agq_formula(M_arr, A_arr, S_arr, C_arr)
agq_track = (PCA_arr + LVR_arr + C_arr) / 3.0

# B2: Validate AGQ-benchmark on GT
print("\nB2: AGQ-benchmark validation on GT (n=52)")
for name, arr in [("AGQ-benchmark (M,A,S,C)", agq_benchmark),
                   ("AGQ-track (PCA,LVR,C)", agq_track),
                   ("AGQ(v3c) stored", np.array([r["agq_v3c"] for r in results]))]:
    rho, p, auc = compute_metrics(arr, panel, name)
    print(f"  {name:<30} ρ={rho:>7.3f}  p={p:.4f}  AUC={auc:.3f}")


# ═══════════════════════════════════════════════════════════════
# C: COUNT-BASED METRICS
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("C: COUNT-BASED METRICS")
print("=" * 70)

# C1: Compute count-based alternatives
print("\nC1: Count-based metric definitions")

# PCA is already fraction of packages in SCC / total packages
# But we have raw SCC data from the graph_metrics? No — PCA is 1 - (largest_SCC / total_pkgs)
# So: pkgs_in_SCC = (1 - PCA) * n_packages
# Count-based: #pkgs_NOT_in_SCC (higher = better)
pkgs_in_scc = np.round((1 - PCA_arr) * n_pkgs).astype(int)
pkgs_acyclic = n_pkgs - pkgs_in_scc  # count of acyclic packages
pkgs_acyclic_ratio = pkgs_acyclic / n_pkgs  # same as PCA basically

# For count-based normalized: pkgs_in_SCC per KLOC (inverted — lower is better)
# We don't have KLOC directly, but nodes (classes) is a proxy
# Alternative: use n_packages as denominator (which is what PCA already does)
# More useful count-based: absolute number of violations

# LVR = 1 - violations/total_edges  →  violations = (1 - LVR) * edges
# But we don't have edges in GT data... we have nodes and n_packages
# Let's compute what we can:

# Actually, from E9b we know n_pkg_cycles, dip_violations, layer_bypasses
# But GT data doesn't have those raw counts — only the ratios PCA, LVR, SH

# So for count-based we need to reverse-engineer or re-scan
# Let's work with what we have:
# violations_approx = (1 - LVR) * estimated_edges
# PCA_count = pkgs_in_scc (absolute)

# Relative Cyclicity (from Ch.9 von Zitzewitz):
# RC = 100 * sqrt(sum_of_cyclicity) / n_components
# We don't have cyclicity data, but we can approximate:
# If SCC has k packages, cyclicity ≈ k^2
# RC_approx = 100 * k / n_packages (simplified)

scc_size = np.round((1 - PCA_arr) * n_pkgs).astype(int)
rc_approx = 100.0 * scc_size / n_pkgs  # simplified relative cyclicity (%)

# Violations per 100 nodes (density-based like PIQUE)
# LVR violations approx: we estimate edges ≈ nodes * 2 (typical for Java package graphs)
edges_est = nodes * 2
violations_est = np.round((1 - LVR_arr) * edges_est).astype(int)
violations_per_100nodes = violations_est / (nodes / 100.0)

# Count-based PCA: fraction is already count-based (it's pkgs_in_SCC/total_pkgs)
# But the issue is ceiling — let's try pkgs_in_SCC as absolute count
# and also pkgs_in_SCC / sqrt(n_packages) to penalize larger systems less

pca_count_abs = scc_size  # higher = worse
pca_density = scc_size / np.sqrt(n_pkgs)  # density-adjusted

print(f"  RC_approx (%): range [{rc_approx.min():.1f}, {rc_approx.max():.1f}], "
      f"median={np.median(rc_approx):.1f}, >0: {(rc_approx > 0).sum()}/{n}")
print(f"  violations_per_100nodes: range [{violations_per_100nodes.min():.2f}, "
      f"{violations_per_100nodes.max():.2f}], median={np.median(violations_per_100nodes):.2f}")
print(f"  pkgs_in_SCC (abs): range [{scc_size.min()}, {scc_size.max()}], "
      f"median={np.median(scc_size):.0f}")

# C2: Correlation of count-based metrics with panel
print("\nC2: Count-based metrics correlation with panel")
print(f"  {'Metric':<30} {'ρ':>8} {'p-value':>10} {'AUC':>8}  note")
print("  " + "-" * 65)

# Note: for inverted metrics (higher = worse), negate for correlation
for name, arr, invert in [
    ("PCA (ratio, existing)", PCA_arr, False),
    ("1-RC_approx (inverted)", 1.0 - rc_approx/100.0, False),
    ("RC_approx (% cyclic)", rc_approx, True),
    ("pkgs_in_SCC (abs, inv)", pca_count_abs, True),
    ("pca_density (inv)", pca_density, True),
    ("LVR (ratio, existing)", LVR_arr, False),
    ("violations_per_100n (inv)", violations_per_100nodes, True),
    ("S (existing)", S_arr, False),
    ("C (existing)", C_arr, False),
]:
    if invert:
        # For inverted metrics, negate for Spearman but keep AUC with negated too
        rho, p, auc = compute_metrics(-arr, panel, name)
        note = "(inverted)"
    else:
        rho, p, auc = compute_metrics(arr, panel, name)
        note = ""
    print(f"  {name:<30} {rho:>8.3f} {p:>10.4f} {auc:>8.3f}  {note}")

# ═══════════════════════════════════════════════════════════════
# Additional: AGQ variants with count-based components
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("AGQ VARIANTS COMPARISON (all cross-repo)")
print("=" * 70)

# Normalize count-based to 0-1 range for AGQ composition
def minmax_norm(arr, invert=False):
    """Min-max normalize to [0,1]. If invert, 0=worst becomes 1=best."""
    mn, mx = arr.min(), arr.max()
    if mx == mn:
        return np.full_like(arr, 0.5)
    normed = (arr - mn) / (mx - mn)
    if invert:
        normed = 1.0 - normed
    return normed

rc_norm = minmax_norm(rc_approx, invert=True)  # lower RC = better = higher score
viol_norm = minmax_norm(violations_per_100nodes, invert=True)

agq_rc = agq_formula(M_arr, A_arr, rc_norm, C_arr)  # replace S with RC-based
agq_viol = agq_formula(M_arr, A_arr, viol_norm, C_arr)  # replace S with violation density

print(f"\n  {'AGQ variant':<35} {'ρ':>8} {'p':>8} {'AUC':>8}")
print("  " + "-" * 60)
for name, arr in [
    ("AGQ(M,A,S,C) — current", agq_current),
    ("AGQ(M,A,S_pct,C) — pct norm S", agq_s_pct),
    ("AGQ(M,A,PCA_pct,C) — pct PCA", agq_pca_pct),
    ("AGQ(M,A,LVR_pct,C) — pct LVR", agq_lvr_pct),
    ("AGQ(M,A,SH_pct,C) — pct SH", agq_sh_pct),
    ("AGQ(M,A,RC_norm,C) — count RC", agq_rc),
    ("AGQ(M,A,ViolDens_norm,C) — count", agq_viol),
    ("AGQ-track(PCA,LVR,C) raw", agq_track),
    ("C alone", C_arr),
]:
    rho, p, auc = compute_metrics(arr, panel, name)
    sig = "*" if p < 0.05 else " "
    print(f"  {name:<35} {rho:>8.3f} {p:>7.4f}{sig} {auc:>8.3f}")

# ═══════════════════════════════════════════════════════════════
# Save results for later comparison
# ═══════════════════════════════════════════════════════════════
output = {
    "experiment": "E11_literature_approaches",
    "phase": "cross_repo_GT",
    "n": n,
    "results": {}
}

all_variants = {
    "S_raw": S_arr, "C_raw": C_arr, "PCA_raw": PCA_arr, "LVR_raw": LVR_arr, "SH_raw": SH_arr,
    "PCA_pct": PCA_pct, "LVR_pct": LVR_pct, "SH_pct": SH_pct, "S_pct": S_pct,
    "RC_approx": rc_approx, "viol_per_100n": violations_per_100nodes,
    "AGQ_current": agq_current, "AGQ_S_pct": agq_s_pct,
    "AGQ_PCA_pct": agq_pca_pct, "AGQ_LVR_pct": agq_lvr_pct, "AGQ_SH_pct": agq_sh_pct,
    "AGQ_RC_norm": agq_rc, "AGQ_ViolDens": agq_viol,
    "AGQ_track": agq_track,
}

for name, arr in all_variants.items():
    rho, p, auc = compute_metrics(arr if "RC" not in name and "viol" not in name else 
                                   (-arr if "RC_approx" == name or "viol_per_100n" == name else arr),
                                   panel, name)
    output["results"][name] = {
        "spearman_rho": round(float(rho), 4),
        "p_value": round(float(p), 4),
        "auc": round(float(auc), 3),
    }

out_path = Path(__file__).parent.parent / "artifacts" / "e11_cross_repo_results.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nResults saved to {out_path}")
