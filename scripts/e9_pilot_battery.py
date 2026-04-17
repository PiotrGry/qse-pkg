"""
E9: Pilot Battery — Before/After Refactoring Sensitivity Test
===============================================================

For each pilot repo:
  1. Clone & scan BEFORE (main branch)
  2. Apply minimal, targeted refactoring
  3. Scan AFTER
  4. Compare deltas across all AGQ components

Goal: Which AGQ components detect architectural improvement?
"""

import json
import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
from qse.graph_metrics import compute_agq, compute_stability


def clone_repo(url, dest):
    """Clone a repo, return True on success."""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", url, dest],
        capture_output=True, text=True, timeout=120
    )
    return result.returncode == 0


def scan_repo(repo_path):
    """Scan a repo and return full metrics."""
    scan = scan_java_repo(repo_path)
    inputs = scan_result_to_agq_inputs(scan)
    graph = inputs.get("graph")
    
    if graph is None or graph.number_of_nodes() == 0:
        return None
    
    agq_result = compute_agq(
        graph=graph,
        abstractness=inputs.get("abstractness", 0),
        total_classes=inputs.get("total_classes", 0),
        abstract_classes=inputs.get("abstract_classes", 0),
    )
    
    return {
        "agq": agq_result["agq"],
        "components": agq_result["components"],
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "n_packages": len(set(
            graph.nodes[n].get("package", "") 
            for n in graph.nodes
        )),
    }


def explore_packages(repo_path):
    """List package structure to plan refactoring."""
    scan = scan_java_repo(repo_path)
    inputs = scan_result_to_agq_inputs(scan)
    graph = inputs.get("graph")
    
    if graph is None:
        return {}
    
    # Count classes per package
    pkg_counts = {}
    pkg_deps = {}  # package -> set of packages it depends on
    
    for n in graph.nodes:
        pkg = graph.nodes[n].get("package", "")
        pkg_counts[pkg] = pkg_counts.get(pkg, 0) + 1
    
    for u, v in graph.edges:
        u_pkg = graph.nodes[u].get("package", "")
        v_pkg = graph.nodes[v].get("package", "")
        if u_pkg != v_pkg:
            if u_pkg not in pkg_deps:
                pkg_deps[u_pkg] = set()
            pkg_deps[u_pkg].add(v_pkg)
    
    return {
        "pkg_counts": dict(sorted(pkg_counts.items(), key=lambda x: -x[1])),
        "pkg_deps": {k: sorted(v) for k, v in sorted(pkg_deps.items())},
        "total_packages": len(pkg_counts),
        "total_classes": sum(pkg_counts.values()),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["explore", "scan", "compare"], required=True)
    parser.add_argument("--repo-url", help="Git URL to clone")
    parser.add_argument("--repo-path", help="Local path to scan")
    parser.add_argument("--name", help="Pilot name")
    args = parser.parse_args()
    
    if args.phase == "explore":
        print(f"Exploring package structure: {args.repo_path or args.repo_url}")
        if args.repo_url:
            dest = f"/tmp/pilot_{args.name}"
            if not os.path.exists(dest):
                clone_repo(args.repo_url, dest)
            result = explore_packages(dest)
        else:
            result = explore_packages(args.repo_path)
        print(json.dumps(result, indent=2, default=str))
    
    elif args.phase == "scan":
        print(f"Scanning: {args.repo_path}")
        result = scan_repo(args.repo_path)
        print(json.dumps(result, indent=2, default=str))
    
    elif args.phase == "compare":
        # Load before/after from artifacts
        artifacts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "artifacts"
        )
        results_file = os.path.join(artifacts_dir, "e9_pilot_results.json")
        if os.path.exists(results_file):
            with open(results_file) as f:
                results = json.load(f)
            
            print("=" * 80)
            print("E9 PILOT BATTERY — SUMMARY")
            print("=" * 80)
            
            for pilot in results.get("pilots", []):
                name = pilot["name"]
                before = pilot["before"]
                after = pilot["after"]
                
                print(f"\n--- {name} ({pilot['refactoring_type']}) ---")
                print(f"  Refactoring: {pilot['refactoring_description']}")
                print(f"  {'Component':<12} {'Before':>8} {'After':>8} {'Delta':>8} {'%Change':>8}")
                
                for comp in ["M", "A", "S", "C", "CD"]:
                    b = before["components"][comp]
                    a = after["components"][comp]
                    delta = a - b
                    pct = (delta / b * 100) if b > 0 else float('inf')
                    marker = " <<<" if abs(delta) > 0.01 else ""
                    print(f"  {comp:<12} {b:>8.4f} {a:>8.4f} {delta:>+8.4f} {pct:>+7.1f}%{marker}")
                
                agq_b = before["agq"]
                agq_a = after["agq"]
                print(f"  {'AGQ':<12} {agq_b:>8.4f} {agq_a:>8.4f} {agq_a-agq_b:>+8.4f} {((agq_a-agq_b)/agq_b*100):>+7.1f}%")
