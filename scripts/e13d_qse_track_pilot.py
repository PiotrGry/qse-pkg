#!/usr/bin/env python3
"""E13d: QSE-Track Within-Repo Pilot — scan/fix/measure with architect panel.

Uses E10b data (5 repos × multiple refactoring iterations with blind_score)
to validate QSE-Track metrics (M, PCA, dip_violations, largest_scc) against
architect panel assessments.

Key questions:
1. Does QSE-Track correlate with blind architect scores within each repo?
2. How does QSE-Track compare to AGQ and SH for within-repo monitoring?
3. Can QSE-Track generate meaningful before/after reports?
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from scipy import stats

# ── Load E10b data ──────────────────────────────────────────────────────

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"
E10B_PATH = ARTIFACTS / "e10b_within_repo_results.json"

with open(E10B_PATH) as f:
    E10B = json.load(f)


# ── Extract QSE-Track metrics from existing E10b measurements ──────────

def extract_qse_track(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the 4 QSE-Track signals from E10b metric dict."""
    return {
        "M": metrics.get("M", 0.0),
        "PCA": metrics.get("PCA", 0.0),
        "dip_violations": metrics.get("dip_violations", 0),
        "largest_scc": metrics.get("largest_scc", 0),
    }


def compute_qse_track_composite(track: Dict[str, Any], n_packages: int = 10) -> float:
    """Composite QSE-Track score for within-repo delta comparison.

    Combines the 4 tracked signals into a single score [0, 1]:
      - M:              direct (higher = better), weight 0.4
      - PCA:            direct (higher = better), weight 0.3
      - dip_violations: inverted, normalized by n_packages, weight 0.2
      - largest_scc:    inverted, normalized by n_packages, weight 0.1

    The weights reflect E10b findings: M is the only significant predictor
    (ρ=0.426*), PCA reacts to cycle-breaking, violations/scc are structural
    problem counts.
    """
    m = track["M"]
    pca = track["PCA"]

    # Normalize violation counts relative to repo size
    dip_norm = max(0.0, 1.0 - (track["dip_violations"] / max(n_packages, 1)))
    scc_norm = max(0.0, 1.0 - (track["largest_scc"] / max(n_packages, 1)))

    composite = 0.4 * m + 0.3 * pca + 0.2 * dip_norm + 0.1 * scc_norm
    return round(composite, 4)


# ── Process each repo ──────────────────────────────────────────────────

def process_repo(repo_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process one repo through QSE-Track and correlate with blind_score."""
    repo_name = repo_data["repo"].split("/")[-1]
    baseline = repo_data["baseline"]
    iterations = repo_data["iterations"]
    n_packages = baseline.get("n_packages", 10)

    # Baseline QSE-Track
    baseline_track = extract_qse_track(baseline)
    baseline_composite = compute_qse_track_composite(baseline_track, n_packages)

    # Process iterations
    iter_results = []
    for it in iterations:
        ma = it["metrics_after"]
        track = extract_qse_track(ma)
        n_pkg_iter = ma.get("n_packages", n_packages)
        composite = compute_qse_track_composite(track, n_pkg_iter)

        # Deltas vs baseline
        delta_m = track["M"] - baseline_track["M"]
        delta_pca = track["PCA"] - baseline_track["PCA"]
        delta_dip = track["dip_violations"] - baseline_track["dip_violations"]
        delta_scc = track["largest_scc"] - baseline_track["largest_scc"]
        delta_composite = composite - baseline_composite

        # Also extract AGQ and SH for comparison
        agq = ma.get("agq_v3c", 0.0)
        sh = ma.get("SH", 0.0)

        iter_results.append({
            "id": it["id"],
            "refactoring": it["refactoring"],
            "description": it["description"],
            "blind_score": it["blind_score"],
            "qse_track": track,
            "qse_track_composite": composite,
            "delta_vs_baseline": {
                "M": round(delta_m, 4),
                "PCA": round(delta_pca, 4),
                "dip_violations": delta_dip,
                "largest_scc": delta_scc,
                "composite": round(delta_composite, 4),
            },
            "comparison": {
                "agq": agq,
                "sh": sh,
                "agq_delta": round(agq - baseline.get("agq_v3c", 0.0), 4),
                "sh_delta": round(sh - baseline.get("SH", 0.0), 4),
            },
        })

    # ── Correlations within this repo ──
    if len(iter_results) >= 3:
        blind_scores = [r["blind_score"] for r in iter_results]
        composites = [r["qse_track_composite"] for r in iter_results]
        m_values = [r["qse_track"]["M"] for r in iter_results]
        agq_values = [r["comparison"]["agq"] for r in iter_results]
        sh_values = [r["comparison"]["sh"] for r in iter_results]

        correlations = {}
        for name, values in [
            ("qse_track_composite", composites),
            ("M", m_values),
            ("agq", agq_values),
            ("sh", sh_values),
        ]:
            if len(set(values)) > 1 and len(set(blind_scores)) > 1:
                rho, p = stats.spearmanr(values, blind_scores)
                correlations[name] = {"rho": round(rho, 4), "p": round(p, 4)}
            else:
                correlations[name] = {"rho": float("nan"), "p": float("nan"), "note": "no variance"}
    else:
        correlations = {"note": f"too few iterations (n={len(iter_results)})"}

    return {
        "repo": repo_name,
        "full_name": repo_data["repo"],
        "n_iterations": len(iterations),
        "n_packages": n_packages,
        "panel_score": repo_data.get("panel", None),
        "baseline": {
            "qse_track": baseline_track,
            "qse_track_composite": baseline_composite,
            "agq": baseline.get("agq_v3c", 0.0),
            "sh": baseline.get("SH", 0.0),
        },
        "iterations": iter_results,
        "correlations": correlations,
    }


# ── Pooled analysis across all repos ───────────────────────────────────

def pooled_analysis(repo_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute pooled correlations and summary statistics across all repos."""

    # Collect all iteration data points (pooled)
    all_blind = []
    all_composite = []
    all_m = []
    all_agq = []
    all_sh = []
    all_delta_m = []
    all_delta_composite = []
    all_delta_agq = []
    all_delta_sh = []
    all_delta_blind = []

    for repo in repo_results:
        prev_blind = None
        for it in repo["iterations"]:
            all_blind.append(it["blind_score"])
            all_composite.append(it["qse_track_composite"])
            all_m.append(it["qse_track"]["M"])
            all_agq.append(it["comparison"]["agq"])
            all_sh.append(it["comparison"]["sh"])
            all_delta_m.append(it["delta_vs_baseline"]["M"])
            all_delta_composite.append(it["delta_vs_baseline"]["composite"])
            all_delta_agq.append(it["comparison"]["agq_delta"])
            all_delta_sh.append(it["comparison"]["sh_delta"])

            if prev_blind is not None:
                all_delta_blind.append(it["blind_score"] - prev_blind)
            prev_blind = it["blind_score"]

    n = len(all_blind)

    # Absolute correlations (metric value vs blind_score)
    abs_corr = {}
    for name, values in [
        ("qse_track_composite", all_composite),
        ("M", all_m),
        ("agq", all_agq),
        ("sh", all_sh),
    ]:
        if len(set(values)) > 1 and len(set(all_blind)) > 1:
            rho, p = stats.spearmanr(values, all_blind)
            abs_corr[name] = {"rho": round(rho, 4), "p": round(p, 4), "n": n}
        else:
            abs_corr[name] = {"rho": float("nan"), "p": float("nan"), "n": n}

    # Delta correlations (delta from baseline vs blind_score)
    delta_corr = {}
    for name, values in [
        ("delta_composite", all_delta_composite),
        ("delta_M", all_delta_m),
        ("delta_agq", all_delta_agq),
        ("delta_sh", all_delta_sh),
    ]:
        if len(set(values)) > 1 and len(set(all_blind)) > 1:
            rho, p = stats.spearmanr(values, all_blind)
            delta_corr[name] = {"rho": round(rho, 4), "p": round(p, 4), "n": n}
        else:
            delta_corr[name] = {"rho": float("nan"), "p": float("nan"), "n": n}

    # Direction agreement: does metric delta agree with blind_score trend?
    direction_agree = {
        "qse_track_composite": 0,
        "M": 0,
        "agq": 0,
        "sh": 0,
        "total": 0,
    }
    for repo in repo_results:
        for it in repo["iterations"]:
            dm = it["delta_vs_baseline"]["composite"]
            blind = it["blind_score"]
            baseline_panel = repo.get("panel_score")
            # If blind_score > panel (baseline estimate), refactoring improved
            # If delta_composite > 0, QSE-Track also says improved
            # Simple: does sign of delta match (blind_score - mean_baseline)?
            direction_agree["total"] += 1

            # Positive delta = improvement
            is_blind_positive = blind >= 5  # 5+ considered improvement
            is_composite_positive = dm > 0
            is_m_positive = it["delta_vs_baseline"]["M"] > 0
            is_agq_positive = it["comparison"]["agq_delta"] > 0
            is_sh_positive = it["comparison"]["sh_delta"] > 0

            if is_blind_positive == is_composite_positive:
                direction_agree["qse_track_composite"] += 1
            if is_blind_positive == is_m_positive:
                direction_agree["M"] += 1
            if is_blind_positive == is_agq_positive:
                direction_agree["agq"] += 1
            if is_blind_positive == is_sh_positive:
                direction_agree["sh"] += 1

    total = direction_agree["total"]
    direction_pcts = {}
    if total > 0:
        for key in ["qse_track_composite", "M", "agq", "sh"]:
            direction_pcts[key] = round(direction_agree[key] / total * 100, 1)

    return {
        "n_repos": len(repo_results),
        "n_iterations_total": n,
        "absolute_correlations": abs_corr,
        "delta_correlations": delta_corr,
        "direction_agreement_pct": direction_pcts,
    }


# ── Three-layer report per repo ────────────────────────────────────────

def generate_three_layer_report(repo_result: Dict[str, Any]) -> str:
    """Generate a 3-layer QSE report for one repo (before/after each iteration)."""
    lines = []
    name = repo_result["repo"]
    bl = repo_result["baseline"]

    lines.append(f"{'='*70}")
    lines.append(f"QSE Three-Layer Report: {name}")
    lines.append(f"{'='*70}")
    lines.append("")

    # Layer 1: QSE-Rank (cross-repo position — from baseline only)
    lines.append("── Layer 1: QSE-Rank (Cross-Repo Benchmark) ──")
    lines.append(f"  AGQ (baseline):  {bl['agq']:.4f}")
    lines.append(f"  Note: QSE-Rank uses C and S which have Δ=0.0 within-repo")
    lines.append(f"  → Not applicable for within-repo monitoring")
    lines.append("")

    # Layer 2: QSE-Track (iteration monitoring)
    lines.append("── Layer 2: QSE-Track (Within-Repo Monitoring) ──")
    lines.append(f"  Baseline: M={bl['qse_track']['M']:.4f}  PCA={bl['qse_track']['PCA']:.4f}  "
                 f"dip={bl['qse_track']['dip_violations']}  scc={bl['qse_track']['largest_scc']}  "
                 f"composite={bl['qse_track_composite']:.4f}")
    lines.append("")

    for it in repo_result["iterations"]:
        t = it["qse_track"]
        d = it["delta_vs_baseline"]
        blind = it["blind_score"]
        arrow = lambda v: "▲" if v > 0 else ("▼" if v < 0 else "─")

        lines.append(f"  Iteration {it['id']}: {it['refactoring']}")
        lines.append(f"    {it['description'][:80]}")
        lines.append(f"    Panel blind_score: {blind}/10")
        lines.append(f"    QSE-Track: M={t['M']:.4f}{arrow(d['M'])}  PCA={t['PCA']:.4f}{arrow(d['PCA'])}  "
                     f"dip={t['dip_violations']}{arrow(-d['dip_violations'])}  "  # inverted: less = better
                     f"scc={t['largest_scc']}{arrow(-d['largest_scc'])}  "
                     f"composite={it['qse_track_composite']:.4f}{arrow(d['composite'])}")
        lines.append(f"    Δ baseline: M={d['M']:+.4f}  PCA={d['PCA']:+.4f}  "
                     f"dip={d['dip_violations']:+d}  scc={d['largest_scc']:+d}  "
                     f"composite={d['composite']:+.4f}")
        lines.append(f"    Comparison — AGQ: {it['comparison']['agq']:.4f} ({it['comparison']['agq_delta']:+.4f})  "
                     f"SH: {it['comparison']['sh']:.4f} ({it['comparison']['sh_delta']:+.4f})")
        lines.append("")

    # Layer 3: QSE-Diagnostic summary
    lines.append("── Layer 3: QSE-Diagnostic (Problem Identification) ──")
    bl_track = bl["qse_track"]
    problems = []
    if bl_track["PCA"] < 0.8:
        problems.append("PACKAGE_CYCLES")
    if bl_track["dip_violations"] > 0:
        problems.append(f"DIP_VIOLATIONS (n={bl_track['dip_violations']})")
    if bl_track["largest_scc"] > 3:
        problems.append(f"LARGE_SCC (size={bl_track['largest_scc']})")
    if bl_track["M"] < 0.4:
        problems.append("LOW_MODULARITY")

    if problems:
        lines.append(f"  Baseline problems: {', '.join(problems)}")
    else:
        lines.append(f"  Baseline: no structural problems detected")

    # Check which problems were resolved
    if repo_result["iterations"]:
        last = repo_result["iterations"][-1]
        lt = last["qse_track"]
        resolved = []
        remaining = []
        if bl_track["PCA"] < 0.8 and lt["PCA"] >= 0.8:
            resolved.append("PACKAGE_CYCLES")
        elif bl_track["PCA"] < 0.8:
            remaining.append(f"PACKAGE_CYCLES (PCA={lt['PCA']:.4f})")

        if bl_track["dip_violations"] > 0 and lt["dip_violations"] == 0:
            resolved.append("DIP_VIOLATIONS")
        elif lt["dip_violations"] > 0:
            remaining.append(f"DIP_VIOLATIONS (n={lt['dip_violations']})")

        if bl_track["largest_scc"] > 3 and lt["largest_scc"] <= 3:
            resolved.append("LARGE_SCC")
        elif lt["largest_scc"] > 3:
            remaining.append(f"LARGE_SCC (size={lt['largest_scc']})")

        if resolved:
            lines.append(f"  Resolved after {len(repo_result['iterations'])} iterations: {', '.join(resolved)}")
        if remaining:
            lines.append(f"  Still remaining: {', '.join(remaining)}")

    lines.append("")

    # Correlation summary
    corr = repo_result["correlations"]
    if "note" not in corr:
        lines.append("── Correlations: QSE-Track vs blind_score ──")
        for metric, val in corr.items():
            if isinstance(val, dict) and "rho" in val:
                sig = "**" if val["p"] < 0.05 else "ns"
                rho_str = f"{val['rho']:+.4f}" if not math.isnan(val["rho"]) else "NaN"
                p_str = f"{val['p']:.4f}" if not math.isnan(val["p"]) else "NaN"
                lines.append(f"  {metric:25s}: ρ={rho_str}  p={p_str} {sig}")
    else:
        lines.append(f"  Correlations: {corr['note']}")

    lines.append("")
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("E13d: QSE-Track Within-Repo Pilot")
    print(f"Data source: E10b ({E10B['n_repos']} repos)")
    print(f"Date: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    print()

    # Process all repos
    repo_results = []
    for repo_data in E10B["repos"]:
        result = process_repo(repo_data)
        repo_results.append(result)

    # Generate per-repo reports
    print("=" * 70)
    print("THREE-LAYER REPORTS PER REPO")
    print("=" * 70)
    for result in repo_results:
        report = generate_three_layer_report(result)
        print(report)

    # Pooled analysis
    pooled = pooled_analysis(repo_results)
    print("=" * 70)
    print("POOLED ANALYSIS ACROSS ALL REPOS")
    print("=" * 70)
    print(f"  Repos: {pooled['n_repos']}")
    print(f"  Total iterations: {pooled['n_iterations_total']}")
    print()

    print("  Absolute correlations (metric value vs blind_score):")
    for metric, val in pooled["absolute_correlations"].items():
        sig = "**" if val["p"] < 0.05 else "ns"
        rho_str = f"{val['rho']:+.4f}" if not math.isnan(val["rho"]) else "NaN"
        p_str = f"{val['p']:.4f}" if not math.isnan(val["p"]) else "NaN"
        print(f"    {metric:25s}: ρ={rho_str}  p={p_str}  n={val['n']} {sig}")
    print()

    print("  Delta correlations (Δ from baseline vs blind_score):")
    for metric, val in pooled["delta_correlations"].items():
        sig = "**" if val["p"] < 0.05 else "ns"
        rho_str = f"{val['rho']:+.4f}" if not math.isnan(val["rho"]) else "NaN"
        p_str = f"{val['p']:.4f}" if not math.isnan(val["p"]) else "NaN"
        print(f"    {metric:25s}: ρ={rho_str}  p={p_str}  n={val['n']} {sig}")
    print()

    print("  Direction agreement (metric Δ agrees with blind_score ≥ 5):")
    for metric, pct in pooled["direction_agreement_pct"].items():
        print(f"    {metric:25s}: {pct:.1f}%")
    print()

    # ── Comparison summary ──
    print("=" * 70)
    print("COMPARISON: QSE-Track vs AGQ vs SH")
    print("=" * 70)

    abs_c = pooled["absolute_correlations"]
    delta_c = pooled["delta_correlations"]
    dir_a = pooled["direction_agreement_pct"]

    print(f"  {'Metric':25s} {'|abs ρ|':>10s} {'|Δ ρ|':>10s} {'dir%':>8s}")
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*8}")

    def fmt_rho(v):
        return f"{v:+.4f}" if not math.isnan(v) else "  NaN"

    rows = [
        ("QSE-Track composite", abs_c.get("qse_track_composite", {}),
         delta_c.get("delta_composite", {}), dir_a.get("qse_track_composite", 0)),
        ("M (modularity)", abs_c.get("M", {}),
         delta_c.get("delta_M", {}), dir_a.get("M", 0)),
        ("AGQ v3c", abs_c.get("agq", {}),
         delta_c.get("delta_agq", {}), dir_a.get("agq", 0)),
        ("SH (structural health)", abs_c.get("sh", {}),
         delta_c.get("delta_sh", {}), dir_a.get("sh", 0)),
    ]

    for name, abs_val, dlt_val, d_pct in rows:
        ar = fmt_rho(abs_val.get("rho", float("nan")))
        dr = fmt_rho(dlt_val.get("rho", float("nan")))
        print(f"  {name:25s} {ar:>10s} {dr:>10s} {d_pct:>7.1f}%")

    print()

    # ── Save full results ──
    output = {
        "experiment": "E13d_qse_track_pilot",
        "date": datetime.now(timezone.utc).isoformat(),
        "source": "e10b_within_repo_results.json",
        "n_repos": len(repo_results),
        "repos": repo_results,
        "pooled": pooled,
        "method": {
            "qse_track_composite": "0.4*M + 0.3*PCA + 0.2*(1-dip/n_pkg) + 0.1*(1-scc/n_pkg)",
            "comparison_metrics": ["AGQ v3c", "SH (structural health)"],
            "blind_score_source": "architect panel (1-10 scale)",
        },
    }

    # Handle NaN for JSON
    def fix_nan(obj):
        if isinstance(obj, float) and math.isnan(obj):
            return None
        if isinstance(obj, dict):
            return {k: fix_nan(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [fix_nan(v) for v in obj]
        return obj

    output = fix_nan(output)

    out_path = ARTIFACTS / "e13d_qse_track_pilot.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to: {out_path}")

    return output


if __name__ == "__main__":
    main()
