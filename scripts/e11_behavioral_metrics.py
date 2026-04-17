#!/usr/bin/env python3
"""
E11 D1-D3: Behavioral metrics from GitHub API.

Metrics computed:
  1. commit_frequency: total commits in last year (from participation API)
  2. contributor_count: unique contributors (from contributors API)  
  3. commit_recency: fraction of commits in last 3 months vs last year
  4. bus_factor: number of contributors making >10% of commits

Correlation with expert panel (cross-repo).
"""

import json
import subprocess
import time
import numpy as np
from scipy import stats
from pathlib import Path

# ── Load GT data ──────────────────────────────────────────────
gt_path = Path(__file__).parent.parent / "artifacts" / "e10_gt_results.json"
with open(gt_path) as f:
    gt_data = json.load(f)

results = gt_data["results"]
n = len(results)
repos = [r["repo"] for r in results]
panel = np.array([r["panel"] for r in results])

print(f"Collecting behavioral metrics for {n} GT repos via GitHub API...\n")

def gh_api(endpoint, retries=3):
    """Call GitHub API via gh CLI with retry."""
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["gh", "api", endpoint, "--cache", "1h"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
            # Rate limit or empty — retry after delay
            if "rate limit" in result.stderr.lower() or result.returncode != 0:
                time.sleep(2 ** attempt)
                continue
            return None
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            time.sleep(2 ** attempt)
    return None

behavioral_data = []

for i, repo in enumerate(repos):
    print(f"  [{i+1}/{n}] {repo}...", end=" ", flush=True)
    
    # 1. Participation: weekly commit counts for last 52 weeks
    participation = gh_api(f"repos/{repo}/stats/participation")
    if participation and isinstance(participation, dict):
        all_weeks = participation.get("all", [])
        total_commits_year = sum(all_weeks)
        # Recency: commits in last 13 weeks / total 
        recent_commits = sum(all_weeks[-13:]) if len(all_weeks) >= 13 else sum(all_weeks)
        commit_recency = recent_commits / max(total_commits_year, 1)
    else:
        total_commits_year = None
        commit_recency = None
    
    # 2. Contributors: use repos/{owner}/{repo} for basic stats
    repo_info = gh_api(f"repos/{repo}")
    if repo_info and isinstance(repo_info, dict):
        # Get from repo metadata
        open_issues = repo_info.get("open_issues_count", 0)
        forks = repo_info.get("forks_count", 0)
        stars = repo_info.get("stargazers_count", 0)
        size_kb = repo_info.get("size", 0)  # KB
    else:
        open_issues = forks = stars = size_kb = None
    
    # 3. Contributors count (paginated)
    contributors = gh_api(f"repos/{repo}/contributors?per_page=1&anon=true")
    if contributors is not None:
        # Use first page to check — for actual count we'd need Link header
        # Simpler: use stats/contributors
        contrib_stats = gh_api(f"repos/{repo}/stats/contributors")
        if contrib_stats and isinstance(contrib_stats, list):
            n_contributors = len(contrib_stats)
            # Bus factor: contributors making >10% of total commits
            if total_commits_year and total_commits_year > 0:
                threshold = total_commits_year * 0.1
                # Get per-contributor recent commits
                contrib_commits = []
                for c in contrib_stats:
                    weeks = c.get("weeks", [])
                    recent = sum(w.get("c", 0) for w in weeks[-52:]) if weeks else 0
                    contrib_commits.append(recent)
                bus_factor = sum(1 for cc in contrib_commits if cc >= threshold)
            else:
                bus_factor = None
        else:
            n_contributors = None
            bus_factor = None
    else:
        n_contributors = bus_factor = None
    
    entry = {
        "repo": repo,
        "total_commits_year": total_commits_year,
        "commit_recency": round(commit_recency, 4) if commit_recency is not None else None,
        "n_contributors": n_contributors,
        "bus_factor": bus_factor,
        "stars": stars,
        "forks": forks,
        "open_issues": open_issues,
        "size_kb": size_kb,
    }
    behavioral_data.append(entry)
    
    # Summary line
    parts = []
    if total_commits_year is not None:
        parts.append(f"commits={total_commits_year}")
    if n_contributors is not None:
        parts.append(f"contribs={n_contributors}")
    if commit_recency is not None:
        parts.append(f"recency={commit_recency:.2f}")
    if bus_factor is not None:
        parts.append(f"bus={bus_factor}")
    print(", ".join(parts) if parts else "no data")
    
    # Small delay to be nice to API
    time.sleep(0.3)

# ── Save raw behavioral data ─────────────────────────────────
out_path = Path(__file__).parent.parent / "artifacts" / "e11_behavioral_raw.json"
with open(out_path, "w") as f:
    json.dump(behavioral_data, f, indent=2)
print(f"\nRaw data saved to {out_path}")

# ── D3: Correlation analysis ─────────────────────────────────
print("\n" + "=" * 70)
print("D3: BEHAVIORAL METRICS — CORRELATION WITH EXPERT PANEL")
print("=" * 70)

def safe_corr(metric_arr, panel_arr, name):
    """Compute Spearman and AUC, handling NaN."""
    mask = ~np.isnan(metric_arr) & ~np.isnan(panel_arr)
    if mask.sum() < 5:
        return None, None, None, mask.sum()
    rho, p = stats.spearmanr(metric_arr[mask], panel_arr[mask])
    
    # AUC
    pos_mask = panel_arr[mask] >= 6.5
    neg_mask = panel_arr[mask] < 6.5
    n_pos, n_neg = pos_mask.sum(), neg_mask.sum()
    if n_pos > 0 and n_neg > 0:
        pos_vals = metric_arr[mask][pos_mask]
        neg_vals = metric_arr[mask][neg_mask]
        auc = 0.0
        for pv in pos_vals:
            for nv in neg_vals:
                if pv > nv: auc += 1.0
                elif pv == nv: auc += 0.5
        auc /= (n_pos * n_neg)
    else:
        auc = float('nan')
    
    return float(rho), float(p), float(auc), int(mask.sum())

# Build metric arrays
commits_arr = np.array([d["total_commits_year"] if d["total_commits_year"] is not None else np.nan 
                        for d in behavioral_data])
recency_arr = np.array([d["commit_recency"] if d["commit_recency"] is not None else np.nan 
                        for d in behavioral_data])
contribs_arr = np.array([d["n_contributors"] if d["n_contributors"] is not None else np.nan 
                         for d in behavioral_data])
bus_arr = np.array([d["bus_factor"] if d["bus_factor"] is not None else np.nan 
                    for d in behavioral_data])
stars_arr = np.array([d["stars"] if d["stars"] is not None else np.nan 
                      for d in behavioral_data])

# Derived: commits per node (normalized by codebase size)
nodes_arr = np.array([r["nodes"] for r in results])
commits_per_node = commits_arr / nodes_arr

# Derived: contributors per 100 nodes
contribs_per_100n = contribs_arr / (nodes_arr / 100.0)

# Log-transformed (many metrics are log-normal)
log_commits = np.log1p(commits_arr)
log_contribs = np.log1p(contribs_arr)

print(f"\n  {'Metric':<30} {'ρ':>8} {'p':>10} {'AUC':>8} {'n':>5}")
print("  " + "-" * 65)

for name, arr in [
    ("total_commits_year", commits_arr),
    ("log(commits)", log_commits),
    ("commits_per_node", commits_per_node),
    ("commit_recency", recency_arr),
    ("n_contributors", contribs_arr),
    ("log(contributors)", log_contribs),
    ("contribs_per_100nodes", contribs_per_100n),
    ("bus_factor", bus_arr),
    ("stars", stars_arr),
]:
    rho, p, auc, valid_n = safe_corr(arr, panel, name)
    if rho is not None:
        sig = "*" if p < 0.05 else " "
        print(f"  {name:<30} {rho:>8.3f} {p:>10.4f}{sig} {auc:>8.3f} {valid_n:>5}")
    else:
        print(f"  {name:<30} {'n/a':>8} {'---':>10} {'---':>8} {valid_n:>5}")

# Also test existing QSE metrics for comparison
print(f"\n  --- QSE metrics for comparison ---")
for name, key in [("C (cohesion)", "C"), ("M (modularity)", "M"), 
                   ("S (stability)", "S"), ("PCA", "PCA"), ("LVR", "LVR")]:
    arr = np.array([r[key] for r in results])
    rho, p, auc, valid_n = safe_corr(arr, panel, name)
    if rho is not None:
        sig = "*" if p < 0.05 else " "
        print(f"  {name:<30} {rho:>8.3f} {p:>10.4f}{sig} {auc:>8.3f} {valid_n:>5}")

# ── Composite: behavioral + structural ───────────────────────
print(f"\n  --- Composite: behavioral + structural ---")

# AGQ-D: add behavioral signal to AGQ
# Normalize behavioral metrics to 0-1
def minmax_norm(arr, invert=False):
    mask = ~np.isnan(arr)
    if mask.sum() < 2:
        return np.full_like(arr, 0.5)
    mn, mx = np.nanmin(arr), np.nanmax(arr)
    if mx == mn:
        return np.full_like(arr, 0.5)
    normed = (arr - mn) / (mx - mn)
    if invert:
        normed = 1.0 - normed
    return normed

# Try: does adding behavioral metric improve AGQ?
agq_current = np.array([(r["M"] + r["A"] + r["S"] + r["C"]) / 4.0 for r in results])
C_arr = np.array([r["C"] for r in results])

# Recency might be negative signal — active development = less mature?
recency_norm = minmax_norm(recency_arr, invert=True)  # less recent = more stable = better?
commits_norm = minmax_norm(log_commits, invert=True)  # fewer commits = more stable?
contribs_norm = minmax_norm(log_contribs)  # more contributors = better maintained

for name, beh_arr in [
    ("AGQ + recency(inv)", recency_norm),
    ("AGQ + log_commits(inv)", commits_norm),
    ("AGQ + log_contribs", contribs_norm),
]:
    composite = 0.75 * agq_current + 0.25 * beh_arr
    rho, p, auc, valid_n = safe_corr(composite, panel, name)
    if rho is not None:
        sig = "*" if p < 0.05 else " "
        print(f"  {name:<30} {rho:>8.3f} {p:>10.4f}{sig} {auc:>8.3f} {valid_n:>5}")

# Try C + behavioral
for name, beh_arr in [
    ("C + recency(inv)", recency_norm),
    ("C + log_commits(inv)", commits_norm),
    ("C + log_contribs", contribs_norm),
]:
    composite = 0.5 * C_arr + 0.5 * beh_arr
    rho, p, auc, valid_n = safe_corr(composite, panel, name)
    if rho is not None:
        sig = "*" if p < 0.05 else " "
        print(f"  {name:<30} {rho:>8.3f} {p:>10.4f}{sig} {auc:>8.3f} {valid_n:>5}")

# Save correlation results
corr_results = {}
for name, arr in [
    ("total_commits_year", commits_arr),
    ("log_commits", log_commits),
    ("commits_per_node", commits_per_node),
    ("commit_recency", recency_arr),
    ("n_contributors", contribs_arr),
    ("log_contributors", log_contribs),
    ("contribs_per_100nodes", contribs_per_100n),
    ("bus_factor", bus_arr),
    ("stars", stars_arr),
]:
    rho, p, auc, valid_n = safe_corr(arr, panel, name)
    corr_results[name] = {
        "spearman_rho": round(rho, 4) if rho is not None else None,
        "p_value": round(p, 4) if p is not None else None,
        "auc": round(auc, 3) if auc is not None else None,
        "n": valid_n,
    }

out_corr = Path(__file__).parent.parent / "artifacts" / "e11_behavioral_corr.json"
with open(out_corr, "w") as f:
    json.dump({
        "experiment": "E11_behavioral",
        "n": n,
        "results": corr_results,
    }, f, indent=2)
print(f"\nCorrelation results saved to {out_corr}")
