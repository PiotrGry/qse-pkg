#!/usr/bin/env python3
"""Compare QSE AGQ modularity with Emerge Louvain modularity.

Usage:
    # 1. Install Emerge: pip install emerge-viz
    # 2. Clone repos to a directory
    # 3. Run:
    python3 scripts/compare_emerge.py --repos-dir /tmp/emerge-test \
        --benchmark artifacts/benchmark/agq_enhanced_python80.json \
        --repos httpx,scrapy,requests,nox,scikit-learn
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


# Map repo name -> subdirectory containing main Python source
SOURCE_DIR_MAP = {
    "scikit-learn": "sklearn",
    "home-assistant": "homeassistant",
}


def find_source_dir(repo_dir: Path, repo_name: str) -> Path | None:
    """Find the main Python source directory in a cloned repo."""
    mapped = SOURCE_DIR_MAP.get(repo_name, repo_name)
    # Try mapped name, then src/<name>, then repo root
    candidates = [
        repo_dir / mapped,
        repo_dir / "src" / mapped,
        repo_dir / "src" / repo_name,
        repo_dir,
    ]
    for c in candidates:
        if c.is_dir() and any(c.glob("*.py")):
            return c
    return None


def run_emerge(repo_name: str, source_dir: Path, output_dir: Path) -> dict | None:
    """Run Emerge on a repo and return parsed metrics."""
    output_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "project_name": repo_name,
        "loglevel": "error",
        "analyses": [{
            "analysis_name": f"{repo_name}_analysis",
            "source_directory": str(source_dir),
            "only_permit_languages": ["py"],
            "only_permit_file_extensions": [".py"],
            "file_scan": [
                "number_of_methods",
                "source_lines_of_code",
                "dependency_graph",
                "fan_in_out",
                "louvain_modularity",
            ],
            "export": [
                {"directory": str(output_dir)},
                "json",
            ],
        }],
    }
    config_path = output_dir / "config.yaml"
    import yaml
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    result = subprocess.run(
        ["emerge", "-c", str(config_path)],
        capture_output=True, text=True, timeout=300,
    )
    metrics_path = output_dir / "emerge-statistics-and-metrics.json"
    if not metrics_path.exists():
        print(f"  WARN: Emerge failed for {repo_name}: {result.stderr[:200]}")
        return None
    with open(metrics_path) as f:
        return json.load(f)


def load_qse_benchmark(path: str) -> dict:
    """Load QSE benchmark and index by repo name."""
    with open(path) as f:
        data = json.load(f)
    return {r["name"]: r for r in data["results"]}


def pearson_r(xs: list, ys: list) -> float:
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    sx = (sum((x - mx) ** 2 for x in xs) / n) ** 0.5
    sy = (sum((y - my) ** 2 for y in ys) / n) ** 0.5
    return cov / (sx * sy) if sx > 0 and sy > 0 else 0.0


def main():
    parser = argparse.ArgumentParser(description="Compare QSE vs Emerge modularity")
    parser.add_argument("--repos-dir", required=True, help="Directory with cloned repos")
    parser.add_argument("--benchmark", required=True, help="QSE benchmark JSON")
    parser.add_argument("--repos", required=True, help="Comma-separated repo names")
    parser.add_argument("--output", default=None, help="Save comparison JSON")
    args = parser.parse_args()

    repos_dir = Path(args.repos_dir)
    repo_names = [r.strip() for r in args.repos.split(",")]
    qse_by_name = load_qse_benchmark(args.benchmark)

    results = []
    emerge_qs, qse_qs = [], []

    header = f"{'Repo':<20} {'Em Q':>6} {'QSE Q':>6} {'Diff':>6} {'Em files':>8} {'QSE nodes':>9} {'Em fan-out':>10} {'AGQ':>6}"
    print(header)
    print("-" * len(header))

    for name in repo_names:
        repo_path = repos_dir / name
        if not repo_path.is_dir():
            print(f"{name:<20} SKIPPED — not found at {repo_path}")
            continue

        src = find_source_dir(repo_path, name)
        if not src:
            print(f"{name:<20} SKIPPED — no Python source found")
            continue

        out = repos_dir / f"{name}_output"
        em = run_emerge(name, src, out)
        if not em:
            print(f"{name:<20} FAILED")
            continue

        om = em["overall-metrics"]
        em_q = om.get("louvain-modularity-dependency-graph", 0)
        em_files = em["statistics"].get("scanned_files", 0)
        em_fan_out = om.get("avg-fan-out-dependency-graph", 0)

        qse = qse_by_name.get(name, {})
        qse_q_norm = qse.get("agq", {}).get("modularity", None)
        qse_q_raw = qse_q_norm * 0.75 if qse_q_norm is not None else None
        qse_nodes = qse.get("agq", {}).get("nodes", None)
        agq = qse.get("agq", {}).get("agq_score", None)

        diff = (qse_q_raw - em_q) if qse_q_raw is not None else None

        row = {
            "repo": name,
            "emerge_q": em_q,
            "qse_q_raw": qse_q_raw,
            "qse_q_normalized": qse_q_norm,
            "diff": diff,
            "emerge_files": em_files,
            "qse_nodes": qse_nodes,
            "emerge_avg_fan_out": em_fan_out,
            "emerge_max_fan_out": om.get("max-fan-out-dependency-graph"),
            "emerge_communities": om.get("louvain-communities-dependency-graph"),
            "agq_score": agq,
        }
        results.append(row)

        if qse_q_raw is not None:
            emerge_qs.append(em_q)
            qse_qs.append(qse_q_raw)

        print(
            f"{name:<20} {em_q:>6.3f} "
            f"{qse_q_raw:>6.3f} " if qse_q_raw else f"{'N/A':>6} "
            f"{diff:>+6.3f} " if diff else f"{'N/A':>6} "
            f"{em_files:>8} "
            f"{qse_nodes:>9} " if qse_nodes else f"{'N/A':>9} "
            f"{em_fan_out:>10.2f} "
            f"{agq:>6.3f}" if agq else f"{'N/A':>6}"
        )

    print()
    if len(emerge_qs) >= 3:
        r = pearson_r(emerge_qs, qse_qs)
        mean_diff = sum(q - e for e, q in zip(emerge_qs, qse_qs)) / len(emerge_qs)
        print(f"Pearson r (Emerge Q vs QSE Q raw): {r:.3f}  (n={len(emerge_qs)})")
        print(f"Mean diff (QSE - Emerge): {mean_diff:+.3f}")
        print()
        print("Interpretation:")
        if r > 0.8:
            print("  Strong correlation — both tools see similar modularity structure.")
        elif r > 0.5:
            print("  Moderate correlation — similar trends, but graph construction differs.")
        else:
            print("  Weak correlation — fundamentally different graph definitions.")
        if mean_diff > 0.05:
            print(f"  QSE consistently higher by ~{mean_diff:.2f} — likely includes more nodes (transitive imports).")

    if args.output:
        out = {
            "comparison": results,
            "pearson_r": pearson_r(emerge_qs, qse_qs) if len(emerge_qs) >= 3 else None,
            "n": len(emerge_qs),
        }
        with open(args.output, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
