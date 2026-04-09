#!/usr/bin/env python3
"""Co-change graph entropy as ground truth for AGQ benchmark.

Based on: "Co-Change Graph Entropy: A New Process Metric for Defect Prediction"
arXiv:2504.18511 (2025).

Key finding: Pearson r=0.54 with defect counts across 8 Apache projects (p<0.05).
Outperforms hotspot_ratio as architectural ground truth because it measures
COUPLING BEHAVIOR (files that change together = implicit dependency) rather
than raw frequency (which correlates with project size/maturity).

Architecture connection:
  High co-change entropy between modules = implicit coupling = bad AGQ
  Low co-change entropy = independent modules = good AGQ

Metrics computed per repo:
  system_entropy      - H'(S): overall co-change dispersion
  cross_module_ratio  - fraction of co-changes crossing package boundaries
  mean_cochange_degree - avg files per "co-change community"
  boundary_crossings  - commits where >1 package was touched simultaneously
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Sequence, Tuple


_TEST_RE = re.compile(r"(^|/)tests?/|test_.*\.py$|_test\.py$")
_MAX_FILES_PER_COMMIT = 30  # filter mega-commits (releases, renames)


# ---------------------------------------------------------------------------
# Git utilities
# ---------------------------------------------------------------------------

def _run(cmd: Sequence[str], cwd: Optional[Path] = None) -> str:
    proc = subprocess.run(list(cmd), cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, timeout=180)
    return proc.stdout if proc.returncode == 0 else ""


def _extract_commits(repo_path: Path, since: str) -> List[List[str]]:
    """Return list of commits, each a list of changed .py production files."""
    raw = _run(["git", "-C", str(repo_path), "log", "--since", since,
                "--name-only", "--pretty=format:--COMMIT--"])
    commits = []
    current: List[str] = []
    for line in raw.splitlines():
        if line == "--COMMIT--":
            if current:
                commits.append(current)
            current = []
        elif line.strip().endswith(".py") and not _TEST_RE.search(line.strip()):
            current.append(line.strip())
    if current:
        commits.append(current)
    # Filter mega-commits and single-file commits (no co-change possible)
    return [c for c in commits if 1 < len(c) <= _MAX_FILES_PER_COMMIT]


def _package_of(filepath: str) -> str:
    """First-level directory of a file path."""
    parts = filepath.replace("\\", "/").split("/")
    return parts[0] if len(parts) > 1 else "__root__"


# ---------------------------------------------------------------------------
# Co-change graph entropy
# ---------------------------------------------------------------------------

def compute_cochange_entropy(commits: List[List[str]]) -> Optional[Dict]:
    """
    Build co-change graph and compute entropy metrics.

    Node = file, Edge = file pair that changed in same commit.
    Edge weight = number of co-occurrences.

    system_entropy:      H'(S) = -sum(p'_k * log(p'_k))
                         where p'_k = degree(k) / (2 * |edges|)
    cross_module_ratio:  fraction of commits touching >1 top-level package
    boundary_crossings:  absolute count of cross-package commits
    """
    if not commits:
        return None

    # Build co-change graph: file → set of co-changed files
    cochange: Dict[str, Counter] = defaultdict(Counter)
    cross_pkg_commits = 0

    for files in commits:
        pkgs = {_package_of(f) for f in files}
        if len(pkgs) > 1:
            cross_pkg_commits += 1
        for i, f1 in enumerate(files):
            for f2 in files[i + 1:]:
                cochange[f1][f2] += 1
                cochange[f2][f1] += 1

    if not cochange:
        return None

    # Degree of each node (sum of edge weights)
    degrees = {node: sum(w for w in neighbors.values())
               for node, neighbors in cochange.items()}
    total_degree = sum(degrees.values())  # = 2 * |edges| (weighted)

    if total_degree == 0:
        return None

    # Co-change graph entropy H'(S)
    entropy = 0.0
    for node, deg in degrees.items():
        p = deg / total_degree
        if p > 0:
            entropy -= p * math.log2(p)

    # Normalize entropy by log2(N) - max entropy for N nodes
    n_nodes = len(degrees)
    max_entropy = math.log2(n_nodes) if n_nodes > 1 else 1.0
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

    # Cross-module ratio
    cross_module_ratio = cross_pkg_commits / len(commits)

    # Mean co-change degree (avg number of files that change together)
    mean_cochange_degree = statistics.mean(
        [len(files) for files in commits]) if commits else 0.0

    return {
        "n_commits_analysed": len(commits),
        "n_files_in_graph": n_nodes,
        "system_entropy": round(entropy, 4),
        "normalized_entropy": round(normalized_entropy, 4),
        "cross_module_ratio": round(cross_module_ratio, 4),
        "boundary_crossings": cross_pkg_commits,
        "mean_cochange_degree": round(mean_cochange_degree, 3),
    }


# ---------------------------------------------------------------------------
# Correlation utilities
# ---------------------------------------------------------------------------

def _pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx * dy > 0 else None


def _ranks(vals: Sequence[float]) -> List[float]:
    idx = sorted(enumerate(vals), key=lambda x: x[1])
    r = [0.0] * len(vals)
    i = 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and idx[j + 1][1] == idx[i][1]:
            j += 1
        rv = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            r[idx[k][0]] = rv
        i = j + 1
    return r


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
    t = abs(r) * math.sqrt((n - 2) / (1 - r2))
    df = n - 2
    x = df / (df + t * t)

    def _betai(a: float, b: float, x: float) -> float:
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0
        lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
        fpmin = 1e-30
        c, d = 1.0, 1.0 - (a + b) * x / (a + 1)
        if abs(d) < fpmin:
            d = fpmin
        d = 1.0 / d
        h = d
        for m in range(1, 101):
            m2 = 2 * m
            aa = m * (b - m) * x / ((a - 1 + m2) * (a + m2))
            d = 1.0 + aa * d
            if abs(d) < fpmin:
                d = fpmin
            c = 1.0 + aa / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1.0 / d
            h *= d * c
            aa = -(a + m) * (a + b + m) * x / ((a + m2) * (a + 1 + m2))
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
        return math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) * h / a

    return _betai(0.5 * df, 0.5, x)


def _fmt(v: Optional[float], d: int = 4) -> str:
    return f"{v:.{d}f}" if v is not None else "n/a"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Co-change entropy ground truth for AGQ (arXiv:2504.18511)")
    parser.add_argument("--input-json",
                        default="artifacts/benchmark/agq_thesis_oss80_v3.json")
    parser.add_argument("--repos-dir", default="/tmp/agq_bench80")
    parser.add_argument("--output-json",
                        default="artifacts/benchmark/agq_cochange_entropy.json")
    parser.add_argument("--output-md",
                        default="artifacts/benchmark/agq_cochange_entropy.md")
    parser.add_argument("--since", default="2 years ago")
    args = parser.parse_args()

    input_path = Path(args.input_json)
    if not input_path.exists():
        raise SystemExit(f"Input not found: {args.input_json}")

    benchmark = json.loads(input_path.read_text())
    repos_dir = Path(args.repos_dir)

    print(f"Computing co-change entropy for {len(benchmark['results'])} repos "
          f"(window: {args.since})\n")

    results = []
    for entry in benchmark["results"]:
        name = entry["name"]
        agq = float(entry["agq"]["score_mean"]) if entry.get("agq") else None
        repo_path = repos_dir / name

        print(f"  [{name}] ", end="", flush=True)
        if not repo_path.exists():
            print("MISSING")
            results.append({"name": name, "agq": agq, "entropy": None, "error": "missing"})
            continue

        commits = _extract_commits(repo_path, args.since)
        entropy = compute_cochange_entropy(commits)

        if entropy is None:
            print("no data")
            results.append({"name": name, "agq": agq, "entropy": None, "error": "no_data"})
            continue

        print(f"n_commits={entropy['n_commits_analysed']} "
              f"H={entropy['system_entropy']:.3f} "
              f"cross_pkg={entropy['cross_module_ratio']:.2%}")
        results.append({"name": name, "agq": agq, "entropy": entropy})

    # Correlations - higher AGQ should predict lower cross_module_ratio
    joint = [(r["agq"], r["entropy"])
             for r in results if r["agq"] is not None and r.get("entropy")]
    agq_vals = [a for a, _ in joint]
    ent_data = [e for _, e in joint]
    n = len(joint)

    correlations = {}
    for key in ["normalized_entropy", "cross_module_ratio",
                "mean_cochange_degree", "boundary_crossings"]:
        target = [float(e[key]) for e in ent_data]
        rp = _pearson(agq_vals, target)
        rs = _spearman(agq_vals, target)
        correlations[f"agq_vs_{key}"] = {
            "pearson": round(rp, 4) if rp is not None else None,
            "p_pearson": round(_p_value(rp, n), 4) if rp is not None else None,
            "spearman": round(rs, 4) if rs is not None else None,
            "p_spearman": round(_p_value(rs, n), 4) if rs is not None else None,
            "n": n,
        }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference": "arXiv:2504.18511 - Co-Change Graph Entropy (2025)",
        "config": {"input_json": str(input_path), "since": args.since},
        "summary": {"repos_with_entropy": n, "repos_total": len(benchmark["results"])},
        "correlations": correlations,
        "results": results,
    }

    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2))

    # Markdown
    lines = ["# AGQ Co-Change Entropy Analysis", "",
             f"- generated_at: `{report['generated_at']}`",
             f"- reference: `{report['reference']}`",
             f"- repos_analysed: `{n}`",
             f"- git_window: `{args.since}`",
             "",
             "## Correlations (AGQ vs co-change metrics)",
             "",
             "Negative correlation expected: high AGQ → low entropy / low cross-module coupling.",
             "",
             "| Metric | n | Pearson | p | Spearman | p | Sig |",
             "|---|---:|---:|---:|---:|---:|---|"]
    for key, c in correlations.items():
        sig = "**p<0.05**" if (c["p_spearman"] or 1.0) < 0.05 else ""
        lines.append(f"| {key.replace('agq_vs_','')} | {c['n']} | "
                     f"{_fmt(c['pearson'])} | {_fmt(c['p_pearson'])} | "
                     f"{_fmt(c['spearman'])} | {_fmt(c['p_spearman'])} | {sig} |")
    lines += ["",
              "## Per-Repo Results (sorted by AGQ)",
              "",
              "| Repo | AGQ | Commits | H(norm) | Cross-pkg% | Mean files/commit |",
              "|---|---:|---:|---:|---:|---:|"]
    for r in sorted(results, key=lambda x: x.get("agq") or 0):
        e = r.get("entropy")
        if e is None:
            lines.append(f"| {r['name']} | {_fmt(r.get('agq'))} | n/a | n/a | n/a | n/a |")
        else:
            lines.append(f"| {r['name']} | {_fmt(r.get('agq'))} | "
                         f"{e['n_commits_analysed']} | "
                         f"{_fmt(e['normalized_entropy'])} | "
                         f"{e['cross_module_ratio']:.1%} | "
                         f"{_fmt(e['mean_cochange_degree'], 2)} |")
    lines.append("")
    out_md.write_text("\n".join(lines) + "\n")

    print(f"\n=== Correlations (AGQ vs co-change entropy) ===")
    for key, c in correlations.items():
        sig = " *" if (c["p_spearman"] or 1.0) < 0.05 else ""
        print(f"  {key:<45} r_s={_fmt(c['spearman'])}  p={_fmt(c['p_spearman'])}{sig}")
    print(f"\nJSON: {out_json}\nMD:   {out_md}")


if __name__ == "__main__":
    main()
