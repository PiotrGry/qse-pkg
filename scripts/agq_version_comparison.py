#!/usr/bin/env python3
"""Compare AGQ benchmark results across metric versions (v1, v2, v3, ...).

Generates a table showing how AGQ scores, thesis results, and correlations
evolved through metric fix iterations. Useful for thesis 'Experimental Results'
section to demonstrate the effect of each fix.

Usage:
    python3 scripts/agq_version_comparison.py \
        --jsons artifacts/benchmark/agq_thesis_oss80.json \
                artifacts/benchmark/agq_thesis_oss80_v2.json \
                artifacts/benchmark/agq_thesis_oss80_v3.json \
        --labels v1 v2 v3 \
        --output-md artifacts/benchmark/agq_version_comparison.md
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


def _fmt(v: Optional[float], d: int = 4) -> str:
    return f"{v:.{d}f}" if v is not None else "n/a"


def _load(path: str) -> Dict:
    return json.loads(Path(path).read_text())


def _agq_stats(data: Dict) -> Dict:
    vals = [float(r["agq"]["score_mean"])
            for r in data["results"] if "agq" in r and "error" not in r]
    if not vals:
        return {}
    return {
        "n": len(vals),
        "min": min(vals),
        "max": max(vals),
        "mean": statistics.mean(vals),
        "std": statistics.pstdev(vals),
        "spread": max(vals) - min(vals),
    }


def _component_stats(data: Dict) -> Dict:
    out = {}
    for key in ["modularity", "acyclicity", "stability", "cohesion"]:
        vals = [float(r["agq"]["run1"].get(key, 0))
                for r in data["results"] if "agq" in r and "error" not in r
                and r["agq"].get("run1")]
        if vals:
            out[key] = {"mean": statistics.mean(vals), "std": statistics.pstdev(vals)}
    return out


def _thesis_row(data: Dict) -> Dict:
    row = {}
    for t in data.get("theses", []):
        row[t["id"]] = "PASS" if t["passed"] else "FAIL"
    return row


def _corr(data: Dict) -> Dict:
    c = data.get("correlations", {})
    return {
        "agq_bugfix": c.get("pearson_agq_vs_bugfix_ratio"),
        "sonar_bugfix": c.get("pearson_sonar_vs_bugfix_ratio"),
        "agq_hotspot": c.get("spearman_agq_vs_hotspot_ratio"),
        "sonar_hotspot": c.get("spearman_sonar_vs_hotspot_ratio"),
        "agq_gini": c.get("spearman_agq_vs_churn_gini"),
    }


def _per_repo_delta(datasets: List[Dict], labels: List[str]) -> List[Dict]:
    """Build per-repo score table across versions."""
    # Use first dataset as reference repo list
    repos = {r["name"] for r in datasets[0]["results"] if "agq" in r and "error" not in r}
    rows = []
    for name in sorted(repos):
        row = {"name": name}
        for label, data in zip(labels, datasets):
            entry = next((r for r in data["results"] if r["name"] == name), None)
            if entry and "agq" in entry and "error" not in entry:
                row[label] = float(entry["agq"]["score_mean"])
            else:
                row[label] = None
        # Compute delta last-vs-first
        first = row.get(labels[0])
        last = row.get(labels[-1])
        row["delta"] = (last - first) if first is not None and last is not None else None
        rows.append(row)
    return rows


def _to_markdown(datasets: List[Dict], labels: List[str]) -> str:
    lines = ["# AGQ Metric Version Comparison", ""]
    lines += [
        f"- generated_at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- versions: {', '.join(f'`{l}`' for l in labels)}",
        "",
    ]

    # --- AGQ distribution per version ---
    lines += ["## AGQ Score Distribution", ""]
    lines += ["| Version | n | Min | Max | Mean | Std | Spread |"]
    lines += ["|---|---:|---:|---:|---:|---:|---:|"]
    for label, data in zip(labels, datasets):
        s = _agq_stats(data)
        if s:
            lines.append(
                f"| {label} | {s['n']} | {_fmt(s['min'])} | {_fmt(s['max'])} | "
                f"{_fmt(s['mean'])} | {_fmt(s['std'])} | {_fmt(s['spread'])} |"
            )
    lines.append("")

    # --- Component means per version ---
    lines += ["## AGQ Component Means", ""]
    lines += ["| Version | Modularity | Acyclicity | Stability | Cohesion |"]
    lines += ["|---|---:|---:|---:|---:|"]
    for label, data in zip(labels, datasets):
        c = _component_stats(data)
        lines.append(
            f"| {label} | "
            f"{_fmt(c.get('modularity', {}).get('mean'))} | "
            f"{_fmt(c.get('acyclicity', {}).get('mean'))} | "
            f"{_fmt(c.get('stability', {}).get('mean'))} | "
            f"{_fmt(c.get('cohesion', {}).get('mean'))} |"
        )
    lines.append("")

    # --- Thesis results per version ---
    lines += ["## Thesis Results", ""]
    thesis_ids = sorted({tid for data in datasets for t in data.get("theses", [])
                         for tid in [t["id"]]})
    lines += ["| Version | " + " | ".join(thesis_ids) + " | Total |"]
    lines += ["|---|" + "|".join(["---:"] * len(thesis_ids)) + "|---:|"]
    for label, data in zip(labels, datasets):
        row = _thesis_row(data)
        results = [row.get(tid, "n/a") for tid in thesis_ids]
        total = sum(1 for v in results if v == "PASS")
        lines.append(
            f"| {label} | " + " | ".join(results) + f" | {total}/{len(thesis_ids)} |"
        )
    lines.append("")

    # --- Correlations per version ---
    lines += ["## Correlations", ""]
    lines += ["| Version | r(AGQ,bugfix) | r(Sonar,bugfix) | r_s(AGQ,hotspot) | r_s(Sonar,hotspot) | r_s(AGQ,gini) |"]
    lines += ["|---|---:|---:|---:|---:|---:|"]
    for label, data in zip(labels, datasets):
        c = _corr(data)
        lines.append(
            f"| {label} | {_fmt(c['agq_bugfix'])} | {_fmt(c['sonar_bugfix'])} | "
            f"{_fmt(c['agq_hotspot'])} | {_fmt(c['sonar_hotspot'])} | {_fmt(c['agq_gini'])} |"
        )
    lines.append("")

    # --- Per-repo delta table (first vs last version) ---
    if len(datasets) >= 2:
        lines += [f"## Per-Repo AGQ: {labels[0]} → {labels[-1]}", ""]
        col_header = " | ".join(labels)
        lines += [f"| Repo | {col_header} | Δ({labels[-1]}-{labels[0]}) |"]
        lines += ["|---|" + "|".join(["---:"] * len(labels)) + "|---:|"]
        per_repo = _per_repo_delta(datasets, labels)
        per_repo.sort(key=lambda r: r.get("delta") or 0, reverse=True)
        for row in per_repo:
            vals = " | ".join(_fmt(row.get(l)) for l in labels)
            delta_s = f"{row['delta']:+.4f}" if row["delta"] is not None else "n/a"
            lines.append(f"| {row['name']} | {vals} | {delta_s} |")
        lines.append("")

    # --- What changed between versions ---
    lines += ["## Fix Summary", ""]
    fixes = [
        ("v1", "Baseline: stability=Martin's D (A=0 everywhere=mean(I)), "
                "acyclicity=sum_cyclic/total, modularity=(Q+0.5)/1.5, coupling=density"),
        ("v2", "stability→instability_variance (per-node), "
                "acyclicity→largest_SCC/total, modularity→max(0,Q)/0.75 + n<10=0.5, "
                "coupling→mean_out_degree/threshold"),
        ("v3", "stability→package-level instability_variance (collapses leaf-module inflation), "
                "acyclicity→internal-nodes-only (filters stdlib/third-party), "
                "T2→churn hotspot_ratio, T3→dynamic threshold mean-0.5*std"),
    ]
    for version, desc in fixes:
        if version in labels:
            lines.append(f"- **{version}**: {desc}")
    lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare AGQ benchmark versions")
    parser.add_argument("--jsons", nargs="+", required=True,
                        help="Benchmark JSON files in version order")
    parser.add_argument("--labels", nargs="+", required=True,
                        help="Version labels (same count as --jsons)")
    parser.add_argument("--output-md",
                        default="artifacts/benchmark/agq_version_comparison.md")
    args = parser.parse_args()

    if len(args.jsons) != len(args.labels):
        raise SystemExit("--jsons and --labels must have the same count")

    datasets = []
    for path in args.jsons:
        p = Path(path)
        if not p.exists():
            print(f"[warn] {path} not found — skipping")
            continue
        datasets.append(_load(path))

    if len(datasets) < 2:
        raise SystemExit("Need at least 2 JSON files for comparison")

    # Trim labels to match loaded datasets
    labels = args.labels[:len(datasets)]

    md = _to_markdown(datasets, labels)
    out = Path(args.output_md)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    print(f"Comparison written to {out}")

    # Print summary to stdout
    print("\n=== AGQ mean per version ===")
    for label, data in zip(labels, datasets):
        s = _agq_stats(data)
        if s:
            print(f"  {label}: mean={_fmt(s['mean'])}  spread={_fmt(s['spread'])}")

    print("\n=== Thesis results ===")
    for label, data in zip(labels, datasets):
        row = _thesis_row(data)
        total = sum(1 for v in row.values() if v == "PASS")
        print(f"  {label}: {total}/{len(row)} — {row}")


if __name__ == "__main__":
    main()
