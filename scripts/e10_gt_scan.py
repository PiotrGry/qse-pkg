"""
E10: Compute PCA, LVR, SH on full GT (n=52 repos from E8).
Compare with S and panel scores.
"""

import json
import os
import sys
import subprocess
import shutil
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
from qse.graph_metrics import (compute_agq, compute_structural_health,
                                compute_package_acyclicity, compute_layer_violation_ratio)
from scipy import stats
import numpy as np


def clone_and_scan(repo_slug, panel, cat):
    """Clone repo, scan, return metrics."""
    url = f"https://github.com/{repo_slug}"
    dest = f"/tmp/gt_scan_{repo_slug.replace('/', '_')}"
    
    try:
        if os.path.exists(dest):
            shutil.rmtree(dest)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, dest],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            return {"repo": repo_slug, "error": "clone_failed"}
        
        scan = scan_java_repo(dest)
        graph, abstract_modules, lcom4 = scan_result_to_agq_inputs(scan)
        agq = compute_agq(graph, abstract_modules, lcom4)
        health = compute_structural_health(graph, scan.internal_nodes, scan.packages)
        
        return {
            "repo": repo_slug,
            "cat": cat,
            "panel": panel,
            "agq_v3c": round(agq.agq_v3c, 4),
            "M": round(agq.modularity, 4),
            "A": round(agq.acyclicity, 4),
            "S": round(agq.stability, 4),
            "C": round(agq.cohesion, 4),
            "CD": round(agq.coupling_density, 4),
            "PCA": health['pca'],
            "LVR": health['lvr'],
            "SH": health['combined'],
            "nodes": graph.number_of_nodes(),
            "n_packages": len(scan.packages),
        }
    except Exception as e:
        return {"repo": repo_slug, "error": str(e)}
    finally:
        if os.path.exists(dest):
            shutil.rmtree(dest)


def main():
    # Load GT repos from E8 results
    with open("artifacts/e8_lfr_results.json") as f:
        e8 = json.load(f)
    
    gt_repos = [(r['repo'], r['panel'], r['cat']) 
                for r in e8['phase2_gt_results'] if 'error' not in r]
    
    print(f"Scanning {len(gt_repos)} GT repos with new metrics...")
    
    results = []
    for i, (repo, panel, cat) in enumerate(gt_repos, 1):
        print(f"\n[{i}/{len(gt_repos)}] {repo}...", end=" ", flush=True)
        r = clone_and_scan(repo, panel, cat)
        if "error" in r:
            print(f"ERROR: {r['error']}")
        else:
            print(f"PCA={r['PCA']:.3f} LVR={r['LVR']:.3f} SH={r['SH']:.3f}")
        results.append(r)
    
    # Filter successful
    ok = [r for r in results if "error" not in r]
    print(f"\n\n{'='*70}")
    print(f"RESULTS: {len(ok)} repos scanned successfully")
    print(f"{'='*70}")
    
    pos = [r for r in ok if r['cat'] == 'POS']
    neg = [r for r in ok if r['cat'] == 'NEG']
    
    # Correlation with panel
    panels = [r['panel'] for r in ok]
    
    print(f"\nSpearman correlation with panel (n={len(ok)}):")
    for comp in ['agq_v3c', 'M', 'A', 'S', 'C', 'CD', 'PCA', 'LVR', 'SH']:
        vals = [r[comp] for r in ok]
        rho, p = stats.spearmanr(vals, panels)
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        print(f"  {comp:>8}: ρ={rho:+.3f} (p={p:.4f}) {sig}")
    
    # Partial correlation controlling for size
    print(f"\nPartial Spearman (controlling for nodes):")
    nodes = [r['nodes'] for r in ok]
    from scipy.stats import spearmanr
    
    for comp in ['agq_v3c', 'M', 'A', 'S', 'C', 'CD', 'PCA', 'LVR', 'SH']:
        vals = [r[comp] for r in ok]
        # Partial correlation: corr(X,Y|Z) ≈ corr of residuals
        rho_xz, _ = spearmanr(vals, nodes)
        rho_yz, _ = spearmanr(panels, nodes)
        rho_xy, _ = spearmanr(vals, panels)
        
        # Partial correlation formula
        if abs(1 - rho_xz**2) > 0.001 and abs(1 - rho_yz**2) > 0.001:
            partial_r = (rho_xy - rho_xz * rho_yz) / ((1 - rho_xz**2)**0.5 * (1 - rho_yz**2)**0.5)
        else:
            partial_r = rho_xy
        
        print(f"  {comp:>8}: partial_r={partial_r:+.3f}")
    
    # Mann-Whitney: POS vs NEG separation
    print(f"\nMann-Whitney U test (POS > NEG):")
    for comp in ['agq_v3c', 'M', 'A', 'S', 'C', 'CD', 'PCA', 'LVR', 'SH']:
        pos_vals = [r[comp] for r in pos]
        neg_vals = [r[comp] for r in neg]
        u, p = stats.mannwhitneyu(pos_vals, neg_vals, alternative='greater')
        auc = u / (len(pos_vals) * len(neg_vals))
        gap = np.mean(pos_vals) - np.mean(neg_vals)
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        print(f"  {comp:>8}: AUC={auc:.3f}, gap={gap:+.3f}, p={p:.4f} {sig}")
    
    # AGQ with PCA/LVR/SH replacing S
    print(f"\nAGQ variants (replacing S):")
    for replacement, label in [
        ('PCA', 'AGQ+PCA'),
        ('LVR', 'AGQ+LVR'),
        ('SH', 'AGQ+SH'),
    ]:
        # Equal weights: 0.20 each for M, A, replacement, C, CD
        pos_vals = [0.20*r['M'] + 0.20*r['A'] + 0.20*r[replacement] + 0.20*r['C'] + 0.20*r['CD'] for r in pos]
        neg_vals = [0.20*r['M'] + 0.20*r['A'] + 0.20*r[replacement] + 0.20*r['C'] + 0.20*r['CD'] for r in neg]
        all_vals = [0.20*r['M'] + 0.20*r['A'] + 0.20*r[replacement] + 0.20*r['C'] + 0.20*r['CD'] for r in ok]
        
        u, p = stats.mannwhitneyu(pos_vals, neg_vals, alternative='greater')
        auc = u / (len(pos_vals) * len(neg_vals))
        gap = np.mean(pos_vals) - np.mean(neg_vals)
        rho, p_rho = stats.spearmanr(all_vals, panels)
        print(f"  {label:>10}: AUC={auc:.3f}, gap={gap:+.3f}, ρ={rho:+.3f} (p={p_rho:.4f})")
    
    # Current AGQ for comparison
    pos_agq = [r['agq_v3c'] for r in pos]
    neg_agq = [r['agq_v3c'] for r in neg]
    u, p = stats.mannwhitneyu(pos_agq, neg_agq, alternative='greater')
    auc = u / (len(pos_agq) * len(neg_agq))
    gap = np.mean(pos_agq) - np.mean(neg_agq)
    rho, p_rho = stats.spearmanr([r['agq_v3c'] for r in ok], panels)
    print(f"  {'AGQ(S)':>10}: AUC={auc:.3f}, gap={gap:+.3f}, ρ={rho:+.3f} (p={p_rho:.4f})  [current]")
    
    # Save results
    output = {
        "experiment": "E10_structural_health_GT",
        "date": datetime.now(timezone.utc).isoformat(),
        "n_scanned": len(ok),
        "results": results,
    }
    with open("artifacts/e10_gt_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to artifacts/e10_gt_results.json")


if __name__ == "__main__":
    main()
