#!/usr/bin/env python3
"""
AGQ Mutation Study - sensitivity analysis of AGQ to controlled architectural degradations.

Usage:
    python3 scripts/mutation_study_agq.py --repos-dir /tmp/mutation_repos --n-repos 30
    python3 scripts/mutation_study_agq.py --repos-dir /tmp/mutation_repos --n-repos 5 --quick
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.mutations import MUTATIONS


def clone_repos(repo_lists: list, n_per_lang: int, repos_dir: str) -> list:
    """Clone stratified sample of repos."""
    os.makedirs(repos_dir, exist_ok=True)
    selected = []

    for lang, list_file in repo_lists:
        with open(list_file) as f:
            repos = json.load(f)
        sample = repos[:n_per_lang]
        for repo in sample:
            name = repo["name"]
            url = repo["url"]
            commit = repo.get("commit")
            dest = os.path.join(repos_dir, name)
            if os.path.isdir(dest):
                selected.append({"name": name, "path": dest, "language": lang})
                continue
            print(f"  Cloning {name} ({lang})...", end=" ", flush=True)
            r = subprocess.run(
                ["git", "clone", "--depth", "1", url, dest],
                capture_output=True, timeout=120
            )
            if r.returncode == 0:
                if commit:
                    subprocess.run(
                        ["git", "-C", dest, "fetch", "--depth", "1", "origin", commit],
                        capture_output=True, timeout=60
                    )
                    subprocess.run(
                        ["git", "-C", dest, "checkout", commit],
                        capture_output=True, timeout=30
                    )
                selected.append({"name": name, "path": dest, "language": lang})
                print("OK")
            else:
                print("FAILED")
    return selected


def scan_agq(repo_path: str) -> dict:
    """Scan repo and return AGQ metrics."""
    try:
        from _qse_core import scan_and_compute_agq
        result = scan_and_compute_agq(repo_path)
        return {
            "modularity": result["modularity"],
            "acyclicity": result["acyclicity"],
            "stability": result["stability"],
            "cohesion": result["cohesion"],
            "agq_score": result["agq_score"],
            "nodes": result.get("nodes", 0),
        }
    except Exception as e:
        return {"error": str(e)}


def git_reset(repo_path: str):
    """Reset repo to clean state."""
    subprocess.run(
        ["git", "-C", repo_path, "checkout", "--", "."],
        capture_output=True, timeout=30
    )
    subprocess.run(
        ["git", "-C", repo_path, "clean", "-fd"],
        capture_output=True, timeout=30
    )


def run_study(repos: list, doses: list, seeds: list, output_dir: str):
    """Run full mutation study."""
    os.makedirs(output_dir, exist_ok=True)
    results = []
    total = len(repos) * len(MUTATIONS) * len(doses) * len(seeds)
    done = 0

    for repo in repos:
        name = repo["name"]
        path = repo["path"]
        lang = repo["language"]

        # Baseline
        git_reset(path)
        # Clear file cache between repos
        from scripts.mutations import _FILE_CACHE
        _FILE_CACHE.clear()

        baseline = scan_agq(path)
        if "error" in baseline:
            print(f"  SKIP {name}: {baseline['error']}")
            continue
        if baseline.get("nodes", 0) < 10:
            print(f"  SKIP {name}: too few nodes ({baseline.get('nodes', 0)})")
            continue

        print(f"\n{name} ({lang}) - baseline AGQ={baseline['agq_score']:.3f} "
              f"[M={baseline['modularity']:.3f} A={baseline['acyclicity']:.3f} "
              f"St={baseline['stability']:.3f} Co={baseline['cohesion']:.3f}]")

        for mut_name, mut_fn in MUTATIONS.items():
            for dose in doses:
                for seed in seeds:
                    git_reset(path)
                    _FILE_CACHE.clear()
                    try:
                        meta = mut_fn(path, dose, seed)
                        if meta.get("mutations", 0) == 0:
                            # No mutations applied (repo too small etc)
                            result_agq = baseline.copy()
                        else:
                            result_agq = scan_agq(path)
                            if "error" in result_agq:
                                result_agq = baseline.copy()
                                result_agq["scan_error"] = True
                    except Exception as e:
                        result_agq = baseline.copy()
                        meta = {"type": mut_name, "dose": dose, "mutations": 0,
                                "error": str(e)}

                    results.append({
                        "repo": name,
                        "language": lang,
                        "mutation": mut_name,
                        "dose": dose,
                        "seed": seed,
                        "mutations_applied": meta.get("mutations", 0),
                        "baseline": baseline,
                        **{f"mutated_{k}": v for k, v in result_agq.items()
                           if k != "error" and k != "nodes"},
                        "delta_agq": result_agq.get("agq_score", 0) - baseline["agq_score"],
                    })
                    done += 1

            # Progress
            pct = done / total * 100
            print(f"  {mut_name}: {done}/{total} ({pct:.0f}%)", end="\r", flush=True)

        git_reset(path)

    # Save raw results
    raw_path = os.path.join(output_dir, "raw_results.json")
    with open(raw_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n\nSaved {len(results)} results to {raw_path}")
    return results


def analyze(results: list, output_dir: str):
    """Compute statistics and write summary."""
    from scipy import stats as sp

    lines = []
    lines.append("=" * 72)
    lines.append("AGQ MUTATION STUDY - RESULTS SUMMARY")
    lines.append("=" * 72)
    lines.append(f"\nTotal runs: {len(results)}")
    lines.append(f"Repos: {len(set(r['repo'] for r in results))}")
    lines.append(f"Languages: {sorted(set(r['language'] for r in results))}")

    # Per mutation type
    lines.append("\n--- MONOTONICITY (Spearman ρ: dose vs mutated_agq_score) ---")
    lines.append(f"  {'Mutation':<30} {'ρ':>8} {'p-value':>12} {'Pass':>6}")
    lines.append("  " + "-" * 58)

    for mut_name in MUTATIONS:
        subset = [r for r in results if r["mutation"] == mut_name
                  and r["mutations_applied"] > 0]
        if len(subset) < 5:
            lines.append(f"  {mut_name:<30} {'N/A':>8} {'N/A':>12} {'SKIP':>6}")
            continue
        doses = [r["dose"] for r in subset]
        scores = [r["mutated_agq_score"] for r in subset]
        rho, p = sp.spearmanr(doses, scores)
        passed = "YES" if rho < -0.3 and p < 0.05 else "NO"
        lines.append(f"  {mut_name:<30} {rho:>8.4f} {p:>12.2e} {passed:>6}")

    # Per mutation vs target component
    component_map = {
        "cycle_injection": "acyclicity",
        "layer_violation": "stability",
        "hub_creation": "modularity",
        "cohesion_degradation": "cohesion",
    }

    lines.append("\n--- TARGET COMPONENT SENSITIVITY ---")
    lines.append(f"  {'Mutation':<30} {'Component':<15} {'ρ':>8} {'p-value':>12}")
    lines.append("  " + "-" * 67)

    for mut_name, comp in component_map.items():
        subset = [r for r in results if r["mutation"] == mut_name
                  and r["mutations_applied"] > 0]
        if len(subset) < 5:
            lines.append(f"  {mut_name:<30} {comp:<15} {'N/A':>8} {'N/A':>12}")
            continue
        doses = [r["dose"] for r in subset]
        comp_scores = [r[f"mutated_{comp}"] for r in subset]
        rho, p = sp.spearmanr(doses, comp_scores)
        lines.append(f"  {mut_name:<30} {comp:<15} {rho:>8.4f} {p:>12.2e}")

    # Effect sizes (baseline vs dose=max)
    max_dose = max(r["dose"] for r in results)
    lines.append(f"\n--- EFFECT SIZES (Cohen's d: baseline vs dose={max_dose}) ---")
    for mut_name in MUTATIONS:
        baselines = [r["baseline"]["agq_score"] for r in results
                     if r["mutation"] == mut_name and r["dose"] == min(
                         d for d in set(r2["dose"] for r2 in results) if d > 0)]
        mutated = [r["mutated_agq_score"] for r in results
                   if r["mutation"] == mut_name and r["dose"] == max_dose
                   and r["mutations_applied"] > 0]
        if baselines and mutated:
            import statistics
            m1, m2 = statistics.mean(baselines), statistics.mean(mutated)
            s1, s2 = statistics.stdev(baselines) if len(baselines) > 1 else 0.01, \
                     statistics.stdev(mutated) if len(mutated) > 1 else 0.01
            pooled_s = ((s1**2 + s2**2) / 2) ** 0.5
            d = (m1 - m2) / pooled_s if pooled_s > 0 else 0
            lines.append(f"  {mut_name:<30} d={d:.2f} (mean {m1:.4f} → {m2:.4f})")

    # Combined monotonicity
    lines.append("\n--- COMBINED MONOTONICITY ---")
    all_with_mutations = [r for r in results if r["mutations_applied"] > 0]
    if len(all_with_mutations) >= 10:
        doses = [r["dose"] for r in all_with_mutations]
        scores = [r["mutated_agq_score"] for r in all_with_mutations]
        rho, p = sp.spearmanr(doses, scores)
        lines.append(f"  Combined ρ(dose, AGQ) = {rho:.4f}, p = {p:.2e}")
    else:
        lines.append("  Insufficient data for combined analysis")

    # Summary
    lines.append("\n--- THRESHOLD CHECKS ---")
    for mut_name in MUTATIONS:
        subset = [r for r in results if r["mutation"] == mut_name
                  and r["mutations_applied"] > 0]
        if len(subset) < 5:
            lines.append(f"  {mut_name}: SKIP (insufficient data)")
            continue
        rho, p = sp.spearmanr([r["dose"] for r in subset],
                              [r["mutated_agq_score"] for r in subset])
        status = "PASS" if rho < -0.3 and p < 0.05 else "FAIL"
        lines.append(f"  {mut_name}: ρ={rho:.4f}, p={p:.2e} → {status}")

    lines.append("\n" + "=" * 72)

    summary = "\n".join(lines)
    summary_path = os.path.join(output_dir, "summary.txt")
    with open(summary_path, "w") as f:
        f.write(summary)
    print(summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description="AGQ Mutation Study")
    parser.add_argument("--repos-dir", default="/tmp/mutation_repos",
                        help="Directory to clone repos into")
    parser.add_argument("--n-repos", type=int, default=10,
                        help="Repos per language (default: 10)")
    parser.add_argument("--output", default="results/mutation_study_agq",
                        help="Output directory")
    parser.add_argument("--quick", action="store_true",
                        help="Quick mode: 3 repos/lang, 3 doses, 2 seeds")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent

    # Use stratified list if available, otherwise fall back to per-language lists
    stratified_file = scripts_dir / "repos_mutation_study.json"
    if stratified_file.exists() and not args.quick:
        with open(stratified_file) as f:
            repo_entries = json.load(f)
        repo_lists = None  # signal to use stratified
    else:
        repo_lists = [
            ("Python", str(scripts_dir / "repos_oss80_benchmark.json")),
            ("Java", str(scripts_dir / "repos_java80_benchmark.json")),
            ("Go", str(scripts_dir / "repos_go80_benchmark.json")),
        ]

    if args.quick:
        n_per_lang = min(3, args.n_repos)
        doses = [0.1, 0.3, 0.5]
        seeds = list(range(2))
    else:
        n_per_lang = args.n_repos
        doses = [0.1, 0.2, 0.3, 0.5]
        seeds = list(range(5))

    print(f"=== AGQ Mutation Study ===")
    if repo_lists:
        print(f"Repos: {n_per_lang}/language, Doses: {doses}, Seeds: {len(seeds)}")
        expected = n_per_lang * 3 * len(MUTATIONS) * len(doses) * len(seeds)
    else:
        print(f"Repos: {len(repo_entries)} (stratified L/M/S), Doses: {doses}, Seeds: {len(seeds)}")
        expected = len(repo_entries) * len(MUTATIONS) * len(doses) * len(seeds)
    print(f"Expected runs: {expected}")
    print()

    print("1. Cloning repos...")
    if repo_lists:
        repos = clone_repos(repo_lists, n_per_lang, args.repos_dir)
    else:
        # Clone from stratified list
        os.makedirs(args.repos_dir, exist_ok=True)
        repos = []
        for entry in repo_entries:
            name = entry["name"]
            dest = os.path.join(args.repos_dir, name)
            if not os.path.isdir(dest):
                print(f"  Cloning {name} ({entry['language']}, {entry.get('bucket','?')})...", end=" ", flush=True)
                r = subprocess.run(
                    ["git", "clone", "--depth", "1", entry["url"], dest],
                    capture_output=True, timeout=180
                )
                if r.returncode != 0:
                    print("FAILED")
                    continue
                print("OK")
            repos.append({"name": name, "path": dest, "language": entry["language"]})
    print(f"   Cloned {len(repos)} repos\n")

    print("2. Running mutations...")
    t0 = time.time()
    results = run_study(repos, doses, seeds, args.output)
    elapsed = time.time() - t0
    print(f"\n   Completed in {elapsed:.0f}s\n")

    print("3. Analyzing...")
    analyze(results, args.output)


if __name__ == "__main__":
    main()
