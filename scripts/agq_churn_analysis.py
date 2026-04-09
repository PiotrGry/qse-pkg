#!/usr/bin/env python3
"""Code churn analysis as ground truth for AGQ benchmark.

Code churn = how often each .py file is modified in git history.
High-churn files are defect-prone (Nagappan & Ball 2005, Moser et al. 2008).

Metrics per repo:
  mean_churn        - mean commits-per-file (production .py only)
  max_churn         - max commits for any single file (hotspot severity)
  churn_gini        - Gini coefficient of churn distribution
                      (high = few hotspot files carry all changes)
  hotspot_ratio     - fraction of files with churn > 2x mean
  module_churn_cv   - coefficient of variation of per-module churn
                      (high CV = uneven distribution = architectural smell)

Hypothesis: high AGQ -> lower mean_churn, lower hotspot_ratio, lower churn_gini.
Well-modularized code changes in small, isolated units.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


_TEST_RE = re.compile(r"(^|/)tests?/|test_.*\.py$|_test\.py$")


# ---------------------------------------------------------------------------
# Math utilities
# ---------------------------------------------------------------------------

def _gini(values: List[float]) -> float:
    """Gini coefficient of inequality for non-negative values."""
    if not values or sum(values) == 0:
        return 0.0
    n = len(values)
    sorted_v = sorted(values)
    cum = sum((i + 1) * v for i, v in enumerate(sorted_v))
    return (2 * cum) / (n * sum(sorted_v)) - (n + 1) / n


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    den = denx * deny
    return num / den if den > 0 else None


def _ranks(vals: Sequence[float]) -> List[float]:
    indexed = sorted(enumerate(vals), key=lambda x: x[1])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        r = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = r
        i = j + 1
    return ranks


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    return _pearson(_ranks(xs), _ranks(ys))


def _p_value(r: Optional[float], n: int) -> Optional[float]:
    if r is None or n < 3:
        return None
    r2 = r * r
    if r2 >= 1.0:
        return 0.0
    df = n - 2
    t = abs(r) * math.sqrt(df / (1.0 - r2))
    x = df / (df + t * t)

    def _betai(a: float, b: float, x: float) -> float:
        if x <= 0.0:
            return 0.0
        if x >= 1.0:
            return 1.0
        lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
        tiny = 1e-30
        fpmin = tiny
        qab = a + b
        qap = a + 1.0
        qam = a - 1.0
        c, d = 1.0, 1.0 - qab * x / qap
        if abs(d) < fpmin:
            d = fpmin
        d = 1.0 / d
        h = d
        for m in range(1, 101):
            m2 = 2 * m
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = 1.0 + aa * d
            if abs(d) < fpmin:
                d = fpmin
            c = 1.0 + aa / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1.0 / d
            h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = 1.0 + aa * d
            if abs(d) < fpmin:
                d = fpmin
            c = 1.0 + aa / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < 3e-7:
                break
        return math.exp(math.log(x) * a + math.log(1.0 - x) * b - lbeta) * h / a

    return _betai(0.5 * df, 0.5, x)


# ---------------------------------------------------------------------------
# Churn computation
# ---------------------------------------------------------------------------

def compute_churn(repo_path: Path, since: str = "2 years ago") -> Optional[Dict]:
    """Compute churn metrics for production .py files in a repo."""
    proc = subprocess.run(
        ["git", "-C", str(repo_path), "log", "--since", since,
         "--name-only", "--format=", "--", "*.py"],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        return None

    file_counts: Counter = Counter()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.endswith(".py"):
            continue
        if _TEST_RE.search(line):
            continue
        file_counts[line] += 1

    if not file_counts:
        return None

    counts = list(file_counts.values())
    mean_c = statistics.mean(counts)
    hotspot_threshold = mean_c * 2.0
    hotspot_ratio = sum(1 for c in counts if c > hotspot_threshold) / len(counts)

    # Module-level churn: group by top-level directory
    module_sums: Counter = Counter()
    for fpath, cnt in file_counts.items():
        parts = fpath.replace("\\", "/").split("/")
        module = parts[0] if parts else "root"
        module_sums[module] += cnt

    module_counts = list(module_sums.values())
    if len(module_counts) >= 2:
        mc_mean = statistics.mean(module_counts)
        mc_std = statistics.pstdev(module_counts)
        module_churn_cv = mc_std / mc_mean if mc_mean > 0 else 0.0
    else:
        module_churn_cv = 0.0

    return {
        "n_files": len(counts),
        "mean_churn": round(mean_c, 3),
        "median_churn": round(statistics.median(counts), 3),
        "max_churn": max(counts),
        "churn_gini": round(_gini(counts), 4),
        "hotspot_ratio": round(hotspot_ratio, 4),
        "module_churn_cv": round(module_churn_cv, 4),
        "top_hotspots": [f for f, _ in file_counts.most_common(5)],
    }


# ---------------------------------------------------------------------------
# Correlation report
# ---------------------------------------------------------------------------

def _corr_row(label: str, agq: List[float], target: List[float]) -> Dict:
    n = len(agq)
    r_p = _pearson(agq, target)
    r_s = _spearman(agq, target)
    return {
        "pair": label,
        "n": n,
        "pearson": round(r_p, 4) if r_p is not None else None,
        "p_pearson": round(_p_value(r_p, n), 4) if r_p is not None else None,
        "spearman": round(r_s, 4) if r_s is not None else None,
        "p_spearman": round(_p_value(r_s, n), 4) if r_s is not None else None,
    }


def _fmt(v: Optional[float], d: int = 4) -> str:
    return f"{v:.{d}f}" if v is not None else "n/a"


def _to_markdown(report: Dict) -> str:
    lines = ["# AGQ Code Churn Analysis", ""]
    lines += [
        f"- generated_at: `{report['generated_at']}`",
        f"- repos_analysed: `{report['summary']['repos_with_churn']}`",
        f"- git window: `{report['config']['since']}`",
        "",
        "## Hypothesis",
        "",
        "High AGQ → lower mean_churn, lower hotspot_ratio, lower churn_gini.",
        "Well-modularized code changes in small isolated units.",
        "Ref: Nagappan & Ball (2005); Moser et al. (2008).",
        "",
        "## Correlations (AGQ vs churn - negative = AGQ predicts lower churn)",
        "",
        "| Pair | n | Pearson | p | Spearman | p | Sig |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in report["correlations"]:
        sig = "**p<0.05**" if (row["p_spearman"] or 1.0) < 0.05 else ""
        lines.append(
            f"| {row['pair']} | {row['n']} | {_fmt(row['pearson'])} | "
            f"{_fmt(row['p_pearson'])} | {_fmt(row['spearman'])} | "
            f"{_fmt(row['p_spearman'])} | {sig} |"
        )
    lines += [
        "",
        "## Per-Repo Results",
        "",
        "| Repo | AGQ | Files | Mean churn | Max churn | Gini | Hotspot% | ModCV |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(report["results"], key=lambda r: r.get("agq") or 0):
        c = row.get("churn")
        agq_s = _fmt(row.get("agq"))
        if c is None:
            lines.append(f"| {row['name']} | {agq_s} | n/a | n/a | n/a | n/a | n/a | n/a |")
        else:
            lines.append(
                f"| {row['name']} | {agq_s} | {c['n_files']} | "
                f"{_fmt(c['mean_churn'], 2)} | {c['max_churn']} | "
                f"{_fmt(c['churn_gini'])} | {c['hotspot_ratio']:.1%} | "
                f"{_fmt(c['module_churn_cv'])} |"
            )
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="AGQ vs code churn correlation")
    parser.add_argument(
        "--input-json",
        default="artifacts/benchmark/agq_thesis_oss80_v2.json",
        help="AGQ benchmark JSON",
    )
    parser.add_argument("--repos-dir", default="/tmp/agq_bench80")
    parser.add_argument("--output-json", default="artifacts/benchmark/agq_churn_analysis.json")
    parser.add_argument("--output-md", default="artifacts/benchmark/agq_churn_analysis.md")
    parser.add_argument("--since", default="2 years ago")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.exists():
        # fallback to v1
        fallback = Path("artifacts/benchmark/agq_thesis_oss80.json")
        if fallback.exists():
            print(f"[warn] {args.input_json} not found, using {fallback}")
            input_path = fallback
        else:
            raise SystemExit(f"Input JSON not found: {args.input_json}")

    benchmark = json.loads(input_path.read_text())
    repos_dir = Path(args.repos_dir)

    print(f"Analysing {len(benchmark['results'])} repos in {repos_dir} "
          f"(window: {args.since})\n")

    results = []
    for repo_entry in benchmark["results"]:
        name = repo_entry["name"]
        agq_data = repo_entry.get("agq")
        agq_score = float(agq_data["score_mean"]) if agq_data else None

        repo_path = repos_dir / name
        print(f"  [{name}] ", end="", flush=True)

        if not repo_path.exists():
            print("MISSING")
            results.append({"name": name, "agq": agq_score, "churn": None, "error": "missing"})
            continue

        churn = compute_churn(repo_path, since=args.since)
        if churn is None:
            print("no data")
            results.append({"name": name, "agq": agq_score, "churn": None, "error": "no_data"})
            continue

        print(f"files={churn['n_files']} mean={churn['mean_churn']} "
              f"gini={churn['churn_gini']} hotspots={churn['hotspot_ratio']:.1%}")
        results.append({"name": name, "agq": agq_score, "churn": churn})

    joint = [(r["agq"], r["churn"]) for r in results
             if r["agq"] is not None and r.get("churn") is not None]
    agq_vals = [a for a, _ in joint]
    churn_data = [c for _, c in joint]

    # All churn metrics are "lower is better" so we expect negative correlation with AGQ
    correlations = []
    for key in ["mean_churn", "median_churn", "churn_gini",
                "hotspot_ratio", "module_churn_cv", "max_churn"]:
        target = [c[key] for c in churn_data]
        correlations.append(_corr_row(f"agq vs {key}", agq_vals, target))

    summary = {
        "repos_total": len(benchmark["results"]),
        "repos_with_churn": len(joint),
        "repos_missing": sum(1 for r in results if r.get("error") == "missing"),
        "repos_no_data": sum(1 for r in results if r.get("error") == "no_data"),
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "input_json": str(input_path),
            "repos_dir": str(repos_dir),
            "since": args.since,
        },
        "summary": summary,
        "correlations": correlations,
        "results": results,
    }

    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2))
    out_md.write_text(_to_markdown(report))

    print(f"\n=== Summary ===")
    print(f"Repos with churn data: {len(joint)}/{len(benchmark['results'])}")
    print("\nCorrelations (negative = AGQ predicts lower churn = good):")
    for row in correlations:
        sig = " *" if (row["p_spearman"] or 1.0) < 0.05 else ""
        print(f"  agq vs {row['pair'].split('vs ')[-1]:<25} "
              f"r_s={_fmt(row['spearman'])}  p={_fmt(row['p_spearman'])}{sig}")
    print(f"\nJSON: {out_json}\nMD:   {out_md}")


if __name__ == "__main__":
    main()
