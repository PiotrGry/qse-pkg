#!/usr/bin/env python3
"""Known-good vs known-bad architectural validation.

Compares AGQ scores between repos with community-recognized good architecture
and repos known to have poor/spaghetti structure. Uses Mann-Whitney U test
to determine if AGQ significantly differentiates the two groups.

Usage:
    python3 scripts/known_good_bad_validation.py
"""
import json
import math
import statistics
import subprocess
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path


# === KNOWN-GOOD REPOS ===
# Selection criteria: widely recognized in Python community for clean architecture.
# Sources: PyCon talks, "Architecture Patterns with Python" (Percival & Gregory),
# "Cosmic Python", conference recommendations, GitHub star count + maintainer reputation.
KNOWN_GOOD = [
    "django",       # 15+ years, layered MTV, 77k stars — gold standard
    "flask",        # Micro-framework, clean extension system
    "fastapi",      # Modern async, clean dependency injection
    "starlette",    # ASGI foundation, minimal, well-layered
    "sqlalchemy",   # Textbook ORM architecture, unit of work pattern
    "pydantic",     # Clean validation layer, well-separated concerns
    "click",        # Composable CLI framework, decorator-based
    "rich",         # Clean rendering pipeline, well-modularized
    "celery",       # Distributed task queue, pluggable backends
    "typer",        # Built on Click, clean type-based API
]

# === KNOWN-BAD REPOS ===
# Selection criteria: repos from spaghetti_oss list + bottom AGQ scorers from
# Python-80 benchmark with documented architectural issues.
# The spaghetti repos are intentionally poorly structured (educational/demo).
KNOWN_BAD_SPAGHETTI = [
    # From repos_spaghetti_oss.json — explicitly spaghetti code
    "python_code_disasters",
    "python_bad_project",
    "python_spaghetti",
    "python_anti_patterns",
    "nickineering_spaghetti",
]


def load_benchmark(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    return {r["name"]: r for r in data["results"]}


def scan_spaghetti_repos() -> dict:
    """Run QSE on spaghetti repos that aren't in the benchmark."""
    spaghetti_path = Path("scripts/repos_spaghetti_oss.json")
    if not spaghetti_path.exists():
        return {}

    with open(spaghetti_path) as f:
        repos = json.load(f)

    results = {}
    clone_dir = Path(tempfile.mkdtemp(prefix="qse_spaghetti_"))

    for repo in repos:
        name = repo["name"]
        url = repo["url"]
        dest = clone_dir / name

        if not dest.exists():
            print(f"  Cloning {name}...")
            ret = subprocess.run(
                ["git", "clone", "--depth", "1", url, str(dest)],
                capture_output=True, timeout=120,
            )
            if ret.returncode != 0:
                print(f"    FAILED to clone {name}")
                continue

        # Run QSE
        try:
            ret = subprocess.run(
                ["python3", "-m", "qse", "agq", str(dest), "--output-json", "/dev/stdout"],
                capture_output=True, text=True, timeout=60,
            )
            if ret.returncode == 0 and ret.stdout.strip():
                data = json.loads(ret.stdout)
                results[name] = {
                    "agq": data,
                    "source": "spaghetti_scan",
                }
                print(f"    {name}: AGQ={data.get('agq_score', 'N/A')}")
        except Exception as e:
            print(f"    {name}: scan failed ({e})")

    return results


def mann_whitney_u(x: list, y: list) -> dict:
    """Mann-Whitney U test (two-tailed). No scipy needed."""
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return {"U": None, "p": None, "z": None, "significant": False}

    # Rank all values
    combined = [(v, "x") for v in x] + [(v, "y") for v in y]
    combined.sort(key=lambda t: t[0])

    # Assign ranks (handle ties)
    ranks = []
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2
        for k in range(i, j):
            ranks.append((combined[k][1], avg_rank))
        i = j

    rank_sum_x = sum(r for group, r in ranks if group == "x")
    U_x = rank_sum_x - nx * (nx + 1) / 2
    U_y = nx * ny - U_x
    U = min(U_x, U_y)

    # Normal approximation for z
    mu = nx * ny / 2
    sigma = math.sqrt(nx * ny * (nx + ny + 1) / 12)
    z = (U - mu) / sigma if sigma > 0 else 0

    # Two-tailed p-value approximation (normal CDF)
    p = 2 * (1 - _norm_cdf(abs(z)))

    return {
        "U": U,
        "z": round(z, 4),
        "p": round(p, 6),
        "significant_005": p < 0.05,
        "significant_001": p < 0.01,
        "n_x": nx,
        "n_y": ny,
    }


def _norm_cdf(x: float) -> float:
    """Approximation of standard normal CDF."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def cohens_d(x: list, y: list) -> float:
    """Effect size: Cohen's d."""
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2:
        return 0.0
    mx, my = statistics.mean(x), statistics.mean(y)
    sx, sy = statistics.stdev(x), statistics.stdev(y)
    pooled = math.sqrt(((nx - 1) * sx**2 + (ny - 1) * sy**2) / (nx + ny - 2))
    return (mx - my) / pooled if pooled > 0 else 0.0


def main():
    benchmark_path = "artifacts/benchmark/agq_enhanced_python80.json"
    benchmark = load_benchmark(benchmark_path)

    # Collect known-good scores from benchmark
    good_scores = []
    good_details = []
    for name in KNOWN_GOOD:
        if name in benchmark:
            r = benchmark[name]
            agq = r["agq"]["agq_score"]
            good_scores.append(agq)
            good_details.append({
                "name": name,
                "agq_score": agq,
                "modularity": r["agq"]["modularity"],
                "acyclicity": r["agq"]["acyclicity"],
                "stability": r["agq"]["stability"],
                "cohesion": r["agq"]["cohesion"],
                "nodes": r["agq"]["nodes"],
                "fingerprint": r.get("enhanced", {}).get("fingerprint"),
                "source": "benchmark",
            })

    # Scan spaghetti repos
    print("=== Scanning spaghetti repos ===")
    spaghetti_results = scan_spaghetti_repos()

    # Also take bottom-10 from benchmark as "known-bad" proxy
    all_sorted = sorted(benchmark.values(), key=lambda r: r["agq"]["agq_score"])
    bottom_10 = all_sorted[:10]

    bad_scores = []
    bad_details = []

    # Spaghetti repos
    for name, data in spaghetti_results.items():
        agq_data = data["agq"]
        score = agq_data.get("agq_score")
        if score is not None:
            bad_scores.append(score)
            bad_details.append({
                "name": name,
                "agq_score": score,
                "modularity": agq_data.get("modularity"),
                "acyclicity": agq_data.get("acyclicity"),
                "stability": agq_data.get("stability"),
                "cohesion": agq_data.get("cohesion"),
                "nodes": agq_data.get("nodes"),
                "fingerprint": agq_data.get("fingerprint"),
                "source": "spaghetti",
            })

    # Bottom-10 from benchmark
    for r in bottom_10:
        name = r["name"]
        if name in KNOWN_GOOD:
            continue  # don't double-count
        agq = r["agq"]["agq_score"]
        bad_scores.append(agq)
        bad_details.append({
            "name": name,
            "agq_score": agq,
            "modularity": r["agq"]["modularity"],
            "acyclicity": r["agq"]["acyclicity"],
            "stability": r["agq"]["stability"],
            "cohesion": r["agq"]["cohesion"],
            "nodes": r["agq"]["nodes"],
            "fingerprint": r.get("enhanced", {}).get("fingerprint"),
            "source": "bottom_10_benchmark",
        })

    # Statistics
    print(f"\n=== Results ===")
    print(f"Known-good: n={len(good_scores)}, mean={statistics.mean(good_scores):.3f}, "
          f"std={statistics.stdev(good_scores):.3f}")
    print(f"Known-bad:  n={len(bad_scores)}, mean={statistics.mean(bad_scores):.3f}, "
          f"std={statistics.stdev(bad_scores):.3f}" if len(bad_scores) > 1 else "")

    mwu = mann_whitney_u(good_scores, bad_scores)
    d = cohens_d(good_scores, bad_scores)

    print(f"\nMann-Whitney U: U={mwu['U']}, z={mwu['z']}, p={mwu['p']}")
    print(f"  Significant at 0.05? {mwu['significant_005']}")
    print(f"  Significant at 0.01? {mwu['significant_001']}")
    print(f"Cohen's d: {d:.3f} ({'large' if abs(d) > 0.8 else 'medium' if abs(d) > 0.5 else 'small'})")

    # Fingerprint distribution
    good_fps = Counter(d["fingerprint"] for d in good_details if d.get("fingerprint"))
    bad_fps = Counter(d["fingerprint"] for d in bad_details if d.get("fingerprint"))

    print(f"\nFingerprints (good): {dict(good_fps)}")
    print(f"Fingerprints (bad):  {dict(bad_fps)}")

    # Table
    print(f"\n{'Group':<10} {'Repo':<28} {'AGQ':>6} {'Mod':>5} {'Acy':>5} {'Stab':>5} {'Coh':>5} {'Fprint':<14}")
    print("-" * 85)
    for d in sorted(good_details, key=lambda x: -x["agq_score"]):
        print(f"{'GOOD':<10} {d['name']:<28} {d['agq_score']:>6.3f} {d['modularity']:>5.2f} {d['acyclicity']:>5.2f} {d['stability']:>5.2f} {d['cohesion']:>5.2f} {d.get('fingerprint', ''):>14}")
    for d in sorted(bad_details, key=lambda x: -x["agq_score"]):
        print(f"{'BAD':<10} {d['name']:<28} {d['agq_score']:>6.3f} {d.get('modularity', 0):>5.2f} {d.get('acyclicity', 0):>5.2f} {d.get('stability', 0):>5.2f} {d.get('cohesion', 0):>5.2f} {d.get('fingerprint', ''):>14}")

    # Save
    output = {
        "generated_at": datetime.now().isoformat(),
        "methodology": {
            "known_good_selection": "Community reputation: widely recognized for clean architecture in Python community (PyCon talks, books, maintainer reputation)",
            "known_bad_selection": "Spaghetti repos (intentionally poor) + bottom-10 AGQ from Python-80 benchmark",
            "statistical_test": "Mann-Whitney U (non-parametric, two-tailed)",
            "effect_size": "Cohen's d",
        },
        "known_good": {"repos": good_details, "n": len(good_scores), "mean_agq": round(statistics.mean(good_scores), 4), "std_agq": round(statistics.stdev(good_scores), 4)},
        "known_bad": {"repos": bad_details, "n": len(bad_scores), "mean_agq": round(statistics.mean(bad_scores), 4) if bad_scores else None, "std_agq": round(statistics.stdev(bad_scores), 4) if len(bad_scores) > 1 else None},
        "mann_whitney_u": mwu,
        "cohens_d": round(d, 4) if isinstance(d, (int, float)) else d,
        "fingerprint_distribution": {"good": dict(good_fps), "bad": dict(bad_fps)},
    }

    out_json = Path("artifacts/benchmark/known_good_bad_validation.json")
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_json}")


if __name__ == "__main__":
    main()
