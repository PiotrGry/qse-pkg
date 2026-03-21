#!/usr/bin/env python3
"""SonarQube cross-validation: AGQ vs Sonar metrics.

Scans Python repos from the benchmark through SonarQube and correlates
Sonar metrics with AGQ scores. Validates that AGQ measures a different
dimension (architecture) than SonarQube (code smells, complexity).

Prerequisites:
    - SonarQube running: docker compose up -d sonarqube
    - sonar-scanner installed or available via PATH
    - QSE benchmark data in artifacts/benchmark/agq_enhanced_python80.json

Usage:
    python3 scripts/sonar_cross_validation.py
    python3 scripts/sonar_cross_validation.py --max-repos 20
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Reuse SonarClient from existing script
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from agq_oss_thesis_benchmark import SonarClient


SONAR_URL = os.environ.get("SONAR_URL", "http://127.0.0.1:9000")
SONAR_USER = os.environ.get("SONAR_USER", "admin")
SONAR_PASS = os.environ.get("SONAR_PASS", "admin")
CLONE_DIR = Path(os.environ.get("QSE_CLONE_DIR", "/tmp/qse-benchmark-repos/python"))


def find_sonar_scanner() -> Optional[str]:
    """Find sonar-scanner binary."""
    for name in ["sonar-scanner", "sonar-scanner-cli"]:
        ret = subprocess.run(["which", name], capture_output=True)
        if ret.returncode == 0:
            return ret.stdout.decode().strip()
    return None


def run_sonar_scan(client: SonarClient, repo_name: str, repo_path: Path) -> Optional[Dict]:
    """Run SonarQube scan on a repo and return measures."""
    project_key = f"qse-bench-{repo_name}"

    # Create project in Sonar
    try:
        client.create_project(project_key, repo_name)
    except Exception as e:
        print(f"    Failed to create project: {e}")
        return None

    # Write sonar-project.properties
    props_file = repo_path / "sonar-project.properties"
    props_content = f"""sonar.projectKey={project_key}
sonar.projectName={repo_name}
sonar.sources=.
sonar.language=py
sonar.python.version=3.10
sonar.host.url={SONAR_URL}
sonar.login={SONAR_USER}
sonar.password={SONAR_PASS}
sonar.exclusions=**/test*/**,**/tests/**,**/*test*.py,**/docs/**,**/examples/**
sonar.scm.disabled=true
"""
    props_file.write_text(props_content)

    # Run sonar-scanner
    scanner = find_sonar_scanner()
    if not scanner:
        # Try running via docker
        ret = subprocess.run(
            ["docker", "run", "--rm", "--network=host",
             "-v", f"{repo_path}:/usr/src",
             "-w", "/usr/src",
             "sonarsource/sonar-scanner-cli:latest"],
            capture_output=True, text=True, timeout=300,
        )
    else:
        ret = subprocess.run(
            [scanner],
            cwd=str(repo_path),
            capture_output=True, text=True, timeout=300,
        )

    # Clean up props file
    if props_file.exists():
        props_file.unlink()

    if ret.returncode != 0:
        # Check if it's a minor error but analysis was submitted
        if "EXECUTION SUCCESS" not in (ret.stdout or ""):
            print(f"    Scanner failed: {ret.stderr[:200] if ret.stderr else 'no output'}")
            return None

    # Wait for Sonar to process
    time.sleep(5)

    # Get measures
    try:
        measures = client.get_measures(project_key)
        if not measures:
            print(f"    No measures returned")
            return None
        return measures
    except Exception as e:
        print(f"    Failed to get measures: {e}")
        return None


def pearson_with_p(xs: list, ys: list) -> dict:
    """Pearson correlation with t-test."""
    n = len(xs)
    if n < 3:
        return {"r": None, "t": None, "p": None, "n": n}
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)
    sx = (sum((x - mx) ** 2 for x in xs) / (n - 1)) ** 0.5
    sy = (sum((y - my) ** 2 for y in ys) / (n - 1)) ** 0.5
    r = cov / (sx * sy) if sx > 0 and sy > 0 else 0
    t = r * math.sqrt((n - 2) / (1 - r * r)) if abs(r) < 1 else float("inf")
    df = n - 2
    # Approximate p-value
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return {"r": round(r, 4), "t": round(t, 3), "p": round(p, 6), "n": n, "df": df}


def main():
    parser = argparse.ArgumentParser(description="SonarQube cross-validation")
    parser.add_argument("--max-repos", type=int, default=40, help="Max repos to scan")
    parser.add_argument("--benchmark", default="artifacts/benchmark/agq_enhanced_python80.json")
    parser.add_argument("--clone-dir", default=str(CLONE_DIR))
    args = parser.parse_args()

    clone_dir = Path(args.clone_dir)

    # Load AGQ benchmark
    with open(args.benchmark) as f:
        benchmark = json.load(f)
    agq_by_name = {r["name"]: r for r in benchmark["results"]}

    # Connect to Sonar
    client = SonarClient(SONAR_URL, SONAR_USER, SONAR_PASS)
    print("Checking SonarQube...")
    client.ensure_up(timeout_s=60)
    print("SonarQube is UP")

    # Check for sonar-scanner
    scanner = find_sonar_scanner()
    if scanner:
        print(f"sonar-scanner: {scanner}")
    else:
        print("sonar-scanner not found — will try Docker image")

    # Scan repos
    results = []
    repos_to_scan = []

    # Prefer repos that are already cloned
    with open(ROOT / "scripts" / "repos_oss80_benchmark.json") as f:
        repo_list = json.load(f)

    for repo in repo_list:
        name = repo["name"]
        repo_path = clone_dir / name
        if repo_path.is_dir() and name in agq_by_name:
            repos_to_scan.append((name, repo_path))
        if len(repos_to_scan) >= args.max_repos:
            break

    # Clone missing ones if needed
    if len(repos_to_scan) < min(args.max_repos, len(repo_list)):
        for repo in repo_list:
            if len(repos_to_scan) >= args.max_repos:
                break
            name = repo["name"]
            if any(n == name for n, _ in repos_to_scan):
                continue
            repo_path = clone_dir / name
            if not repo_path.is_dir():
                print(f"  Cloning {name}...")
                ret = subprocess.run(
                    ["git", "clone", "--depth", "1", repo["url"], str(repo_path)],
                    capture_output=True, timeout=120,
                )
                if ret.returncode != 0:
                    continue
            if name in agq_by_name:
                repos_to_scan.append((name, repo_path))

    print(f"\nScanning {len(repos_to_scan)} repos through SonarQube...\n")

    for i, (name, repo_path) in enumerate(repos_to_scan):
        print(f"[{i + 1}/{len(repos_to_scan)}] {name}...")
        measures = run_sonar_scan(client, name, repo_path)
        if not measures:
            continue

        agq_data = agq_by_name[name]
        agq = agq_data["agq"]
        churn = agq_data.get("churn") or {}

        row = {
            "repo": name,
            "sonar": measures,
            "agq_score": agq["agq_score"],
            "modularity": agq["modularity"],
            "acyclicity": agq["acyclicity"],
            "stability": agq["stability"],
            "cohesion": agq["cohesion"],
            "nodes": agq["nodes"],
            "fingerprint": agq_data.get("enhanced", {}).get("fingerprint"),
            "hotspot_ratio": churn.get("hotspot_ratio"),
        }
        results.append(row)
        print(f"    Sonar: smells={measures.get('code_smells', 'N/A')}, "
              f"complexity={measures.get('complexity', 'N/A')}, "
              f"AGQ={agq['agq_score']:.3f}")

    if len(results) < 3:
        print(f"\nOnly {len(results)} repos scanned — too few for correlations.")
        print("Check that sonar-scanner is installed and repos are cloned.")
        sys.exit(1)

    # Correlations
    sonar_metrics = ["code_smells", "bugs", "vulnerabilities", "complexity",
                     "cognitive_complexity", "duplicated_lines_density",
                     "sqale_rating", "ncloc"]
    agq_metrics = ["agq_score", "modularity", "acyclicity", "stability", "cohesion"]

    correlations = {}
    for sm in sonar_metrics:
        for am in agq_metrics:
            pairs = [(r[am], r["sonar"].get(sm))
                     for r in results
                     if r.get(am) is not None and r["sonar"].get(sm) is not None]
            if len(pairs) >= 3:
                xs, ys = zip(*pairs)
                corr = pearson_with_p(list(xs), list(ys))
                key = f"{am}_vs_sonar_{sm}"
                correlations[key] = corr

    # Print results
    print(f"\n{'=' * 60}")
    print(f"SONAR CROSS-VALIDATION RESULTS (n={len(results)})")
    print(f"{'=' * 60}\n")

    sig_count = 0
    print(f"{'AGQ metric':<15} {'Sonar metric':<25} {'r':>7} {'p':>10} {'sig?':>5}")
    print("-" * 65)
    for key, corr in sorted(correlations.items()):
        parts = key.split("_vs_sonar_")
        am, sm = parts[0], parts[1]
        sig = "**" if corr["p"] is not None and corr["p"] < 0.05 else ""
        if sig:
            sig_count += 1
        print(f"{am:<15} {sm:<25} {corr['r']:>+7.3f} {corr['p']:>10.4f} {sig:>5}")

    total = len(correlations)
    print(f"\nSignificant (p<0.05): {sig_count}/{total}")
    if sig_count / total < 0.15 if total > 0 else True:
        print("INTERPRETATION: AGQ and SonarQube measure orthogonal dimensions.")
        print("  SonarQube: code-level smells, complexity, duplication")
        print("  AGQ: architectural structure — modularity, cycles, stability, cohesion")

    # Save
    output = {
        "generated_at": datetime.now().isoformat(),
        "sonar_version": "9.9.8 (LTS Community)",
        "n_repos": len(results),
        "n_scanned": len(repos_to_scan),
        "correlations": correlations,
        "significant_count": sig_count,
        "total_correlations": total,
        "interpretation": "orthogonal_dimensions" if (total > 0 and sig_count / total < 0.15) else "some_overlap",
        "results": results,
    }

    out_path = Path("artifacts/benchmark/sonar_vs_agq_validation.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
