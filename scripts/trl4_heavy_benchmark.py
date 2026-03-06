#!/usr/bin/env python3
"""Heavy, reproducible benchmark for TRL4 evidence.

Compares optimized checker against:
1) legacy baseline (expected clear speedup),
2) current exp4 baseline (expected near-parity).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List

from optimizations.constraints_benchmark.benchmark import (
    Case,
    median,
    parse_cases,
    resolve_baseline_checker,
    run_case,
)


def _run_suite(cases: List[Case], repeats: int, seed: int, baseline_mode: str) -> Dict[str, object]:
    checker, checker_name = resolve_baseline_checker(baseline_mode)
    results = []
    for idx, case in enumerate(cases):
        run_seed = seed + idx * 101
        row = run_case(case=case, repeats=repeats, seed=run_seed, baseline_checker=checker)
        row["seed"] = run_seed
        results.append(row)
    median_speedup = median([r["speedup_x"] for r in results])
    return {
        "baseline_mode": baseline_mode,
        "baseline_checker": checker_name,
        "repeats": repeats,
        "median_speedup_x": median_speedup,
        "cases": [asdict(c) for c in cases],
        "results": results,
    }


def _to_markdown(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# TRL4 Heavy Benchmark")
    lines.append("")
    lines.append(f"- generated_at: `{report['generated_at']}`")
    lines.append(f"- overall_pass: `{report['overall_pass']}`")
    lines.append("")
    lines.append("## Acceptance thresholds")
    lines.append("")
    lines.append(
        f"- legacy median speedup >= `{report['thresholds']['legacy_min_speedup_x']}`"
    )
    lines.append(
        f"- exp4 parity range: `{report['thresholds']['exp4_min_speedup_x']}.."
        f"{report['thresholds']['exp4_max_speedup_x']}`"
    )
    lines.append("")

    for suite in report["suites"]:
        lines.append(f"## Suite: {suite['baseline_mode']}")
        lines.append("")
        lines.append(f"- baseline_checker: `{suite['baseline_checker']}`")
        lines.append(f"- repeats: `{suite['repeats']}`")
        lines.append(f"- median_speedup_x: `{suite['median_speedup_x']:.4f}`")
        lines.append("")
        lines.append("| Case | Baseline median (s) | Optimized median (s) | Speedup x |")
        lines.append("|---|---:|---:|---:|")
        for row in suite["results"]:
            label = f"{row['nodes']}n:{row['edges']}e:{row['rules']}r"
            lines.append(
                f"| {label} | {row['baseline_median_s']:.6f} | "
                f"{row['optimized_median_s']:.6f} | {row['speedup_x']:.3f} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run heavy benchmark for TRL4 evidence")
    parser.add_argument(
        "--cases",
        default="1000:20000:100,3000:80000:180,3500:100000:220",
        help="Comma-separated benchmark cases: nodes:edges:rules",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--legacy-repeats", type=int, default=6)
    parser.add_argument("--exp4-repeats", type=int, default=8)
    parser.add_argument("--legacy-min-speedup", type=float, default=2.0)
    parser.add_argument("--exp4-min-speedup", type=float, default=0.8)
    parser.add_argument("--exp4-max-speedup", type=float, default=1.2)
    parser.add_argument("--output-json", default="artifacts/trl4/heavy_benchmark.json")
    parser.add_argument("--output-md", default="artifacts/trl4/heavy_benchmark.md")
    args = parser.parse_args()

    cases = parse_cases(args.cases)

    legacy_suite = _run_suite(
        cases=cases,
        repeats=args.legacy_repeats,
        seed=args.seed,
        baseline_mode="legacy",
    )
    exp4_suite = _run_suite(
        cases=cases,
        repeats=args.exp4_repeats,
        seed=args.seed,
        baseline_mode="exp4",
    )

    legacy_pass = legacy_suite["median_speedup_x"] >= args.legacy_min_speedup
    exp4_pass = args.exp4_min_speedup <= exp4_suite["median_speedup_x"] <= args.exp4_max_speedup
    overall_pass = bool(legacy_pass and exp4_pass)

    report: Dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_pass": overall_pass,
        "checks": {
            "legacy_speedup": {
                "passed": legacy_pass,
                "value": legacy_suite["median_speedup_x"],
                "min_required": args.legacy_min_speedup,
            },
            "exp4_parity": {
                "passed": exp4_pass,
                "value": exp4_suite["median_speedup_x"],
                "range": [args.exp4_min_speedup, args.exp4_max_speedup],
            },
        },
        "thresholds": {
            "legacy_min_speedup_x": args.legacy_min_speedup,
            "exp4_min_speedup_x": args.exp4_min_speedup,
            "exp4_max_speedup_x": args.exp4_max_speedup,
        },
        "suites": [legacy_suite, exp4_suite],
    }

    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2))
    output_md.write_text(_to_markdown(report))

    print(f"Heavy benchmark {'PASS' if overall_pass else 'FAIL'}")
    print(f"JSON: {output_json}")
    print(f"MD:   {output_md}")
    raise SystemExit(0 if overall_pass else 1)


if __name__ == "__main__":
    main()
