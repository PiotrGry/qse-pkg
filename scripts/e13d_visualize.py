#!/usr/bin/env python3
"""E13d visualizations: QSE-Track vs blind_score per repo."""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

with open(ARTIFACTS / "e13d_qse_track_pilot.json") as f:
    data = json.load(f)

# ── Figure 1: Per-repo QSE-Track composite vs blind_score ──────────

fig, axes = plt.subplots(2, 3, figsize=(16, 10))
fig.suptitle("E13d: QSE-Track Within-Repo Pilot — QSE-Track vs Architect Panel", fontsize=14, fontweight="bold")

repos = data["repos"]
for idx, repo in enumerate(repos):
    row, col = divmod(idx, 3)
    ax = axes[row][col]

    # Collect data
    iters = [0] + [it["id"] for it in repo["iterations"]]
    composites = [repo["baseline"]["qse_track_composite"]] + [it["qse_track_composite"] for it in repo["iterations"]]
    blind_scores = [None] + [it["blind_score"] for it in repo["iterations"]]
    agq_vals = [repo["baseline"]["agq"]] + [it["comparison"]["agq"] for it in repo["iterations"]]
    sh_vals = [repo["baseline"]["sh"]] + [it["comparison"]["sh"] for it in repo["iterations"]]

    # Plot QSE-Track composite
    ax.plot(iters, composites, "b-o", label="QSE-Track", linewidth=2, markersize=6, zorder=3)
    ax.plot(iters, agq_vals, "g--s", label="AGQ", linewidth=1.5, markersize=5, alpha=0.7)
    ax.plot(iters, sh_vals, "r-.^", label="SH", linewidth=1.5, markersize=5, alpha=0.7)

    # Plot blind_score on secondary axis
    ax2 = ax.twinx()
    blind_clean = [b for b in blind_scores if b is not None]
    iter_clean = [i for i, b in zip(iters, blind_scores) if b is not None]
    ax2.bar(iter_clean, blind_clean, alpha=0.2, color="orange", width=0.3, label="blind_score")
    ax2.set_ylabel("blind_score", color="orange", fontsize=9)
    ax2.set_ylim(0, 10)
    ax2.tick_params(axis="y", labelcolor="orange")

    ax.set_title(repo["repo"], fontsize=11, fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Metric score")
    ax.set_xticks(iters)
    ax.legend(fontsize=7, loc="upper left")

# Remove empty subplot
axes[1][2].axis("off")

# Add pooled summary in last cell
ax_summary = axes[1][2]
ax_summary.axis("off")
pooled = data["pooled"]
abs_c = pooled["absolute_correlations"]
summary_text = "POOLED CORRELATIONS (n=19)\n\n"
summary_text += "Absolute (value vs blind):\n"
for metric, val in abs_c.items():
    rho = val["rho"] if val["rho"] is not None else float("nan")
    p = val["p"] if val["p"] is not None else float("nan")
    sig = "**" if p < 0.05 else "ns"
    summary_text += f"  {metric}: ρ={rho:+.3f} {sig}\n"

summary_text += "\nDirection agreement:\n"
for metric, pct in pooled["direction_agreement_pct"].items():
    summary_text += f"  {metric}: {pct:.0f}%\n"

ax_summary.text(0.1, 0.9, summary_text, transform=ax_summary.transAxes,
                fontsize=9, verticalalignment="top", fontfamily="monospace",
                bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))

plt.tight_layout()
fig.savefig(str(ARTIFACTS / "e13d_qse_track_pilot.png"), dpi=150, bbox_inches="tight")
print(f"Saved: {ARTIFACTS / 'e13d_qse_track_pilot.png'}")


# ── Figure 2: Comparison bar chart ──────────────────────────────────

fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
fig2.suptitle("E13d: Metric Comparison for Within-Repo Monitoring", fontsize=13, fontweight="bold")

# Absolute correlation
metrics = ["QSE-Track\ncomposite", "M\n(modularity)", "AGQ v3c", "SH"]
abs_rhos = [
    abs_c["qse_track_composite"]["rho"] or 0,
    abs_c["M"]["rho"] or 0,
    abs_c["agq"]["rho"] or 0,
    abs_c["sh"]["rho"] or 0,
]
abs_ps = [
    abs_c["qse_track_composite"]["p"] or 1,
    abs_c["M"]["p"] or 1,
    abs_c["agq"]["p"] or 1,
    abs_c["sh"]["p"] or 1,
]
colors = ["#2196F3" if p < 0.05 else "#90CAF9" for p in abs_ps]
bars1 = ax1.bar(metrics, abs_rhos, color=colors, edgecolor="black", linewidth=0.5)
ax1.set_ylabel("Spearman ρ")
ax1.set_title("Absolute Correlation with blind_score")
ax1.axhline(y=0, color="black", linewidth=0.5)
for bar, p in zip(bars1, abs_ps):
    if p < 0.05:
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, "**",
                 ha="center", fontsize=12, fontweight="bold")

# Direction agreement
dir_pcts = pooled["direction_agreement_pct"]
dir_vals = [dir_pcts["qse_track_composite"], dir_pcts["M"], dir_pcts["agq"], dir_pcts["sh"]]
colors2 = ["#4CAF50" if v >= 60 else "#FFC107" if v >= 50 else "#F44336" for v in dir_vals]
bars2 = ax2.bar(metrics, dir_vals, color=colors2, edgecolor="black", linewidth=0.5)
ax2.set_ylabel("Agreement %")
ax2.set_title("Direction Agreement (Δ matches blind_score ≥ 5)")
ax2.axhline(y=50, color="gray", linewidth=0.5, linestyle="--", label="chance")
ax2.set_ylim(0, 100)
ax2.legend()

plt.tight_layout()
fig2.savefig(str(ARTIFACTS / "e13d_comparison.png"), dpi=150, bbox_inches="tight")
print(f"Saved: {ARTIFACTS / 'e13d_comparison.png'}")
