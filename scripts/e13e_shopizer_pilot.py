#!/usr/bin/env python3
"""E13e: QSE-Track pilot on Shopizer — full scan/fix/measure cycle.

Scans shopizer-ecommerce/shopizer with QSE three-layer framework,
performs aggressive refactoring, rescans, and compares.
"""

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add qse-pkg to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
from qse.graph_metrics import (
    compute_agq,
    compute_qse_rank,
    compute_qse_track,
    compute_qse_diagnostic,
    compute_structural_health,
    compute_package_acyclicity,
    compute_layer_violation_ratio,
    _compute_largest_pkg_scc,
    _count_dip_violations,
    GT_BENCHMARK_C,
    GT_BENCHMARK_S,
)

import networkx as nx


ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"


def full_scan(repo_path: str, label: str = "scan") -> dict:
    """Run complete QSE three-layer scan on a Java repo."""
    print(f"\n{'='*60}")
    print(f"  Scanning: {repo_path}")
    print(f"  Label: {label}")
    print(f"{'='*60}")

    # Step 1: Java scan
    scan = scan_java_repo(repo_path)
    G, abstract_modules, classes_lcom4 = scan_result_to_agq_inputs(scan)

    internal = scan.internal_nodes
    packages = scan.packages

    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    n_internal = len(internal) if internal else n_nodes
    n_packages = len(packages) if packages else 0

    print(f"  Graph: {n_nodes} nodes, {n_edges} edges")
    print(f"  Internal: {n_internal} classes, {n_packages} packages")

    # Step 2: AGQ metrics
    agq = compute_agq(
        G,
        abstract_modules=abstract_modules,
        classes_lcom4=classes_lcom4,
    )

    # Step 3: QSE-Rank
    qse_rank = compute_qse_rank(agq, GT_BENCHMARK_C, GT_BENCHMARK_S)

    # Step 4: QSE-Track
    track = compute_qse_track(G, internal, packages)

    # Step 5: QSE-Diagnostic
    diag = compute_qse_diagnostic(G, agq, GT_BENCHMARK_C, GT_BENCHMARK_S, internal, packages)

    # Step 6: Structural Health
    sh = compute_structural_health(G, internal, packages)

    # Compile results
    result = {
        "label": label,
        "repo_path": repo_path,
        "graph": {"nodes": n_nodes, "edges": n_edges, "internal": n_internal, "packages": n_packages},
        "agq": {
            "M": round(agq.modularity, 4),
            "A": round(agq.acyclicity, 4),
            "S": round(agq.stability, 4),
            "C": round(agq.cohesion, 4),
            "CD": round(agq.coupling_density, 4),
            "agq_v3c": round(agq.agq_score, 4),
        },
        "qse_rank": round(qse_rank, 4),
        "qse_track": track,
        "qse_diagnostic": diag,
        "structural_health": sh,
    }

    # Print summary
    print(f"\n  === QSE Three-Layer Results ===")
    print(f"  Layer 1 — QSE-Rank:  {qse_rank:.4f} / 3.0")
    print(f"  Layer 2 — QSE-Track: M={track['M']:.4f}  PCA={track['PCA']:.4f}  "
          f"dip={track['dip_violations']}  scc={track['largest_scc']}")
    print(f"  Layer 3 — Diagnostic:")
    print(f"    C={diag['C']:.4f} (p{diag['C_percentile']:.0%})  "
          f"S={diag['S']:.4f} (p{diag['S_percentile']:.0%})")
    print(f"    M={diag['M']:.4f}  A={diag['A']:.4f}  CD={diag['CD']:.4f}")
    print(f"    PCA={diag['PCA']:.4f}  LVR={diag['LVR']:.4f}")
    print(f"    Problems: {diag['problems']}")
    print(f"  SH combined: {sh['combined']:.4f}")
    print(f"  AGQ v3c:     {result['agq']['agq_v3c']:.4f}")

    return result


def compute_deltas(before: dict, after: dict) -> dict:
    """Compute deltas between two scan results."""
    deltas = {}

    # QSE-Track deltas
    for key in ["M", "PCA"]:
        deltas[f"track_{key}"] = round(after["qse_track"][key] - before["qse_track"][key], 4)
    deltas["track_dip"] = after["qse_track"]["dip_violations"] - before["qse_track"]["dip_violations"]
    deltas["track_scc"] = after["qse_track"]["largest_scc"] - before["qse_track"]["largest_scc"]

    # AGQ deltas
    for key in ["M", "A", "S", "C", "CD", "agq_v3c"]:
        deltas[f"agq_{key}"] = round(after["agq"][key] - before["agq"][key], 4)

    # QSE-Rank delta
    deltas["qse_rank"] = round(after["qse_rank"] - before["qse_rank"], 4)

    # SH delta
    deltas["sh_combined"] = round(
        after["structural_health"]["combined"] - before["structural_health"]["combined"], 4
    )

    return deltas


if __name__ == "__main__":
    repo_path = str(Path("/home/user/workspace/shopizer"))

    # Baseline scan
    baseline = full_scan(repo_path, "baseline")

    # Save baseline
    output = {
        "experiment": "E13e_shopizer_pilot",
        "date": datetime.now(timezone.utc).isoformat(),
        "repo": "shopizer-ecommerce/shopizer",
        "baseline": baseline,
        "iterations": [],
    }

    out_path = ARTIFACTS / "e13e_shopizer_pilot.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nBaseline saved to: {out_path}")
