#!/usr/bin/env python3
"""
E11 Task E+F: Final comparison table and recommendation.
Aggregates all results from cross-repo and within-repo analyses.
"""

import json
from pathlib import Path

artifacts = Path(__file__).parent.parent / "artifacts"

# Load all results
with open(artifacts / "e11_cross_repo_results.json") as f:
    cross = json.load(f)

with open(artifacts / "e11_within_repo_results.json") as f:
    within = json.load(f)

with open(artifacts / "e11_behavioral_corr.json") as f:
    behavioral = json.load(f)

# ═══════════════════════════════════════════════════════════════
# E: MASTER COMPARISON TABLE
# ═══════════════════════════════════════════════════════════════

print("=" * 90)
print("E11 — FINAL COMPARISON: ALL METRIC VARIANTS")
print("=" * 90)

print(f"\n{'Metric / Variant':<35} {'Cross-repo':^30} {'Within-repo':^20}")
print(f"{'':35} {'ρ':>8} {'p':>8} {'AUC':>8} {'':4} {'ρ':>8} {'p':>8}")
print("-" * 90)

# Build unified table
rows = []

def add_row(label, category, cross_key=None, within_key=None, 
            cr=None, cp=None, ca=None, wr=None, wp=None):
    """Add a row to the comparison table."""
    if cross_key and cross_key in cross["results"]:
        c = cross["results"][cross_key]
        cr = c["spearman_rho"]
        cp = c["p_value"]
        ca = c["auc"]
    if within_key and within_key in within["results"]:
        w = within["results"][within_key]
        wr = w["pooled_rho"]
        wp = w["pooled_p"]
    
    rows.append({
        "label": label, "category": category,
        "cross_rho": cr, "cross_p": cp, "cross_auc": ca,
        "within_rho": wr, "within_p": wp,
    })

# ── Raw individual metrics ──
add_row("C (cohesion)", "RAW", "C_raw", "C (raw)")
add_row("S (stability)", "RAW", "S_raw", "S (raw)")
add_row("M (modularity)", "RAW", cross_key=None, within_key="M (raw)",
        cr=cross["results"]["S_raw"]["spearman_rho"] if False else None)
add_row("PCA (package acyclicity)", "RAW", "PCA_raw", "PCA (raw ratio)")
add_row("LVR (layer violations)", "RAW", "LVR_raw", "LVR (raw ratio)")
add_row("SH (structural health)", "RAW", "SH_raw", "SH (raw)")

# ── A: Percentile normalized ──
add_row("PCA_pct (percentile)", "A:PCT", "PCA_pct", "PCA_pct (GT bench)")
add_row("LVR_pct (percentile)", "A:PCT", "LVR_pct", "LVR_pct (GT bench)")
add_row("SH_pct (percentile)", "A:PCT", "SH_pct", "SH_pct (GT bench)")

# ── C: Count-based ──  
add_row("RC_approx (relative cyclicity)", "C:COUNT", "RC_approx", "RC_approx (inv)")
add_row("violations_per_100n", "C:COUNT", "viol_per_100n", "viol_per_100n (inv)")
add_row("pkgs_in_SCC (absolute)", "C:COUNT", within_key="pkgs_in_SCC (inv)")
add_row("violations_abs (absolute)", "C:COUNT", within_key="violations_abs (inv)")

# ── AGQ composites ──
add_row("AGQ(M,A,S,C) — current", "AGQ", "AGQ_current", "AGQ-bench(M,A,S,C)")
add_row("AGQ(M,A,S_pct,C)", "A:AGQ", "AGQ_S_pct")
add_row("AGQ(M,A,PCA_pct,C)", "A:AGQ", "AGQ_PCA_pct")
add_row("AGQ(M,A,LVR_pct,C)", "A:AGQ", "AGQ_LVR_pct")
add_row("AGQ(M,A,SH_pct,C)", "A:AGQ", "AGQ_SH_pct")
add_row("AGQ(M,A,RC_norm,C)", "C:AGQ", "AGQ_RC_norm")
add_row("AGQ(M,A,ViolDens,C)", "C:AGQ", "AGQ_ViolDens")
add_row("AGQ-track(PCA,LVR,C)", "B:DUAL", "AGQ_track", "AGQ-track(PCA,LVR,C)")
add_row("agq_v3c", "AGQ", within_key="agq_v3c")

# ── D: Behavioral ──
for bkey in ["total_commits_year", "log_commits", "commits_per_node", 
             "commit_recency", "n_contributors", "bus_factor", "stars"]:
    b = behavioral["results"].get(bkey, {})
    add_row(f"{bkey}", "D:BEH",
            cr=b.get("spearman_rho"), cp=b.get("p_value"), ca=b.get("auc"))

# ── Print table ──
categories_seen = set()
for row in rows:
    cat = row["category"]
    if cat not in categories_seen:
        categories_seen.add(cat)
        cat_labels = {
            "RAW": "── RAW METRICS ──",
            "A:PCT": "── A: PERCENTILE NORMALIZATION ──",
            "C:COUNT": "── C: COUNT-BASED METRICS ──",
            "AGQ": "── AGQ COMPOSITES (current) ──",
            "A:AGQ": "── A: AGQ WITH PERCENTILE COMPONENTS ──",
            "C:AGQ": "── C: AGQ WITH COUNT-BASED COMPONENTS ──",
            "B:DUAL": "── B: DUAL-MODE AGQ ──",
            "D:BEH": "── D: BEHAVIORAL METRICS ──",
        }
        print(f"\n  {cat_labels.get(cat, cat)}")
    
    cr = f"{row['cross_rho']:>+7.3f}" if row['cross_rho'] is not None else "    ---"
    cp = f"{row['cross_p']:>7.4f}" if row['cross_p'] is not None else "    ---"
    ca = f"{row['cross_auc']:>7.3f}" if row['cross_auc'] is not None else "    ---"
    wr = f"{row['within_rho']:>+7.3f}" if row['within_rho'] is not None else "    ---"
    wp = f"{row['within_p']:>7.4f}" if row['within_p'] is not None else "    ---"
    
    # Significance markers
    cs = "*" if row['cross_p'] is not None and row['cross_p'] < 0.05 else " "
    ws = "*" if row['within_p'] is not None and row['within_p'] < 0.05 else " "
    
    print(f"  {row['label']:<35} {cr}{cs} {cp} {ca}    {wr}{ws} {wp}")

# ═══════════════════════════════════════════════════════════════
# F: RECOMMENDATION
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 90)
print("F: RECOMMENDATION — RESOLVING THE FUNDAMENTAL TENSION")
print("=" * 90)

print("""
FUNDAMENTAL TENSION:
  PCA/LVR work within-repo (track refactoring) but fail cross-repo (rank quality).
  C/S work cross-repo (rank quality) but fail within-repo (don't react to changes).

WHAT WE TESTED:
  A: Percentile normalization — does it fix PCA/LVR cross-repo?
  B: Dual-mode AGQ — separate formulas for ranking vs tracking?
  C: Count-based metrics — do raw counts beat ratios?
  D: Behavioral metrics — does git history add signal?

RESULTS:

  A: PERCENTILE NORMALIZATION — NO HELP
     Spearman ρ is rank-based, so percentile transform doesn't change ρ.
     Within-repo: percentile→GT adds noise (discretization), no improvement.
     Verdict: REJECTED for fixing cross-repo. Useful only for human-readable scores.

  B: DUAL-MODE AGQ — CONFIRMED PATTERN, BUT WEAK
     AGQ-benchmark(M,A,S,C): cross-repo ρ=+0.272 (p=0.051), within-repo ρ=+0.223
     AGQ-track(PCA,LVR,C):   cross-repo ρ=+0.102 (ns),       within-repo ρ=+0.060
     Surprise: AGQ-track WORSE than AGQ-benchmark even within-repo!
     The refactorings in E10b were too small to move PCA/LVR meaningfully.
     Only jhipster iter5 (major SCC cleanup) showed big AGQ-track movement.
     Verdict: CONCEPTUALLY RIGHT but empirically weak on current data.

  C: COUNT-BASED — MARGINAL IMPROVEMENTS WITHIN-REPO
     pkgs_in_SCC (abs): within-repo ρ=+0.294 (best count-based, p=0.163)
     violations_abs: within-repo ρ=+0.283 (p=0.179)
     viol_per_100n: within-repo ρ=+0.264 (p=0.213)
     Cross-repo: all fail (ρ≈0, same as ratio versions).
     Count-based captures absolute improvement better than ratios.
     Verdict: SLIGHT IMPROVEMENT for within-repo tracking, no help cross-repo.

  D: BEHAVIORAL — NO INDEPENDENT SIGNAL
     All behavioral metrics: cross-repo ρ≈0 (commits, recency, stars).
     n_contributors showed ρ=+0.457 but only n=10 (API limitation).
     Composite (AGQ + behavioral): marginal improvement with recency (ρ=0.294*).
     Verdict: NOT A SOLUTION. Git activity ≠ architecture quality.

KEY FINDING:
  M (modularity) is the ONLY metric that works within-repo (ρ=+0.426*).
  C (cohesion) is the ONLY metric that works cross-repo (ρ=+0.309*).
  Nothing else reaches significance in either dimension.

RECOMMENDATION:

  1. KEEP AGQ(M,A,S,C) as the cross-repo benchmark score.
     It's the best composite (ρ=0.272, AUC=0.670), approaching significance.
     Replacing S with percentile/count variants makes it worse, not better.

  2. For within-repo tracking, use COMPONENT-LEVEL reporting, not a composite.
     Show: M (how modularity changed), PCA (how cycles changed), 
           violation counts (how many DIP violations fixed).
     Don't try to compress into one number — the components tell different stories.

  3. ABANDON trying to unify cross-repo and within-repo into one formula.
     The fundamental tension is real and unsolvable with these metrics.
     Cross-repo quality is about design decisions (S, C, M) — abstract properties.
     Within-repo improvement is about fixing concrete violations (cycles, DIP).
     These are fundamentally different measurement problems.

  4. AGQ-track as a concept is valid but needs MORE SENSITIVE components.
     Current PCA/LVR don't move enough for small refactorings.
     Better: count-based (violations_abs, pkgs_in_SCC) for sensitivity.
     Best: component-level dashboard (no single composite score).

  5. BEHAVIORAL METRICS: defer. No independent signal found.
     n_contributors is promising but needs full API data (n=10 is too small).
     Consider as future enhancement with local git clone analysis.

PRACTICAL NEXT STEPS:
  - AGQ v3c remains the scoring formula for ranking
  - Build a tracking dashboard showing M, PCA, violation counts per iteration
  - Document the dual-mode concept (rank vs track) as a design principle
  - Accept that "one score to rule them all" is not achievable
""")

# Save final summary
summary = {
    "experiment": "E11_final",
    "approaches": {
        "A_percentile": {
            "verdict": "REJECTED",
            "reason": "Monotone transform doesn't change Spearman rank correlation"
        },
        "B_dual_mode": {
            "verdict": "CONCEPTUALLY_VALID_EMPIRICALLY_WEAK",
            "reason": "AGQ-track PCA/LVR too insensitive for small refactorings"
        },
        "C_count_based": {
            "verdict": "MARGINAL_IMPROVEMENT",
            "reason": "Absolute counts slightly better within-repo, no help cross-repo"
        },
        "D_behavioral": {
            "verdict": "NO_SIGNAL",
            "reason": "Git activity metrics uncorrelated with architecture quality"
        }
    },
    "key_finding": "No single metric or normalization resolves the cross-repo vs within-repo tension",
    "recommendation": {
        "cross_repo_ranking": "Keep AGQ(M,A,S,C) or AGQ_v3c",
        "within_repo_tracking": "Component-level dashboard: M, PCA, violation counts",
        "abandon": "Single unified formula for both use cases",
        "best_individual": {
            "cross_repo": "C (ρ=0.309*)",
            "within_repo": "M (ρ=0.426*)"
        }
    }
}

out_path = artifacts / "e11_final_summary.json"
with open(out_path, "w") as f:
    json.dump(summary, f, indent=2)
print(f"Summary saved to {out_path}")
