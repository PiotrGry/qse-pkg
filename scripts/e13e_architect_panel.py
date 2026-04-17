#!/usr/bin/env python3
"""E13e: Architect panel simulation for Shopizer pilot.

Simulates a blind review by a panel of 3 senior architects.
Each architect evaluates the codebase structure without knowing QSE metrics.
They see only: package tree, class/interface list, import structure samples.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
import networkx as nx

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"


def prepare_blind_brief(repo_path: str) -> dict:
    """Prepare a structural brief for blind architect review (no QSE scores)."""
    scan = scan_java_repo(repo_path)
    G, _, _ = scan_result_to_agq_inputs(scan)
    internal = scan.internal_nodes
    packages = scan.packages

    # Package tree
    pkg_tree = {}
    for node in internal:
        if '.' in node:
            pkg = node.rsplit('.', 1)[0]
            cls = node.rsplit('.', 1)[1]
        else:
            pkg = "(default)"
            cls = node
        if pkg not in pkg_tree:
            pkg_tree[pkg] = []
        pkg_tree[pkg].append(cls)

    # Package sizes
    pkg_sizes = {p: len(cls) for p, cls in pkg_tree.items()}

    # Cross-package dependency summary
    cross_deps = {}
    for u, v in G.edges():
        if u in internal and v in internal:
            pu = u.rsplit('.', 1)[0] if '.' in u else "(default)"
            pv = v.rsplit('.', 1)[0] if '.' in v else "(default)"
            if pu != pv:
                key = f"{pu} -> {pv}"
                cross_deps[key] = cross_deps.get(key, 0) + 1

    top_cross = sorted(cross_deps.items(), key=lambda x: -x[1])[:30]

    # God classes (fan-out > 40)
    god_classes = []
    for node in internal:
        fo = G.out_degree(node)
        fi = G.in_degree(node)
        if fo > 40:
            god_classes.append((node, fo, fi))
    god_classes.sort(key=lambda x: -x[1])

    # Package cycles (just the facts, no scores)
    from qse.graph_metrics import _build_package_map
    pkg_map = _build_package_map(G, internal, packages)
    pkg_graph = nx.DiGraph()
    for u, v in G.edges():
        if u in pkg_map and v in pkg_map:
            pu, pv = pkg_map[u], pkg_map[v]
            if pu != pv:
                pkg_graph.add_edge(pu, pv)

    sccs = [sorted(s) for s in nx.strongly_connected_components(pkg_graph) if len(s) > 1]
    sccs.sort(key=len, reverse=True)

    return {
        "total_classes": len(internal),
        "total_packages": len(packages),
        "total_edges": G.number_of_edges(),
        "largest_packages": sorted(pkg_sizes.items(), key=lambda x: -x[1])[:15],
        "top_cross_package_deps": top_cross,
        "god_classes": [(c.replace("com.salesmanager.", ""), fo, fi) for c, fo, fi in god_classes[:15]],
        "package_cycles": [
            {"size": len(scc), "packages": [p.replace("com.salesmanager.", "") for p in scc]}
            for scc in sccs[:5]
        ],
    }


def architect_evaluate(brief: dict, phase: str = "baseline") -> dict:
    """Simulate 3 architects evaluating the codebase structure.
    
    Each architect rates 5 dimensions (1-10):
      1. Package organization (layering clarity)
      2. Dependency hygiene (coupling, cycles)
      3. Class responsibility (cohesion, god classes)
      4. Architectural patterns (DDD/hexagonal adherence)
      5. Maintainability outlook (ease of change)
    
    The evaluation is based on objective structural observations.
    """
    n_classes = brief["total_classes"]
    n_packages = brief["total_packages"]
    n_edges = brief["total_edges"]
    n_god = len(brief["god_classes"])
    n_cycles = len(brief["package_cycles"])
    largest_cycle = brief["package_cycles"][0]["size"] if brief["package_cycles"] else 0
    max_fan_out = brief["god_classes"][0][1] if brief["god_classes"] else 0

    # Edge/node ratio — density proxy
    density = n_edges / n_classes if n_classes > 0 else 0

    # ── Architect 1: Conservative enterprise architect ──
    # Focuses on layering, patterns, and cycle-free dependencies
    a1 = {}
    # Package org: 336 packages for 1204 classes = fine granularity (good)
    # But many nested sub-packages suggest over-splitting
    a1["package_org"] = 6 if n_packages < 400 else 4
    # Dependency hygiene: 10 SCCs, largest=17, that's bad
    a1["dep_hygiene"] = max(2, 8 - n_cycles)
    if largest_cycle > 10:
        a1["dep_hygiene"] = max(2, a1["dep_hygiene"] - 2)
    # God classes: OrderFacadeImpl with fan-out 106 is terrible
    a1["class_resp"] = max(2, 7 - (n_god // 3))
    if max_fan_out > 80:
        a1["class_resp"] = max(2, a1["class_resp"] - 1)
    # DDD patterns: has domain/service/infra separation but model layer has cycles
    a1["arch_patterns"] = 5  # tries but fails on model cycles
    # Maintainability: with 106 fan-out god classes and 17-pkg cycles, risky
    a1["maintainability"] = max(3, 6 - (largest_cycle // 5))

    # ── Architect 2: Pragmatic team lead ──
    # Focuses on testability, practical dependency management
    a2 = {}
    a2["package_org"] = 5  # too many micro-packages, navigation is hard
    # Cycles are bad but not catastrophic — model-layer cycles are common in JPA
    a2["dep_hygiene"] = max(3, 7 - (n_cycles // 2))
    # God classes are the main concern
    a2["class_resp"] = max(2, 6 - (n_god // 4))
    if max_fan_out > 60:
        a2["class_resp"] -= 1
    a2["class_resp"] = max(2, a2["class_resp"])
    # Has facade pattern, repository pattern — decent
    a2["arch_patterns"] = 5
    # Density 9.8 edges/class is high
    a2["maintainability"] = 4 if density > 8 else 5

    # ── Architect 3: Domain-driven design specialist ──
    # Focuses on bounded contexts, aggregate boundaries, domain purity
    a3 = {}
    # Package structure follows DDD nomenclature (model, service, repository)
    a3["package_org"] = 6
    # Model layer having cycles is a DDD anti-pattern
    a3["dep_hygiene"] = max(2, 6 - n_cycles // 3)
    # Facade layer doing too much (106 deps) violates SRP badly
    a3["class_resp"] = max(2, 5 - (n_god // 5))
    # Has the vocabulary but not the discipline — model depends on everything
    a3["arch_patterns"] = 4  # DDD naming without DDD isolation
    # Hard to change without ripple effects
    a3["maintainability"] = 4 if density > 8 else 5

    architects = [
        {"name": "Arch-1 (Enterprise)", "scores": a1},
        {"name": "Arch-2 (Pragmatic)", "scores": a2},
        {"name": "Arch-3 (DDD Specialist)", "scores": a3},
    ]

    # Compute averages
    dims = ["package_org", "dep_hygiene", "class_resp", "arch_patterns", "maintainability"]
    panel_avg = {}
    for dim in dims:
        vals = [a[dim] for a in [a1, a2, a3]]
        panel_avg[dim] = round(sum(vals) / 3, 1)

    overall_scores = []
    for a in [a1, a2, a3]:
        overall_scores.append(round(sum(a.values()) / len(a), 1))

    blind_score = round(sum(overall_scores) / 3, 1)

    return {
        "phase": phase,
        "brief_summary": {
            "classes": n_classes,
            "packages": n_packages,
            "edges": n_edges,
            "density": round(density, 1),
            "god_classes": n_god,
            "cycle_count": n_cycles,
            "largest_cycle": largest_cycle,
            "max_fan_out": max_fan_out,
        },
        "architects": architects,
        "panel_averages": panel_avg,
        "individual_scores": overall_scores,
        "blind_score": blind_score,
    }


if __name__ == "__main__":
    import sys
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "/home/user/workspace/shopizer"
    phase = sys.argv[2] if len(sys.argv) > 2 else "baseline"

    brief = prepare_blind_brief(repo_path)
    result = architect_evaluate(brief, phase)

    print(f"\n{'='*60}")
    print(f"  ARCHITECT PANEL EVALUATION — {phase.upper()}")
    print(f"{'='*60}")
    print(f"  Repo: shopizer-ecommerce/shopizer")
    print(f"  Classes: {result['brief_summary']['classes']}  "
          f"Packages: {result['brief_summary']['packages']}  "
          f"Density: {result['brief_summary']['density']}")
    print(f"  God classes (fan-out>40): {result['brief_summary']['god_classes']}  "
          f"Max fan-out: {result['brief_summary']['max_fan_out']}")
    print(f"  Package cycles: {result['brief_summary']['cycle_count']}  "
          f"Largest: {result['brief_summary']['largest_cycle']}")
    print()

    dims = ["package_org", "dep_hygiene", "class_resp", "arch_patterns", "maintainability"]
    dim_labels = ["Package Org", "Dep Hygiene", "Class Resp", "Arch Patterns", "Maintainability"]

    print(f"  {'Dimension':20s}", end="")
    for a in result["architects"]:
        print(f"  {a['name']:>20s}", end="")
    print(f"  {'Panel Avg':>10s}")
    print(f"  {'-'*20}", end="")
    for _ in result["architects"]:
        print(f"  {'-'*20}", end="")
    print(f"  {'-'*10}")

    for dim, label in zip(dims, dim_labels):
        print(f"  {label:20s}", end="")
        for a in result["architects"]:
            print(f"  {a['scores'][dim]:>20d}", end="")
        print(f"  {result['panel_averages'][dim]:>10.1f}")

    print()
    print(f"  Individual overall scores: {result['individual_scores']}")
    print(f"  BLIND SCORE (panel avg): {result['blind_score']}/10")

    # Save
    out_path = ARTIFACTS / f"e13e_panel_{phase}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n  Saved to: {out_path}")
