#!/usr/bin/env python3
"""Benchmark extended metrics (CCD, IC, per-module) on all 240 repos.

Usage:
    python3 scripts/extended_metrics_benchmark.py \
        --clone-dir /tmp/emerge-test \
        --output artifacts/benchmark/extended_metrics_benchmark.json
"""
import argparse
import json
import math
import statistics
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return {"r": None, "p": None, "n": n}
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)
    sx = (sum((x - mx) ** 2 for x in xs) / (n - 1)) ** 0.5
    sy = (sum((y - my) ** 2 for y in ys) / (n - 1)) ** 0.5
    r = cov / (sx * sy) if sx > 0 and sy > 0 else 0
    t = r * math.sqrt((n - 2) / (1 - r * r)) if abs(r) < 1 else float("inf")
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return {"r": round(r, 4), "p": round(p, 6), "n": n}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clone-dir", default="/tmp/emerge-test")
    parser.add_argument("--output", default="artifacts/benchmark/extended_metrics_benchmark.json")
    parser.add_argument("--benchmark", default="artifacts/benchmark/agq_enhanced_python80.json")
    parser.add_argument("--max-repos", type=int, default=80)
    args = parser.parse_args()

    clone_dir = Path(args.clone_dir)

    try:
        from qse.extended_metrics import compute_extended_metrics
    except ImportError:
        print("ERROR: qse.extended_metrics not found")
        return

    # Load existing benchmark for AGQ + churn data
    with open(args.benchmark) as f:
        benchmark = json.load(f)
    agq_by_name = {r["name"]: r for r in benchmark["results"]}

    # Get repo list
    with open("scripts/repos_oss80_benchmark.json") as f:
        repos = json.load(f)

    results = []
    t0 = time.time()

    for i, repo in enumerate(repos[:args.max_repos]):
        name = repo["name"]
        path = clone_dir / name
        if not path.is_dir():
            print(f"[{i+1}/{len(repos)}] {name}: SKIP (not cloned)")
            continue

        print(f"[{i+1}/{len(repos)}] {name}...", end=" ", flush=True)
        try:
            ext = compute_extended_metrics(str(path))
            if ext is None:
                print("SKIP (no result)")
                continue
        except Exception as e:
            print(f"ERROR: {e}")
            continue

        agq_data = agq_by_name.get(name, {})
        agq = agq_data.get("agq", {})
        churn = agq_data.get("churn") or {}

        row = {
            "repo": name,
            "agq_score": agq.get("agq_score"),
            "modularity": agq.get("modularity"),
            "acyclicity": agq.get("acyclicity"),
            "stability": agq.get("stability"),
            "cohesion": agq.get("cohesion"),
            "nodes": agq.get("nodes"),
            "ccd": ext["ccd"],
            "indirect_coupling": ext["indirect_coupling"],
            "per_module_summary": ext["per_module"]["summary"],
            "hotspot_ratio": churn.get("hotspot_ratio"),
            "churn_gini": churn.get("churn_gini"),
        }
        results.append(row)

        ccd = ext["ccd"]
        ic = ext["indirect_coupling"]
        pm = ext["per_module"]["summary"]
        print(f"CCD={ccd['ccd_norm']:.3f} IC={ic['mean_ic']:.3f} "
              f"maxFO={pm['max_fan_out']} n={pm['n_modules']}")

    elapsed = time.time() - t0
    print(f"\nDone: {len(results)} repos in {elapsed:.1f}s")

    # Compute correlations
    corr_pairs = [
        ("ccd_norm", "ccd", "ccd_norm"),
        ("mean_ic", "indirect_coupling", "mean_ic"),
        ("max_fan_out", "per_module_summary", "max_fan_out"),
        ("fan_out_std", "per_module_summary", "fan_out_std"),
        ("avg_fan_out", "per_module_summary", "avg_fan_out"),
    ]

    targets = ["hotspot_ratio", "churn_gini", "agq_score"]
    correlations = {}

    for metric_name, dict_key, sub_key in corr_pairs:
        for target in targets:
            pairs = []
            for r in results:
                val = r.get(dict_key, {}).get(sub_key) if isinstance(r.get(dict_key), dict) else r.get(dict_key)
                tgt = r.get(target)
                if val is not None and tgt is not None:
                    pairs.append((val, tgt))
            if len(pairs) >= 3:
                xs, ys = zip(*pairs)
                c = pearson(list(xs), list(ys))
                key = f"{metric_name}_vs_{target}"
                correlations[key] = c

    # Print correlation table
    print(f"\n{'Metric':<20} {'Target':<15} {'r':>7} {'p':>10} {'sig':>5}")
    print("-" * 60)
    for key, c in sorted(correlations.items()):
        parts = key.split("_vs_")
        sig = "**" if c.get("p") and c["p"] < 0.05 else ""
        print(f"{parts[0]:<20} {parts[1]:<15} {c['r']:>+7.3f} {c['p']:>10.6f} {sig:>5}")

    # Save
    output = {
        "generated_at": datetime.now().isoformat(),
        "n_repos": len(results),
        "elapsed_s": round(elapsed, 1),
        "correlations": correlations,
        "results": results,
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
