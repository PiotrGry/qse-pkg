#!/usr/bin/env python3
"""E10 — full analysis of new structural metrics on GT (n=52)."""
import json
import numpy as np
from scipy import stats

with open("/home/user/workspace/qse-pkg/artifacts/e10_gt_results.json") as f:
    data = json.load(f)

results = data["results"]
n = len(results)
print(f"=== E10 GT Analysis (n={n}) ===\n")

# Extract arrays
panel = np.array([r["panel"] for r in results])
metrics = {}
for key in ["M", "A", "S", "C", "CD", "PCA", "LVR", "SH"]:
    metrics[key] = np.array([r[key] for r in results])

# 1. Spearman correlations with panel
print("--- 1. Spearman ρ with panel score ---")
for name in ["M", "A", "S", "C", "CD", "PCA", "LVR", "SH"]:
    rho, p = stats.spearmanr(metrics[name], panel)
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "†" if p < 0.1 else "ns"
    print(f"  {name:4s}: ρ={rho:+.3f}  p={p:.4f} {sig}")

# 2. AUC analysis (POS vs NEG)
print("\n--- 2. AUC (POS vs NEG classification) ---")
pos = [r for r in results if r["cat"] == "POS"]
neg = [r for r in results if r["cat"] == "NEG"]
print(f"  POS: {len(pos)}, NEG: {len(neg)}")

for name in ["M", "A", "S", "C", "CD", "PCA", "LVR", "SH"]:
    pos_vals = [r[name] for r in pos]
    neg_vals = [r[name] for r in neg]
    # Mann-Whitney U for AUC
    u, p = stats.mannwhitneyu(pos_vals, neg_vals, alternative="greater")
    auc = u / (len(pos_vals) * len(neg_vals))
    print(f"  {name:4s}: AUC={auc:.3f}  p={p:.4f}")

# 3. LVR ceiling effect analysis
print("\n--- 3. LVR Ceiling Effect ---")
lvr = metrics["LVR"]
print(f"  >= 0.99: {np.sum(lvr >= 0.99)}/{n} ({100*np.sum(lvr >= 0.99)/n:.0f}%)")
print(f"  == 1.0:  {np.sum(lvr == 1.0)}/{n} ({100*np.sum(lvr == 1.0)/n:.0f}%)")
print(f"  < 0.95:  {np.sum(lvr < 0.95)}/{n} ({100*np.sum(lvr < 0.95)/n:.0f}%)")
print(f"  Min: {lvr.min():.4f}  Max: {lvr.max():.4f}  Median: {np.median(lvr):.4f}")

# 4. PCA - library penalty analysis
print("\n--- 4. PCA — Library vs App repos ---")
lib_names = ["google/guava", "apache/commons-lang", "apache/commons-collections",
             "FasterXML/jackson-databind", "remkop/picocli", "resilience4j/resilience4j"]
libs = [r for r in results if r["repo"] in lib_names]
apps = [r for r in results if r["repo"] not in lib_names]
print(f"  Libraries (n={len(libs)}):")
for r in libs:
    print(f"    {r['repo']:45s}  PCA={r['PCA']:.3f}  panel={r['panel']}")
lib_pcas = [r["PCA"] for r in libs]
app_pcas = [r["PCA"] for r in apps]
print(f"  Library PCA mean: {np.mean(lib_pcas):.3f}")
print(f"  App PCA mean:     {np.mean(app_pcas):.3f}")

# 5. AGQ variant comparison
print("\n--- 5. AGQ Variants (replacing S) ---")
# Current AGQ = mean(M, A, S, C)
agq_current = np.array([(r["M"] + r["A"] + r["S"] + r["C"]) / 4 for r in results])
# AGQ with PCA replacing S
agq_pca = np.array([(r["M"] + r["A"] + r["PCA"] + r["C"]) / 4 for r in results])
# AGQ with LVR replacing S
agq_lvr = np.array([(r["M"] + r["A"] + r["LVR"] + r["C"]) / 4 for r in results])
# AGQ with SH replacing S
agq_sh = np.array([(r["M"] + r["A"] + r["SH"] + r["C"]) / 4 for r in results])

for label, agq_arr in [("AGQ(S) current", agq_current), ("AGQ(PCA)", agq_pca), 
                         ("AGQ(LVR)", agq_lvr), ("AGQ(SH)", agq_sh)]:
    rho, p = stats.spearmanr(agq_arr, panel)
    # AUC
    pos_v = [agq_arr[i] for i in range(n) if results[i]["cat"] == "POS"]
    neg_v = [agq_arr[i] for i in range(n) if results[i]["cat"] == "NEG"]
    u, _ = stats.mannwhitneyu(pos_v, neg_v, alternative="greater")
    auc = u / (len(pos_v) * len(neg_v))
    print(f"  {label:20s}: ρ={rho:+.3f}  AUC={auc:.3f}")

# 6. Interesting: what about adding PCA/LVR as 5th metric instead of replacing?
print("\n--- 6. AGQ-5 (adding 5th metric instead of replacing S) ---")
agq5_pca = np.array([(r["M"] + r["A"] + r["S"] + r["C"] + r["PCA"]) / 5 for r in results])
agq5_lvr = np.array([(r["M"] + r["A"] + r["S"] + r["C"] + r["LVR"]) / 5 for r in results])
agq5_sh = np.array([(r["M"] + r["A"] + r["S"] + r["C"] + r["SH"]) / 5 for r in results])

for label, agq_arr in [("AGQ5(+PCA)", agq5_pca), ("AGQ5(+LVR)", agq5_lvr), ("AGQ5(+SH)", agq5_sh)]:
    rho, p = stats.spearmanr(agq_arr, panel)
    pos_v = [agq_arr[i] for i in range(n) if results[i]["cat"] == "POS"]
    neg_v = [agq_arr[i] for i in range(n) if results[i]["cat"] == "NEG"]
    u, _ = stats.mannwhitneyu(pos_v, neg_v, alternative="greater")
    auc = u / (len(pos_v) * len(neg_v))
    print(f"  {label:20s}: ρ={rho:+.3f}  AUC={auc:.3f}")

# 7. Key diagnostic: compare within-repo sensitivity from E9b
print("\n--- 7. Reminder: Within-repo (E9b jhipster) ---")
print("  LVR: ρ=+0.949 (p=0.014) with blind architect score")
print("  PCA: reacted 4/5 iterations, cumulative Δ=+0.468")
print("  S:   0.0000 in ALL iterations (dead)")

# 8. The fundamental tension summary
print("\n=== FUNDAMENTAL TENSION ===")
print("  CROSS-REPO (n=52 GT):")
print("    Best individual: C ρ=+0.309*, AUC=0.717")
print("    S:               ρ=+0.259†, AUC=0.601")
print("    PCA:             ρ=-0.025ns, AUC=0.583")
print("    LVR:             ρ=-0.064ns, AUC=0.519 (ceiling!)")
print()
print("  WITHIN-REPO (iterative pilot):")
print("    Best individual: LVR ρ=+0.949***")
print("    PCA:             reacted 4/5 iterations")
print("    S:               0.000 (dead)")
print()
print("  → These serve DIFFERENT purposes:")
print("    S → cross-repo ranking/benchmarking")
print("    PCA/LVR → within-repo improvement tracking")

# 9. Distribution stats for all metrics
print("\n--- 9. Distribution stats ---")
for name in ["PCA", "LVR", "SH", "S", "C"]:
    vals = metrics[name]
    print(f"  {name:4s}: mean={vals.mean():.3f}  std={vals.std():.3f}  "
          f"min={vals.min():.3f}  max={vals.max():.3f}  median={np.median(vals):.3f}")

# 10. Bonus: C (cohesion) deep-dive since it's the strongest
print("\n--- 10. C (Cohesion) — strongest cross-repo metric ---")
rho_c, p_c = stats.spearmanr(metrics["C"], panel)
print(f"  ρ={rho_c:+.3f}  p={p_c:.4f}")
pos_c = [r["C"] for r in pos]
neg_c = [r["C"] for r in neg]
u_c, p_c_auc = stats.mannwhitneyu(pos_c, neg_c, alternative="greater")
auc_c = u_c / (len(pos_c) * len(neg_c))
print(f"  AUC={auc_c:.3f}  p={p_c_auc:.4f}")
print(f"  POS mean={np.mean(pos_c):.3f}  NEG mean={np.mean(neg_c):.3f}")
print(f"  Separation: {np.mean(pos_c) - np.mean(neg_c):+.3f}")
