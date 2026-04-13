#!/usr/bin/env python3
"""
E11: Within-repo analysis (A4, B3-B4, C3-C4)
Uses E10b data (5 repos with PCA/LVR/SH per iteration).
"""

import json
import numpy as np
from scipy import stats
from pathlib import Path

# ── Load E10b data ──────────────────────────────────────────────
e10b_path = Path(__file__).parent.parent / "artifacts" / "e10b_within_repo_results.json"
with open(e10b_path) as f:
    e10b = json.load(f)

# ── Load GT data for percentile benchmarks ──────────────────────
gt_path = Path(__file__).parent.parent / "artifacts" / "e10_gt_results.json"
with open(gt_path) as f:
    gt_data = json.load(f)

gt_pca = np.array([r["PCA"] for r in gt_data["results"]])
gt_lvr = np.array([r["LVR"] for r in gt_data["results"]])
gt_sh  = np.array([r["SH"]  for r in gt_data["results"]])
gt_c   = np.array([r["C"]   for r in gt_data["results"]])

def gt_percentile(value, gt_arr):
    """What percentile rank would 'value' get in the GT benchmark?"""
    return float(np.mean(gt_arr <= value))

# ═══════════════════════════════════════════════════════════════
# Helper: per-repo Spearman of metric trajectory vs blind scores
# ═══════════════════════════════════════════════════════════════
def within_repo_correlation(repos, metric_key, include_baseline=True):
    """Compute per-repo Spearman ρ and pooled ρ for a given metric.
    
    Returns dict with per-repo rho and pooled results.
    """
    per_repo = {}
    all_metrics = []
    all_blinds = []
    
    for repo in repos:
        name = repo["repo"]
        baseline = repo["baseline"]
        iterations = repo["iterations"]
        
        metrics = []
        blinds = []
        
        if include_baseline and metric_key in baseline:
            metrics.append(baseline[metric_key])
            blinds.append(repo.get("panel", 5))  # baseline = pre-refactoring
        
        for it in iterations:
            m = it["metrics_after"]
            if metric_key in m:
                metrics.append(m[metric_key])
                blinds.append(it["blind_score"])
        
        if len(metrics) >= 3:
            rho, p = stats.spearmanr(metrics, blinds)
            per_repo[name] = {"rho": round(rho, 4), "p": round(p, 4), "n": len(metrics)}
        else:
            per_repo[name] = {"rho": None, "p": None, "n": len(metrics), "note": "too few points"}
        
        all_metrics.extend(metrics)
        all_blinds.extend(blinds)
    
    # Pooled correlation
    if len(all_metrics) >= 5:
        pooled_rho, pooled_p = stats.spearmanr(all_metrics, all_blinds)
    else:
        pooled_rho, pooled_p = float('nan'), float('nan')
    
    return {
        "per_repo": per_repo,
        "pooled_rho": round(float(pooled_rho), 4),
        "pooled_p": round(float(pooled_p), 4),
        "pooled_n": len(all_metrics),
    }

def compute_trajectory(repos, metric_fn, label, include_baseline=True):
    """Compute metric trajectory for a function that takes full iteration data."""
    per_repo = {}
    all_metrics = []
    all_blinds = []
    
    for repo in repos:
        name = repo["repo"]
        baseline = repo["baseline"]
        iterations = repo["iterations"]
        
        metrics = []
        blinds = []
        
        if include_baseline:
            val = metric_fn(baseline)
            if val is not None:
                metrics.append(val)
                blinds.append(repo.get("panel", 5))
        
        for it in iterations:
            m = it["metrics_after"]
            val = metric_fn(m)
            if val is not None:
                metrics.append(val)
                blinds.append(it["blind_score"])
        
        if len(metrics) >= 3:
            rho, p = stats.spearmanr(metrics, blinds)
            per_repo[name] = {"rho": round(rho, 4), "p": round(p, 4), "n": len(metrics),
                              "trajectory": [round(v, 4) for v in metrics]}
        else:
            per_repo[name] = {"rho": None, "p": None, "n": len(metrics), "note": "too few"}
        
        all_metrics.extend(metrics)
        all_blinds.extend(blinds)
    
    if len(all_metrics) >= 5:
        pooled_rho, pooled_p = stats.spearmanr(all_metrics, all_blinds)
    else:
        pooled_rho, pooled_p = float('nan'), float('nan')
    
    return {
        "per_repo": per_repo,
        "pooled_rho": round(float(pooled_rho), 4),
        "pooled_p": round(float(pooled_p), 4),
        "pooled_n": len(all_metrics),
    }

repos = e10b["repos"]
print(f"Loaded E10b: {len(repos)} repos\n")

# Show repo overview
for repo in repos:
    n_iters = repo["n_iterations"]
    blinds = [it["blind_score"] for it in repo["iterations"]]
    print(f"  {repo['repo']:<45} panel={repo.get('panel','?')}, {n_iters} iters, blinds={blinds}")
print()

# ═══════════════════════════════════════════════════════════════
# A4: PERCENTILE-NORMALIZED METRICS WITHIN-REPO
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("A4: PERCENTILE NORMALIZATION — WITHIN-REPO TEST")
print("=" * 70)

# For within-repo: use GT as external benchmark
# Map each iteration's raw PCA/LVR to its percentile in GT distribution
def pca_pct(m):
    v = m.get("PCA")
    return gt_percentile(v, gt_pca) if v is not None else None

def lvr_pct(m):
    v = m.get("LVR")
    return gt_percentile(v, gt_lvr) if v is not None else None

def sh_pct(m):
    v = m.get("SH")
    return gt_percentile(v, gt_sh) if v is not None else None

print("\nRaw PCA/LVR/SH within-repo:")
for key in ["PCA", "LVR", "SH"]:
    res = within_repo_correlation(repos, key)
    print(f"  {key:<10} pooled ρ={res['pooled_rho']:>7.3f}  p={res['pooled_p']:.4f}  n={res['pooled_n']}")
    for name, r in res["per_repo"].items():
        short = name.split("/")[-1][:25]
        if r["rho"] is not None:
            print(f"    {short:<25} ρ={r['rho']:>7.3f}  p={r['p']:.4f}  n={r['n']}")
        else:
            print(f"    {short:<25} {r.get('note', 'n/a')}")

print("\nPercentile-normalized PCA/LVR/SH within-repo (vs GT benchmark):")
for label, fn in [("PCA_pct", pca_pct), ("LVR_pct", lvr_pct), ("SH_pct", sh_pct)]:
    res = compute_trajectory(repos, fn, label)
    print(f"  {label:<10} pooled ρ={res['pooled_rho']:>7.3f}  p={res['pooled_p']:.4f}  n={res['pooled_n']}")
    for name, r in res["per_repo"].items():
        short = name.split("/")[-1][:25]
        if r["rho"] is not None:
            print(f"    {short:<25} ρ={r['rho']:>7.3f}  traj={r.get('trajectory', [])}")

# Key question: does percentile add info? For within-repo, pct is monotone transform
# of raw, so Spearman ρ should be identical. But with GT benchmark, there's potential
# for information gain if GT distribution is non-uniform.

# ═══════════════════════════════════════════════════════════════
# B3: AGQ-TRACK WITHIN-REPO VALIDATION
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("B3: AGQ-TRACK (PCA, LVR, C) — WITHIN-REPO")
print("=" * 70)

def agq_track(m):
    pca = m.get("PCA")
    lvr = m.get("LVR")
    c = m.get("C")
    if pca is not None and lvr is not None and c is not None:
        return (pca + lvr + c) / 3.0
    return None

def agq_benchmark(m):
    M = m.get("M")
    A = m.get("A")
    S = m.get("S")
    C = m.get("C")
    if all(v is not None for v in [M, A, S, C]):
        return (M + A + S + C) / 4.0
    return None

print("\nAGQ-track vs AGQ-benchmark vs individual metrics (within-repo):")
metrics_to_test = [
    ("AGQ-track(PCA,LVR,C)", agq_track),
    ("AGQ-bench(M,A,S,C)", agq_benchmark),
    ("agq_v3c", lambda m: m.get("agq_v3c")),
    ("PCA", lambda m: m.get("PCA")),
    ("LVR", lambda m: m.get("LVR")),
    ("C", lambda m: m.get("C")),
    ("M", lambda m: m.get("M")),
    ("S", lambda m: m.get("S")),
    ("SH", lambda m: m.get("SH")),
    ("CD", lambda m: m.get("CD")),
]

results_table = []
print(f"\n  {'Metric':<25} {'pooled ρ':>10} {'pooled p':>10} {'n':>5}")
print("  " + "-" * 55)

for label, fn in metrics_to_test:
    res = compute_trajectory(repos, fn, label)
    sig = "*" if res["pooled_p"] < 0.05 else " "
    print(f"  {label:<25} {res['pooled_rho']:>10.3f} {res['pooled_p']:>10.4f}{sig} {res['pooled_n']:>5}")
    results_table.append({"metric": label, **res})

# ═══════════════════════════════════════════════════════════════
# B4: WHERE AGQ-TRACK REACTS BUT AGQ-BENCHMARK DOESN'T
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("B4: AGQ-TRACK vs AGQ-BENCHMARK — PER REPO COMPARISON")
print("=" * 70)

for repo in repos:
    name = repo["repo"].split("/")[-1]
    baseline = repo["baseline"]
    iterations = repo["iterations"]
    
    print(f"\n  {name}:")
    print(f"    {'Iter':<6} {'blind':>6} {'AGQ-bench':>10} {'Δ-bench':>8} {'AGQ-track':>10} {'Δ-track':>8} {'PCA':>6} {'LVR':>6} {'S':>6}")
    
    prev_bench = agq_benchmark(baseline)
    prev_track = agq_track(baseline)
    
    print(f"    {'base':<6} {'---':>6} {prev_bench:>10.4f} {'---':>8} {prev_track:>10.4f} {'---':>8} "
          f"{baseline.get('PCA',0):>6.3f} {baseline.get('LVR',0):>6.3f} {baseline.get('S',0):>6.3f}")
    
    for it in iterations:
        m = it["metrics_after"]
        bench = agq_benchmark(m)
        track = agq_track(m)
        d_bench = bench - prev_bench if bench and prev_bench else 0
        d_track = track - prev_track if track and prev_track else 0
        
        print(f"    {it['id']:<6} {it['blind_score']:>6} {bench:>10.4f} {d_bench:>+8.4f} {track:>10.4f} {d_track:>+8.4f} "
              f"{m.get('PCA',0):>6.3f} {m.get('LVR',0):>6.3f} {m.get('S',0):>6.3f}")
        
        prev_bench = bench
        prev_track = track

# ═══════════════════════════════════════════════════════════════
# C3: COUNT-BASED METRICS WITHIN-REPO
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("C3: COUNT-BASED METRICS — WITHIN-REPO")
print("=" * 70)

def rc_approx(m):
    """Relative cyclicity ≈ 100 * largest_scc / n_packages"""
    scc = m.get("largest_scc")
    n_pkgs = m.get("n_packages")
    if scc is not None and n_pkgs and n_pkgs > 0:
        return 100.0 * scc / n_pkgs
    return None

def violations_per_100n(m):
    """(dip_violations + layer_bypasses) / (nodes/100)"""
    dip = m.get("dip_violations", 0)
    bypasses = m.get("layer_bypasses", 0)
    nodes = m.get("nodes", 1)
    if nodes > 0:
        return (dip + bypasses) / (nodes / 100.0)
    return None

def violations_abs(m):
    """Absolute violation count (inverted: negative = lower is better)"""
    dip = m.get("dip_violations", 0)
    bypasses = m.get("layer_bypasses", 0)
    return -(dip + bypasses)  # negate so higher = better for Spearman

def pkgs_in_scc(m):
    """Number of packages in largest SCC (inverted: fewer = better)"""
    scc = m.get("largest_scc")
    if scc is not None:
        return -scc  # negate so higher = better
    return None

count_metrics = [
    ("RC_approx (inv)", lambda m: -rc_approx(m) if rc_approx(m) is not None else None),
    ("viol_per_100n (inv)", lambda m: -violations_per_100n(m) if violations_per_100n(m) is not None else None),
    ("violations_abs (inv)", violations_abs),
    ("pkgs_in_SCC (inv)", pkgs_in_scc),
    ("PCA (raw)", lambda m: m.get("PCA")),
    ("LVR (raw)", lambda m: m.get("LVR")),
]

print(f"\n  {'Metric':<25} {'pooled ρ':>10} {'pooled p':>10} {'n':>5}")
print("  " + "-" * 55)

for label, fn in count_metrics:
    res = compute_trajectory(repos, fn, label)
    sig = "*" if res["pooled_p"] < 0.05 else " "
    print(f"  {label:<25} {res['pooled_rho']:>10.3f} {res['pooled_p']:>10.4f}{sig} {res['pooled_n']:>5}")

# Per-repo detail for count-based
print("\nPer-repo count-based trajectories:")
for repo in repos:
    name = repo["repo"].split("/")[-1][:20]
    baseline = repo["baseline"]
    print(f"\n  {name}:")
    print(f"    {'Iter':<6} {'blind':>6} {'RC%':>8} {'viol':>6} {'dip':>5} {'byp':>5} {'scc':>5} {'PCA':>6} {'LVR':>6}")
    
    rc = rc_approx(baseline)
    dip = baseline.get("dip_violations", 0)
    byp = baseline.get("layer_bypasses", 0)
    scc = baseline.get("largest_scc", 0)
    print(f"    {'base':<6} {'---':>6} {rc if rc else 0:>8.1f} {dip+byp:>6} {dip:>5} {byp:>5} {scc:>5} "
          f"{baseline.get('PCA',0):>6.3f} {baseline.get('LVR',0):>6.3f}")
    
    for it in repo["iterations"]:
        m = it["metrics_after"]
        rc = rc_approx(m)
        dip = m.get("dip_violations", 0)
        byp = m.get("layer_bypasses", 0)
        scc = m.get("largest_scc", 0)
        print(f"    {it['id']:<6} {it['blind_score']:>6} {rc if rc else 0:>8.1f} {dip+byp:>6} {dip:>5} {byp:>5} {scc:>5} "
              f"{m.get('PCA',0):>6.3f} {m.get('LVR',0):>6.3f}")

# ═══════════════════════════════════════════════════════════════
# C4: COMPARISON TABLE — count vs ratio vs percentile (within-repo)
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("C4: COMPARISON — ALL VARIANTS WITHIN-REPO")
print("=" * 70)

all_within_metrics = [
    ("PCA (raw ratio)", lambda m: m.get("PCA")),
    ("PCA_pct (GT bench)", pca_pct),
    ("RC_approx (inv)", lambda m: -rc_approx(m) if rc_approx(m) is not None else None),
    ("pkgs_in_SCC (inv)", pkgs_in_scc),
    ("LVR (raw ratio)", lambda m: m.get("LVR")),
    ("LVR_pct (GT bench)", lvr_pct),
    ("viol_per_100n (inv)", lambda m: -violations_per_100n(m) if violations_per_100n(m) is not None else None),
    ("violations_abs (inv)", violations_abs),
    ("SH (raw)", lambda m: m.get("SH")),
    ("SH_pct (GT bench)", sh_pct),
    ("S (raw)", lambda m: m.get("S")),
    ("C (raw)", lambda m: m.get("C")),
    ("M (raw)", lambda m: m.get("M")),
    ("AGQ-track(PCA,LVR,C)", agq_track),
    ("AGQ-bench(M,A,S,C)", agq_benchmark),
    ("agq_v3c", lambda m: m.get("agq_v3c")),
]

print(f"\n  {'Metric':<25} {'pooled ρ':>10} {'pooled p':>10} {'n':>5} {'sig':>5}")
print("  " + "-" * 60)

output_results = {}
for label, fn in all_within_metrics:
    res = compute_trajectory(repos, fn, label)
    sig = "*" if res["pooled_p"] < 0.05 else ""
    if res["pooled_p"] < 0.01:
        sig = "**"
    if res["pooled_p"] < 0.001:
        sig = "***"
    print(f"  {label:<25} {res['pooled_rho']:>10.3f} {res['pooled_p']:>10.4f} {res['pooled_n']:>5} {sig:>5}")
    output_results[label] = {
        "pooled_rho": res["pooled_rho"],
        "pooled_p": res["pooled_p"],
        "pooled_n": res["pooled_n"],
        "per_repo": {k: v for k, v in res["per_repo"].items()},
    }

# ═══════════════════════════════════════════════════════════════
# Save results
# ═══════════════════════════════════════════════════════════════
out_path = Path(__file__).parent.parent / "artifacts" / "e11_within_repo_results.json"
with open(out_path, "w") as f:
    json.dump({
        "experiment": "E11_within_repo",
        "n_repos": len(repos),
        "repos": [r["repo"] for r in repos],
        "results": output_results,
    }, f, indent=2, default=str)

print(f"\nResults saved to {out_path}")
