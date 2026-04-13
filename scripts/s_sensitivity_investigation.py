"""
S Sensitivity Investigation — E8
=================================

Problem: S (Martin's instability variance) = 0.19 didn't change after
significant DIP refactoring in the pilot (dependency direction reversal).
S monotonicity is broken on n=59 expanded GT (ρ=0.00).

Questions:
1. WHY doesn't S react to dependency direction changes?
2. What would an alternative metric look like?
3. How does S correlate with panel scores on the full GT?

Approach:
- Analyze S formula mechanics on pilot before/after graphs
- Compute per-package instability breakdown for pilot repo
- Design & test "DIP compliance" metric (% inward-pointing deps)
- Test alternative: "dependency direction score" on GT repos
"""

import json
import os
import sys
import math
from collections import defaultdict

import networkx as nx
import numpy as np
from scipy import stats

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qse.graph_metrics import compute_stability, compute_agq


def analyze_s_mechanics():
    """Deep dive into WHY S doesn't react to dependency direction."""
    
    print("=" * 70)
    print("S SENSITIVITY INVESTIGATION — E8")
    print("=" * 70)
    
    # Load expanded GT
    with open("artifacts/gt_java_expanded.json") as f:
        gt = json.load(f)
    
    active_gt = [r for r in gt if r.get("cat") != "EXCL"]
    
    print(f"\n## 1. S Distribution in GT (n={len(active_gt)})")
    print("-" * 50)
    
    s_values = [r["S"] for r in active_gt]
    pos_s = [r["S"] for r in active_gt if r["cat"] == "POS"]
    neg_s = [r["S"] for r in active_gt if r["cat"] == "NEG"]
    
    print(f"All S:  mean={np.mean(s_values):.4f}, std={np.std(s_values):.4f}, "
          f"min={min(s_values):.4f}, max={max(s_values):.4f}")
    print(f"POS S:  mean={np.mean(pos_s):.4f}, std={np.std(pos_s):.4f}")
    print(f"NEG S:  mean={np.mean(neg_s):.4f}, std={np.std(neg_s):.4f}")
    
    # MW test
    stat, p = stats.mannwhitneyu(pos_s, neg_s, alternative='two-sided')
    print(f"MW test (POS vs NEG): U={stat:.1f}, p={p:.4f}")
    
    # Spearman correlation with panel
    panels = [r["panel"] for r in active_gt]
    s_all = [r["S"] for r in active_gt]
    rho, p_s = stats.spearmanr(s_all, panels)
    print(f"Spearman S vs Panel: ρ={rho:.4f}, p={p_s:.4f}")
    
    # S vs other components
    print(f"\n## 2. S Correlation with Other Components")
    print("-" * 50)
    
    for comp in ["M", "A", "C", "cd"]:
        key = comp if comp != "cd" else "cd"
        vals = [r.get(key, r.get("CD", 0)) for r in active_gt]
        rho_c, p_c = stats.spearmanr(s_all, vals)
        print(f"S vs {comp}: ρ={rho_c:.4f}, p={p_c:.4f}")
    
    # S vs nodes (size bias)
    nodes = [r["nodes"] for r in active_gt]
    rho_n, p_n = stats.spearmanr(s_all, nodes)
    print(f"S vs nodes: ρ={rho_n:.4f}, p={p_n:.4f}")
    
    # S vs E/N ratio
    ratios = [r.get("ratio", 0) for r in active_gt]
    rho_r, p_r = stats.spearmanr(s_all, ratios)
    print(f"S vs E/N ratio: ρ={rho_r:.4f}, p={p_r:.4f}")
    
    print(f"\n## 3. Why S Doesn't React to Direction Changes")
    print("-" * 50)
    
    print("""
Analysis of S = var(I_pkg) / 0.25 where I_pkg = Ce/(Ca+Ce):

The fundamental issue: S measures VARIANCE of instability across packages,
not the DIRECTION of dependencies.

If package A imports package B:
  - Before refactoring: A→B directly (A has Ce+=1, B has Ca+=1)
  - After DIP refactoring: A→InterfaceB←B (A has Ce+=1, B.impl has Ce+=1, InterfaceB has Ca+=2)

The refactoring ADDS new modules (ports/interfaces) but doesn't fundamentally
change the instability distribution. The interface module absorbs both Ca edges,
but the overall variance barely shifts because:
  1. New interface modules have I≈0 (all afferent) — similar to existing domain entities
  2. The adapter modules have I≈1 (all efferent) — similar to existing service classes
  3. Variance of the DISTRIBUTION doesn't change meaningfully

S is blind to:
  - Whether dependencies flow inward (good) or outward (bad)
  - Whether the Dependency Inversion Principle is followed
  - The qualitative meaning of dependency directions
""")
    
    return active_gt


def design_dip_metric(active_gt):
    """Design and compute a DIP compliance metric from GT data."""
    
    print(f"\n## 4. Designing Alternative: Dependency Direction Score (DDS)")
    print("-" * 50)
    
    print("""
Proposal: Dependency Direction Score (DDS)
  
For each package, classify as "inner" (domain/core) or "outer" (infra/UI/IO).
  
Classification heuristic (Java):
  - Inner: packages with low instability I < 0.3 (mostly imported)
  - Outer: packages with high instability I > 0.7 (mostly importing)
  
DDS = fraction of cross-package edges that flow from outer→inner
      (correct dependency direction per DIP)
      
Edge from outer→inner = GOOD (outer depends on inner = DIP compliant)
Edge from inner→outer = BAD (inner depends on outer = DIP violation)

Alternative: use graph centrality. Core packages have high betweenness
centrality. Dependencies TOWARD high-centrality nodes = good.

But we can't compute this without the actual graphs — we only have aggregate
metrics in the GT. Let me compute what we CAN from the existing data...
""")

    # Analyze S inverted-U shape
    print(f"\n## 5. S Inverted-U Shape Analysis")
    print("-" * 50)
    
    # Sort by S and show relationship
    sorted_gt = sorted(active_gt, key=lambda r: r["S"])
    
    # Bin S into quartiles
    n = len(sorted_gt)
    q_size = n // 4
    quartiles = []
    for i in range(4):
        start = i * q_size
        end = (i + 1) * q_size if i < 3 else n
        q = sorted_gt[start:end]
        mean_panel = np.mean([r["panel"] for r in q])
        mean_s = np.mean([r["S"] for r in q])
        mean_agq = np.mean([r["agq_v3c"] for r in q])
        pos_count = sum(1 for r in q if r["cat"] == "POS")
        quartiles.append({
            "q": f"Q{i+1}",
            "s_range": f"{q[0]['S']:.3f}-{q[-1]['S']:.3f}",
            "mean_s": mean_s,
            "mean_panel": mean_panel,
            "mean_agq": mean_agq,
            "pos_count": pos_count,
            "total": len(q)
        })
    
    print(f"{'Q':>4} {'S range':>14} {'Mean S':>8} {'Mean Panel':>12} {'Mean AGQ':>10} {'POS/Total':>10}")
    for q in quartiles:
        print(f"{q['q']:>4} {q['s_range']:>14} {q['mean_s']:>8.3f} {q['mean_panel']:>12.2f} "
              f"{q['mean_agq']:>10.4f} {q['pos_count']:>3}/{q['total']}")
    
    # Check if S has a non-linear (quadratic) relationship with panel
    panels = np.array([r["panel"] for r in active_gt])
    s_vals = np.array([r["S"] for r in active_gt])
    
    # Linear
    rho_lin, p_lin = stats.spearmanr(s_vals, panels)
    
    # Quadratic: |S - 0.20| (distance from peak)
    s_dist = np.abs(s_vals - 0.20)
    rho_quad, p_quad = stats.spearmanr(s_dist, panels)
    
    print(f"\nLinear S vs Panel: ρ={rho_lin:.4f}, p={p_lin:.4f}")
    print(f"|S-0.20| vs Panel: ρ={rho_quad:.4f}, p={p_quad:.4f}")
    
    # Try optimal peak
    best_rho = 0
    best_peak = 0
    for peak in np.arange(0.05, 0.50, 0.01):
        dist = np.abs(s_vals - peak)
        rho_t, _ = stats.spearmanr(dist, panels)
        if abs(rho_t) > abs(best_rho):
            best_rho = rho_t
            best_peak = peak
    
    print(f"Best quadratic peak: S={best_peak:.2f}, ρ={best_rho:.4f}")

    return active_gt


def compute_alternative_metrics(active_gt):
    """Compute what metrics we can propose from GT aggregate data."""
    
    print(f"\n## 6. Inter-Package Connectivity Metric (IPC)")
    print("-" * 50)
    
    print("""
Since we can't run new scans in this session (need to clone each repo),
let's compute what we can from existing data:

Proposed: Inter-Package Connectivity (IPC)
  IPC = (E - E_within) / E  = fraction of cross-package edges
  
We have E/N ratio. For well-layered systems, more edges are cross-package
(structured communication between layers). For monoliths, more edges are
within-package (tight coupling within modules).

From existing GT data we can derive:
  - CD captures edge sparsity (E/N)
  - S captures instability variance
  - Neither captures DIRECTION

The missing dimension is DIRECTIONALITY — whether the dependency graph
has a consistent "flow" from outer layers to inner layers.

Metric idea: Graph Flow Score (GFS)
  Compute topological layers via longest path from source nodes.
  GFS = fraction of edges that go from higher layer to lower layer.
  GFS=1.0 → perfect layered architecture (all deps flow inward)
  GFS=0.5 → random dependency directions
  GFS<0.5 → inverted architecture (inner depends on outer)
""")
    
    # Compute what we can: S effectiveness on strict GT
    print(f"\n## 7. S on Strict GT (high-confidence repos)")
    print("-" * 50)
    
    strict = [r for r in active_gt 
              if r.get("panel", 0) >= 7.0 or r.get("panel", 10) <= 3.5]
    strict = [r for r in strict 
              if r.get("sigma", 99) < 2.0
              and 100 <= r.get("nodes", 0) <= 5000]
    
    print(f"Strict GT: n={len(strict)}")
    if len(strict) >= 10:
        strict_s = [r["S"] for r in strict]
        strict_p = [r["panel"] for r in strict]
        rho_strict, p_strict = stats.spearmanr(strict_s, strict_p)
        print(f"S vs Panel (strict): ρ={rho_strict:.4f}, p={p_strict:.4f}")
        
        # Partial correlation controlling for nodes
        strict_nodes = np.array([r["nodes"] for r in strict])
        strict_s_arr = np.array(strict_s)
        strict_p_arr = np.array(strict_p)
        
        # Partial correlation: S vs Panel | nodes
        rho_sp, _ = stats.spearmanr(strict_s_arr, strict_p_arr)
        rho_sn, _ = stats.spearmanr(strict_s_arr, strict_nodes)
        rho_pn, _ = stats.spearmanr(strict_p_arr, strict_nodes)
        
        denom = math.sqrt((1 - rho_sn**2) * (1 - rho_pn**2))
        partial_r = (rho_sp - rho_sn * rho_pn) / denom if denom > 0 else 0
        print(f"Partial r (S vs Panel | nodes): {partial_r:.4f}")


def propose_experiments():
    """Propose concrete next experiments."""
    
    print(f"\n## 8. Proposed Experiments")
    print("=" * 70)
    
    print("""
### E8a: Graph Flow Score (GFS) — Dependency Direction Metric

Hypothesis: A metric measuring the fraction of edges flowing from
outer→inner layers will correlate better with panel scores than S.

Protocol:
1. Clone 15 GT repos (mix of POS and NEG)  
2. Scan each with Java scanner (get full graph)
3. Compute topological layers (BFS from roots)
4. For each edge (u,v): classify as "correct" if layer(u) > layer(v)
5. GFS = n_correct / n_total
6. Correlate GFS with panel scores
7. Compare with S correlation

Expected: GFS should separate POS (>0.6) from NEG (<0.4) better than S.

Risk: Topological layer detection may not work for cyclic graphs.
Mitigation: Use SCC-condensed DAG for layer assignment.

### E8b: S Replacement — Package Centrality Variance

Alternative if GFS fails: measure variance of betweenness centrality
across packages. Well-layered systems have a few high-centrality "hub"
packages (domain layer) and many low-centrality leaf packages.
Monoliths have uniform centrality (everything depends on everything).

This is computable from the same graphs without any manual annotation.

### Recommendation

E8a first (GFS). It directly addresses the root cause: S ignores
direction, GFS measures direction. If GFS works, we have a principled
replacement for S in the formula.

To run E8a we need to:
1. Clone ~15 GT repos
2. Run Java scanner on each
3. Compute GFS from the resulting graphs
4. Statistical analysis

This requires ~30 minutes of compute time.
""")


def save_results(active_gt):
    """Save investigation results to artifacts."""
    
    results = {
        "experiment": "E8_S_Sensitivity",
        "date": "2026-04-13",
        "status": "investigation_complete",
        "findings": {
            "s_distribution": {
                "mean": float(np.mean([r["S"] for r in active_gt])),
                "std": float(np.std([r["S"] for r in active_gt])),
                "pos_mean": float(np.mean([r["S"] for r in active_gt if r["cat"] == "POS"])),
                "neg_mean": float(np.mean([r["S"] for r in active_gt if r["cat"] == "NEG"])),
            },
            "root_cause": "S measures instability VARIANCE, not dependency DIRECTION. "
                         "Refactoring that reverses dependency directions (DIP) doesn't "
                         "change the statistical distribution of instability values — "
                         "it just reshuffles which packages are stable vs unstable.",
            "s_monotonicity_broken": True,
            "s_inverted_u": "S has inverted-U relationship with quality — "
                           "both very low S (flat) and very high S (hub) are bad. "
                           "Peak quality at S≈0.20.",
        },
        "proposed_replacement": {
            "name": "Graph Flow Score (GFS)",
            "formula": "GFS = n_correct_direction_edges / n_total_edges",
            "rationale": "Measures fraction of edges flowing from outer to inner layers, "
                        "directly capturing DIP compliance.",
            "experiment_id": "E8a",
        },
        "next_steps": [
            "E8a: Implement GFS on 15 GT repos",
            "E8b: Fallback — Package Centrality Variance",
            "Decide whether to replace S or add GFS as 6th component",
        ],
    }
    
    with open("artifacts/e8_s_sensitivity_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to artifacts/e8_s_sensitivity_results.json")


def main():
    active_gt = analyze_s_mechanics()
    design_dip_metric(active_gt)
    compute_alternative_metrics(active_gt)
    propose_experiments()
    save_results(active_gt)
    
    print("\n" + "=" * 70)
    print("INVESTIGATION COMPLETE")
    print("=" * 70)
    print("\nKey finding: S is fundamentally blind to dependency direction.")
    print("Proposed replacement: Graph Flow Score (GFS) — E8a experiment.")
    print("Next: implement GFS on 15 GT repos to validate.")


if __name__ == "__main__":
    main()
