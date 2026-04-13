"""
Multi-Repo Re-Run with Archipelago Detector — Item 6
=====================================================

Re-run the 15 pilot repos with the archipelago detector enabled.
Also run on a sample of GT repos to validate detector behavior.

Goals:
1. Confirm detector catches the 5 BAD repos (collections/tutorials)
2. Verify 0 false positives on GOOD repos
3. Compute updated accuracy excluding detected archipelagos
4. Test GFS (Graph Flow Score) prototype on scanned repos
"""

import json
import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone

import networkx as nx
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qse.graph_metrics import compute_agq, compute_stability
from qse.archtest import _detect_archipelago, run_java_scan


# Repos from pilot multi-repo scan
PILOT_REPOS = [
    # Expected GOOD (frameworks, well-architected)
    {"name": "eventuate-tram-core", "url": "https://github.com/eventuate-tram/eventuate-tram-core", "expected": "GOOD"},
    {"name": "dropwizard", "url": "https://github.com/dropwizard/dropwizard", "expected": "GOOD"},
    {"name": "logbook", "url": "https://github.com/zalando/logbook", "expected": "GOOD"},
    {"name": "axon-framework", "url": "https://github.com/AxonFramework/AxonFramework", "expected": "GOOD"},
    {"name": "apollo", "url": "https://github.com/apolloconfig/apollo", "expected": "GOOD"},
    
    # Expected MIXED
    {"name": "mybatis-3", "url": "https://github.com/mybatis/mybatis-3", "expected": "MIXED"},
    {"name": "redisson", "url": "https://github.com/redisson/redisson", "expected": "MIXED"},
    {"name": "shardingsphere", "url": "https://github.com/apache/shardingsphere", "expected": "MIXED"},
    {"name": "dubbo", "url": "https://github.com/apache/dubbo", "expected": "MIXED"},
    {"name": "seata", "url": "https://github.com/apache/seata", "expected": "MIXED"},
    
    # Expected BAD (collections, tutorials)
    {"name": "java-design-patterns", "url": "https://github.com/iluwatar/java-design-patterns", "expected": "BAD"},
    {"name": "TheAlgorithms-Java", "url": "https://github.com/TheAlgorithms/Java", "expected": "BAD"},
    {"name": "JCSprout", "url": "https://github.com/crossoverJie/JCSprout", "expected": "BAD"},
    {"name": "spring-boot-demo", "url": "https://github.com/xkcoding/spring-boot-demo", "expected": "BAD"},
    {"name": "spring-boot-learning", "url": "https://github.com/forezp/SpringBootLearning", "expected": "BAD"},
]


def compute_gfs(graph):
    """
    Graph Flow Score (GFS) — fraction of edges following correct 
    dependency direction (outer→inner).
    
    Uses topological layers on the SCC-condensed DAG.
    Nodes in the same SCC get the same layer.
    Edge from layer L1 to layer L2: correct if L1 >= L2 (outer depends on inner).
    
    GFS = n_correct / n_total
    GFS=1.0 → perfect layered architecture
    GFS=0.5 → random
    GFS<0.5 → inverted
    """
    if graph.number_of_edges() == 0:
        return {"gfs": 0.5, "n_correct": 0, "n_total": 0, "n_layers": 0}
    
    # Condense SCCs
    condensed = nx.condensation(graph)
    
    # Compute topological layers on DAG
    # Layer 0 = roots (no incoming edges), higher = deeper
    layers_dag = {}
    for node in nx.topological_sort(condensed):
        preds = list(condensed.predecessors(node))
        if not preds:
            layers_dag[node] = 0
        else:
            layers_dag[node] = max(layers_dag[p] for p in preds) + 1
    
    # Map original nodes to layers via their SCC
    node_to_scc = {}
    for scc_id, data in condensed.nodes(data=True):
        for member in data.get("members", [scc_id]):
            node_to_scc[member] = scc_id
    
    node_layer = {}
    for node in graph.nodes():
        scc = node_to_scc.get(node, 0)
        node_layer[node] = layers_dag.get(scc, 0)
    
    n_layers = max(layers_dag.values()) + 1 if layers_dag else 0
    
    # Count correct direction edges
    n_correct = 0
    n_total = 0
    for u, v in graph.edges():
        lu = node_layer.get(u, 0)
        lv = node_layer.get(v, 0)
        n_total += 1
        # Correct: dependency goes from higher layer (outer) to lower (inner)
        # or same layer (lateral)
        if lu >= lv:
            n_correct += 1
    
    gfs = n_correct / n_total if n_total > 0 else 0.5
    
    return {
        "gfs": round(gfs, 4),
        "n_correct": n_correct,
        "n_total": n_total,
        "n_layers": n_layers,
    }


def compute_pkg_centrality_variance(graph):
    """
    Package Centrality Variance (PCV) — alternative to S.
    
    Well-layered systems have high variance in package betweenness 
    centrality (few hub packages, many leaf packages).
    Monoliths have low variance (everything equally connected).
    """
    nodes = list(graph.nodes())
    if len(nodes) < 5:
        return {"pcv": 0.5, "mean_bc": 0, "std_bc": 0}
    
    # Group by second-level package
    packages = {}
    for node in nodes:
        parts = node.split(".")
        pkg = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
        packages.setdefault(pkg, []).append(node)
    
    if len(packages) < 3:
        return {"pcv": 0.5, "mean_bc": 0, "std_bc": 0}
    
    # Compute betweenness centrality (sample for large graphs)
    if len(nodes) > 1000:
        bc = nx.betweenness_centrality(graph, k=min(200, len(nodes)))
    else:
        bc = nx.betweenness_centrality(graph)
    
    # Aggregate by package
    pkg_bc = {}
    for pkg, members in packages.items():
        pkg_bc[pkg] = np.mean([bc.get(m, 0) for m in members])
    
    bc_values = list(pkg_bc.values())
    mean_bc = np.mean(bc_values)
    std_bc = np.std(bc_values)
    
    # Normalize: CV (coefficient of variation) 
    cv = std_bc / mean_bc if mean_bc > 0 else 0
    # Scale to [0, 1]: CV > 2.0 → 1.0
    pcv = min(1.0, cv / 2.0)
    
    return {
        "pcv": round(pcv, 4),
        "mean_bc": round(mean_bc, 6),
        "std_bc": round(std_bc, 6),
    }


def clone_and_scan(repo_info, work_dir):
    """Clone a repo and run Java scan."""
    name = repo_info["name"]
    url = repo_info["url"]
    repo_dir = os.path.join(work_dir, name)
    
    print(f"  Cloning {name}...", end=" ", flush=True)
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, repo_dir],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"FAILED: {result.stderr[:200]}")
            return None
        print("OK", end=" ", flush=True)
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        return None
    
    print(f"  Scanning...", end=" ", flush=True)
    try:
        scan = run_java_scan(repo_dir)
        print(f"OK (nodes={scan['graph_stats']['nodes']})")
        
        # Get the raw graph for GFS computation
        from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
        raw_result = scan_java_repo(repo_dir)
        graph, _, _ = scan_result_to_agq_inputs(raw_result)
        
        # Compute GFS
        gfs = compute_gfs(graph)
        
        # Compute PCV
        pcv = compute_pkg_centrality_variance(graph)
        
        scan["gfs"] = gfs
        scan["pcv"] = pcv
        scan["name"] = name
        scan["expected"] = repo_info["expected"]
        
        return scan
        
    except Exception as e:
        print(f"SCAN FAILED: {e}")
        return None
    finally:
        # Cleanup to save disk space
        shutil.rmtree(repo_dir, ignore_errors=True)


def run_scans():
    """Run scans on all pilot repos."""
    
    print("=" * 70)
    print("MULTI-REPO RE-RUN WITH ARCHIPELAGO DETECTOR + GFS")
    print("=" * 70)
    
    work_dir = tempfile.mkdtemp(prefix="qse_multirepo_")
    print(f"\nWork dir: {work_dir}")
    
    results = []
    for repo in PILOT_REPOS:
        print(f"\n--- {repo['name']} ({repo['expected']}) ---")
        scan = clone_and_scan(repo, work_dir)
        if scan:
            results.append(scan)
    
    # Cleanup work dir
    shutil.rmtree(work_dir, ignore_errors=True)
    
    return results


def analyze_results(results):
    """Analyze scan results with focus on archipelago detection and GFS."""
    
    print(f"\n\n{'='*70}")
    print("ANALYSIS")
    print(f"{'='*70}")
    
    print(f"\nSuccessfully scanned: {len(results)}/{len(PILOT_REPOS)} repos")
    
    # Table
    print(f"\n{'Name':<30} {'Exp':>6} {'AGQ':>6} {'Status':>7} {'Arch?':>6} {'GFS':>6} {'PCV':>6} {'S':>6} {'Layers':>6}")
    print("-" * 100)
    
    for r in results:
        arch = r.get("archipelago", {})
        gfs = r.get("gfs", {})
        pcv = r.get("pcv", {})
        comp = r.get("components", {})
        print(f"{r['name']:<30} {r['expected']:>6} {r['agq_v3c']:>6.3f} "
              f"{'GREEN' if r['agq_v3c'] >= 0.55 else 'AMBER' if r['agq_v3c'] >= 0.45 else 'RED':>7} "
              f"{'YES' if arch.get('detected') else 'no':>6} "
              f"{gfs.get('gfs', 0):>6.3f} "
              f"{pcv.get('pcv', 0):>6.3f} "
              f"{comp.get('S', 0):>6.3f} "
              f"{gfs.get('n_layers', 0):>6}")
    
    # Archipelago detection accuracy
    print(f"\n## Archipelago Detection")
    print("-" * 50)
    
    bad_repos = [r for r in results if r["expected"] == "BAD"]
    good_repos = [r for r in results if r["expected"] == "GOOD"]
    
    bad_detected = sum(1 for r in bad_repos if r.get("archipelago", {}).get("detected"))
    good_detected = sum(1 for r in good_repos if r.get("archipelago", {}).get("detected"))
    
    print(f"BAD repos detected as archipelago: {bad_detected}/{len(bad_repos)}")
    print(f"GOOD repos false positives: {good_detected}/{len(good_repos)}")
    
    # GFS analysis
    print(f"\n## Graph Flow Score (GFS) Analysis")
    print("-" * 50)
    
    good_gfs = [r["gfs"]["gfs"] for r in results if r["expected"] == "GOOD" and "gfs" in r]
    mixed_gfs = [r["gfs"]["gfs"] for r in results if r["expected"] == "MIXED" and "gfs" in r]
    bad_gfs = [r["gfs"]["gfs"] for r in results if r["expected"] == "BAD" and "gfs" in r]
    
    if good_gfs:
        print(f"GOOD repos GFS: mean={np.mean(good_gfs):.3f}, range=[{min(good_gfs):.3f}, {max(good_gfs):.3f}]")
    if mixed_gfs:
        print(f"MIXED repos GFS: mean={np.mean(mixed_gfs):.3f}, range=[{min(mixed_gfs):.3f}, {max(mixed_gfs):.3f}]")
    if bad_gfs:
        print(f"BAD repos GFS: mean={np.mean(bad_gfs):.3f}, range=[{min(bad_gfs):.3f}, {max(bad_gfs):.3f}]")
    
    # MW test GFS: GOOD vs BAD
    if good_gfs and bad_gfs and len(good_gfs) >= 3 and len(bad_gfs) >= 3:
        stat, p = stats.mannwhitneyu(good_gfs, bad_gfs, alternative='two-sided')
        print(f"MW test GFS (GOOD vs BAD): U={stat:.1f}, p={p:.4f}")
    
    # Compare S vs GFS discrimination
    print(f"\n## S vs GFS Comparison")
    print("-" * 50)
    
    good_s = [r["components"]["S"] for r in results if r["expected"] == "GOOD"]
    bad_s = [r["components"]["S"] for r in results if r["expected"] == "BAD"]
    
    if good_s and bad_s:
        stat_s, p_s = stats.mannwhitneyu(good_s, bad_s, alternative='two-sided')
        print(f"S discrimination (GOOD vs BAD): MW p={p_s:.4f}")
        if good_gfs and bad_gfs:
            stat_g, p_g = stats.mannwhitneyu(good_gfs, bad_gfs, alternative='two-sided')
            print(f"GFS discrimination (GOOD vs BAD): MW p={p_g:.4f}")
            print(f"GFS better than S: {p_g < p_s}")
    
    # PCV analysis
    print(f"\n## Package Centrality Variance (PCV) Analysis")
    print("-" * 50)
    
    good_pcv = [r["pcv"]["pcv"] for r in results if r["expected"] == "GOOD" and "pcv" in r]
    bad_pcv = [r["pcv"]["pcv"] for r in results if r["expected"] == "BAD" and "pcv" in r]
    
    if good_pcv:
        print(f"GOOD repos PCV: mean={np.mean(good_pcv):.3f}")
    if bad_pcv:
        print(f"BAD repos PCV: mean={np.mean(bad_pcv):.3f}")
    
    if good_pcv and bad_pcv and len(good_pcv) >= 3 and len(bad_pcv) >= 3:
        stat, p = stats.mannwhitneyu(good_pcv, bad_pcv, alternative='two-sided')
        print(f"MW test PCV (GOOD vs BAD): U={stat:.1f}, p={p:.4f}")
    
    return results


def save_results(results):
    """Save results to artifacts."""
    
    serializable = []
    for r in results:
        s = {
            "name": r["name"],
            "expected": r["expected"],
            "agq_v3c": r["agq_v3c"],
            "components": r["components"],
            "graph_stats": r["graph_stats"],
            "archipelago": {
                "detected": r.get("archipelago", {}).get("detected", False),
                "tier": r.get("archipelago", {}).get("tier"),
                "metrics": r.get("archipelago", {}).get("metrics", {}),
            },
            "gfs": r.get("gfs", {}),
            "pcv": r.get("pcv", {}),
        }
        serializable.append(s)
    
    output = {
        "experiment": "multirepo_rerun_with_detector_and_gfs",
        "date": datetime.now(timezone.utc).isoformat(),
        "n_repos": len(results),
        "results": serializable,
    }
    
    with open("artifacts/multirepo_rerun_results.json", "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nResults saved to artifacts/multirepo_rerun_results.json")


def main():
    results = run_scans()
    if results:
        analyze_results(results)
        save_results(results)
    else:
        print("No results to analyze.")


if __name__ == "__main__":
    main()
