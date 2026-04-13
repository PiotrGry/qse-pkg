"""
E8: Layer Flow Ratio — S Replacement Experiment
================================================

Faza 1: Scan kandydatów before/after refactoring, measure delta S vs delta LFR
Faza 2: Compute LFR on full GT (n=55)
Faza 3: If LFR > S → formula replacement + weight recalibration

LFR = Layer Flow Ratio
  Uses PageRank as proxy for "architectural depth":
    - High PageRank nodes = core/domain (many things depend on them)
    - Low PageRank nodes = leaf/infra (depend on others, few dependents)
  
  For each cross-package edge (u→v):
    - "Correct" if PageRank(v) >= PageRank(u)  [leaf imports core = DIP compliant]
    - "Incorrect" if PageRank(v) < PageRank(u)  [core imports leaf = DIP violation]
  
  LFR = n_correct / n_total
  LFR = 1.0 → perfect layered architecture
  LFR = 0.5 → random
  LFR < 0.5 → inverted
  
  Normalized: LFR_score = (LFR - 0.5) * 2  clamped to [0, 1]
  So random=0.0, perfect=1.0
"""

import json
import os
import sys
import subprocess
import tempfile
import shutil
import math
from collections import defaultdict
from datetime import datetime, timezone

import networkx as nx
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
from qse.graph_metrics import compute_agq, compute_stability


def compute_lfr(graph):
    """
    Layer Flow Ratio — measures DIP compliance via PageRank.
    
    High-PageRank nodes are "core" (heavily depended upon).
    Correct edge: dependency from low-PR (outer) → high-PR (inner).
    
    Returns dict with lfr, lfr_score, n_correct, n_total, pr_stats.
    """
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()
    
    if n_edges == 0 or n_nodes < 5:
        return {"lfr": 0.5, "lfr_score": 0.0, "n_correct": 0, "n_total": 0,
                "n_layers_effective": 0, "pr_gini": 0.0}
    
    # PageRank on the dependency graph
    # In import graphs: A imports B means edge A→B
    # B has high in-degree = high PageRank = "core"
    try:
        pr = nx.pagerank(graph, alpha=0.85, max_iter=200)
    except nx.PowerIterationFailedConvergence:
        pr = nx.pagerank(graph, alpha=0.85, max_iter=500, tol=1e-4)
    
    # Group by second-level package
    packages = {}
    for node in graph.nodes():
        parts = node.split(".")
        pkg = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
        packages.setdefault(pkg, []).append(node)
    
    # Package-level PageRank = mean of member PageRanks
    pkg_pr = {}
    for pkg, members in packages.items():
        pkg_pr[pkg] = np.mean([pr.get(m, 0) for m in members])
    
    # Node to package mapping
    node_pkg = {}
    for pkg, members in packages.items():
        for m in members:
            node_pkg[m] = pkg
    
    # Count correct-direction cross-package edges
    n_correct = 0
    n_total = 0
    
    for u, v in graph.edges():
        pkg_u = node_pkg.get(u)
        pkg_v = node_pkg.get(v)
        
        if pkg_u is None or pkg_v is None:
            continue
        if pkg_u == pkg_v:
            continue  # Skip intra-package edges
        
        n_total += 1
        
        # u imports v: correct if v is more "core" (higher PR) than u
        pr_u = pkg_pr.get(pkg_u, 0)
        pr_v = pkg_pr.get(pkg_v, 0)
        
        if pr_v >= pr_u:
            n_correct += 1
    
    lfr = n_correct / n_total if n_total > 0 else 0.5
    # Normalize: 0.5→0.0, 1.0→1.0
    lfr_score = max(0.0, min(1.0, (lfr - 0.5) * 2.0))
    
    # PR distribution stats (Gini coefficient as measure of hierarchy)
    pr_values = sorted(pr.values())
    n = len(pr_values)
    if n > 0 and sum(pr_values) > 0:
        cum = np.cumsum(pr_values)
        gini = (2 * sum((i + 1) * pr_values[i] for i in range(n)) / (n * sum(pr_values))) - (n + 1) / n
    else:
        gini = 0.0
    
    # Effective layers: how many distinct PR tiers exist
    pr_array = np.array(list(pkg_pr.values()))
    if len(pr_array) > 2:
        # Use quartile-based tier counting
        q25, q50, q75 = np.percentile(pr_array, [25, 50, 75])
        n_tiers = len(set([
            np.searchsorted([q25, q50, q75], v) for v in pr_array
        ]))
    else:
        n_tiers = len(pr_array)
    
    return {
        "lfr": round(lfr, 4),
        "lfr_score": round(lfr_score, 4),
        "n_correct": n_correct,
        "n_total": n_total,
        "n_cross_pkg_edges": n_total,
        "n_packages": len(packages),
        "n_layers_effective": n_tiers,
        "pr_gini": round(gini, 4),
    }


def compute_dip_compliance(graph):
    """
    Alternative DIP metric: uses per-node instability I = Ce/(Ca+Ce)
    instead of PageRank.
    
    Correct edge (u→v): I(u) > I(v) — unstable imports stable.
    This directly measures Martin's DIP principle.
    """
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()
    
    if n_edges == 0 or n_nodes < 5:
        return {"dip": 0.5, "dip_score": 0.0, "n_correct": 0, "n_total": 0}
    
    # Compute per-node instability
    node_I = {}
    for node in graph.nodes():
        ca = graph.in_degree(node)
        ce = graph.out_degree(node)
        total = ca + ce
        node_I[node] = ce / total if total > 0 else 0.5
    
    # Group by package for package-level I
    packages = {}
    for node in graph.nodes():
        parts = node.split(".")
        pkg = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
        packages.setdefault(pkg, []).append(node)
    
    pkg_I = {}
    for pkg, members in packages.items():
        pkg_I[pkg] = np.mean([node_I[m] for m in members])
    
    node_pkg = {}
    for pkg, members in packages.items():
        for m in members:
            node_pkg[m] = pkg
    
    n_correct = 0
    n_total = 0
    
    for u, v in graph.edges():
        pkg_u = node_pkg.get(u)
        pkg_v = node_pkg.get(v)
        if pkg_u is None or pkg_v is None or pkg_u == pkg_v:
            continue
        n_total += 1
        # u imports v: correct if I(u) > I(v) — unstable depends on stable
        # Also correct if equal (lateral dependency)
        if pkg_I.get(pkg_u, 0.5) >= pkg_I.get(pkg_v, 0.5):
            n_correct += 1
    
    dip = n_correct / n_total if n_total > 0 else 0.5
    dip_score = max(0.0, min(1.0, (dip - 0.5) * 2.0))
    
    return {
        "dip": round(dip, 4),
        "dip_score": round(dip_score, 4),
        "n_correct": n_correct,
        "n_total": n_total,
    }


def scan_repo_full(repo_dir, name=""):
    """Scan a Java repo and compute all metrics including LFR."""
    raw_result = scan_java_repo(repo_dir)
    graph, abstract_modules, lcom4_values = scan_result_to_agq_inputs(raw_result)
    metrics = compute_agq(graph, abstract_modules, lcom4_values)
    
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()
    
    lfr = compute_lfr(graph)
    dip = compute_dip_compliance(graph)
    
    components = {
        "M": round(metrics.modularity, 4),
        "A": round(metrics.acyclicity, 4),
        "S": round(metrics.stability, 4),
        "C": round(metrics.cohesion, 4),
        "CD": round(metrics.coupling_density, 4),
    }
    
    metrics._language = "Java"
    metrics._flat_score = 1.0
    agq = metrics.agq_v3c
    
    return {
        "name": name,
        "agq_v3c": round(agq, 4),
        "components": components,
        "graph_stats": {"nodes": n_nodes, "edges": n_edges},
        "lfr": lfr,
        "dip": dip,
    }


# --- PHASE 1: Before/After Pilots ---

# Candidate repos for refactoring pilots
# Criteria: 200-2000 nodes, clear architectural issues, Java
PILOT_CANDIDATES = [
    {
        "name": "monolith-enterprise",
        "url": "https://github.com/colinbut/monolith-enterprise-application",
        "nodes_approx": 194,
        "refactoring_type": "DIP: extract port/adapter interfaces",
        "notes": "Already done in previous pilot — include as reference"
    },
    {
        "name": "mall-learning",
        "url": "https://github.com/macrozheng/mall-learning",
        "nodes_approx": 800,
        "refactoring_type": "Break god packages, extract domain layer",
        "notes": "E-commerce tutorial project, likely flat structure"
    },
    {
        "name": "Java-WebSocket",
        "url": "https://github.com/TooTallNate/Java-WebSocket",
        "nodes_approx": 200,
        "refactoring_type": "Extract protocol layer from transport",
        "notes": "Library with mixed concerns"
    },
    {
        "name": "conductor",
        "url": "https://github.com/conductor-oss/conductor",
        "nodes_approx": 1500,
        "refactoring_type": "DIP: core→persistence boundary",
        "notes": "Workflow orchestrator, Netflix origin"
    },
    {
        "name": "javalin",
        "url": "https://github.com/javalin/javalin",
        "nodes_approx": 400,
        "refactoring_type": "Extract plugin interfaces from core",
        "notes": "Web framework, compact"
    },
    {
        "name": "jhipster-sample-app",
        "url": "https://github.com/jhipster/jhipster-sample-app",
        "nodes_approx": 300,
        "refactoring_type": "DIP: domain→infrastructure separation",
        "notes": "Generated app, typical enterprise layering issues"
    },
    {
        "name": "piggymetrics",
        "url": "https://github.com/sqshq/piggymetrics",
        "nodes_approx": 250,
        "refactoring_type": "Extract shared kernel, break circular deps",
        "notes": "Microservices demo, known circular dependencies"
    },
    {
        "name": "spring-petclinic",
        "url": "https://github.com/spring-projects/spring-petclinic",
        "nodes_approx": 100,
        "refactoring_type": "Extract repository interfaces",
        "notes": "Small but canonical — may be too small"
    },
]


def phase1_scan_candidates():
    """Phase 1a: Scan candidates to pick the best 5-8 for refactoring."""
    
    print("=" * 70)
    print("PHASE 1a: SCAN CANDIDATES")
    print("=" * 70)
    
    work_dir = tempfile.mkdtemp(prefix="qse_e8_")
    results = []
    
    for cand in PILOT_CANDIDATES:
        name = cand["name"]
        url = cand["url"]
        repo_dir = os.path.join(work_dir, name)
        
        print(f"\n--- {name} ---")
        print(f"  Cloning...", end=" ", flush=True)
        
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", url, repo_dir],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                print(f"CLONE FAILED")
                continue
            print("OK", end=" ", flush=True)
        except subprocess.TimeoutExpired:
            print("TIMEOUT")
            continue
        
        print(f"  Scanning...", end=" ", flush=True)
        try:
            scan = scan_repo_full(repo_dir, name)
            n = scan["graph_stats"]["nodes"]
            print(f"OK (nodes={n})")
            
            scan["url"] = url
            scan["refactoring_type"] = cand["refactoring_type"]
            scan["notes"] = cand["notes"]
            results.append(scan)
            
        except Exception as e:
            print(f"SCAN FAILED: {e}")
        finally:
            shutil.rmtree(repo_dir, ignore_errors=True)
    
    shutil.rmtree(work_dir, ignore_errors=True)
    
    # Display results
    print(f"\n\n{'='*70}")
    print("CANDIDATE SCAN RESULTS")
    print(f"{'='*70}")
    
    print(f"\n{'Name':<25} {'Nodes':>6} {'AGQ':>6} {'S':>6} {'LFR':>6} {'LFR_s':>6} {'DIP':>6} {'DIP_s':>6} {'Pkgs':>5} {'XPkg':>5}")
    print("-" * 100)
    
    for r in results:
        c = r["components"]
        lfr = r["lfr"]
        dip = r["dip"]
        gs = r["graph_stats"]
        print(f"{r['name']:<25} {gs['nodes']:>6} {r['agq_v3c']:>6.3f} "
              f"{c['S']:>6.3f} {lfr['lfr']:>6.3f} {lfr['lfr_score']:>6.3f} "
              f"{dip['dip']:>6.3f} {dip['dip_score']:>6.3f} "
              f"{lfr['n_packages']:>5} {lfr['n_cross_pkg_edges']:>5}")
    
    return results


def phase2_gt_lfr():
    """Phase 2: Compute LFR on full GT (n=55) by scanning GT repos."""
    
    print(f"\n\n{'='*70}")
    print("PHASE 2: LFR ON FULL GT")
    print(f"{'='*70}")
    
    with open("artifacts/gt_java_expanded.json") as f:
        gt = json.load(f)
    
    active_gt = [r for r in gt if r.get("cat") != "EXCL"]
    print(f"\nActive GT repos: {len(active_gt)}")
    
    work_dir = tempfile.mkdtemp(prefix="qse_e8_gt_")
    gt_results = []
    
    for repo_info in active_gt:
        repo_name = repo_info["repo"]
        url = f"https://github.com/{repo_name}"
        short_name = repo_name.split("/")[-1]
        local_dir = os.path.join(work_dir, short_name)
        
        print(f"  {repo_name}...", end=" ", flush=True)
        
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", url, local_dir],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                print(f"CLONE FAILED")
                gt_results.append({
                    "repo": repo_name,
                    "cat": repo_info["cat"],
                    "panel": repo_info.get("panel", 0),
                    "S": repo_info.get("S", 0),
                    "error": "clone_failed"
                })
                continue
        except subprocess.TimeoutExpired:
            print("TIMEOUT")
            gt_results.append({
                "repo": repo_name,
                "cat": repo_info["cat"],
                "panel": repo_info.get("panel", 0),
                "S": repo_info.get("S", 0),
                "error": "timeout"
            })
            continue
        
        try:
            scan = scan_repo_full(local_dir, short_name)
            print(f"OK (nodes={scan['graph_stats']['nodes']}, "
                  f"LFR={scan['lfr']['lfr']:.3f}, S={scan['components']['S']:.3f})")
            
            gt_results.append({
                "repo": repo_name,
                "cat": repo_info["cat"],
                "panel": repo_info.get("panel", 0),
                "S_gt": repo_info.get("S", 0),
                "S_rescan": scan["components"]["S"],
                "lfr": scan["lfr"]["lfr"],
                "lfr_score": scan["lfr"]["lfr_score"],
                "dip": scan["dip"]["dip"],
                "dip_score": scan["dip"]["dip_score"],
                "pr_gini": scan["lfr"]["pr_gini"],
                "n_packages": scan["lfr"]["n_packages"],
                "n_cross_pkg": scan["lfr"]["n_cross_pkg_edges"],
                "nodes": scan["graph_stats"]["nodes"],
                "agq_v3c": scan["agq_v3c"],
                "components": scan["components"],
            })
        except Exception as e:
            print(f"SCAN FAILED: {e}")
            gt_results.append({
                "repo": repo_name,
                "cat": repo_info["cat"],
                "panel": repo_info.get("panel", 0),
                "S": repo_info.get("S", 0),
                "error": str(e)[:100]
            })
        finally:
            shutil.rmtree(local_dir, ignore_errors=True)
    
    shutil.rmtree(work_dir, ignore_errors=True)
    
    # Analyze
    successful = [r for r in gt_results if "error" not in r]
    print(f"\n\nSuccessfully scanned: {len(successful)}/{len(active_gt)}")
    
    if len(successful) < 20:
        print("WARNING: Too few successful scans for reliable statistics")
    
    # Correlation analysis
    print(f"\n## LFR vs Panel Correlation")
    print("-" * 50)
    
    panels = [r["panel"] for r in successful]
    lfr_scores = [r["lfr_score"] for r in successful]
    lfr_raw = [r["lfr"] for r in successful]
    s_values = [r["S_rescan"] for r in successful]
    dip_scores = [r["dip_score"] for r in successful]
    dip_raw = [r["dip"] for r in successful]
    nodes = [r["nodes"] for r in successful]
    
    # Spearman correlations
    rho_lfr, p_lfr = stats.spearmanr(lfr_raw, panels)
    rho_s, p_s = stats.spearmanr(s_values, panels)
    rho_dip, p_dip = stats.spearmanr(dip_raw, panels)
    
    print(f"LFR vs Panel:     ρ={rho_lfr:.4f}, p={p_lfr:.4f}")
    print(f"S vs Panel:       ρ={rho_s:.4f}, p={p_s:.4f}")
    print(f"DIP vs Panel:     ρ={rho_dip:.4f}, p={p_dip:.4f}")
    
    # Partial correlations (controlling for nodes)
    rho_nodes_lfr, _ = stats.spearmanr(lfr_raw, nodes)
    rho_nodes_panel, _ = stats.spearmanr(nodes, panels)
    rho_nodes_s, _ = stats.spearmanr(s_values, nodes)
    rho_nodes_dip, _ = stats.spearmanr(dip_raw, nodes)
    
    def partial_r(rho_xy, rho_xz, rho_yz):
        denom = math.sqrt((1 - rho_xz**2) * (1 - rho_yz**2))
        return (rho_xy - rho_xz * rho_yz) / denom if denom > 0 else 0
    
    pr_lfr = partial_r(rho_lfr, rho_nodes_lfr, rho_nodes_panel)
    pr_s = partial_r(rho_s, rho_nodes_s, rho_nodes_panel)
    pr_dip = partial_r(rho_dip, rho_nodes_dip, rho_nodes_panel)
    
    print(f"\nPartial r (controlling for nodes):")
    print(f"LFR|nodes vs Panel: {pr_lfr:.4f}")
    print(f"S|nodes vs Panel:   {pr_s:.4f}")
    print(f"DIP|nodes vs Panel: {pr_dip:.4f}")
    
    # MW test
    pos_lfr = [r["lfr"] for r in successful if r["cat"] == "POS"]
    neg_lfr = [r["lfr"] for r in successful if r["cat"] == "NEG"]
    pos_s = [r["S_rescan"] for r in successful if r["cat"] == "POS"]
    neg_s = [r["S_rescan"] for r in successful if r["cat"] == "NEG"]
    pos_dip = [r["dip"] for r in successful if r["cat"] == "POS"]
    neg_dip = [r["dip"] for r in successful if r["cat"] == "NEG"]
    
    if pos_lfr and neg_lfr:
        stat_lfr, p_mw_lfr = stats.mannwhitneyu(pos_lfr, neg_lfr, alternative='two-sided')
        stat_s, p_mw_s = stats.mannwhitneyu(pos_s, neg_s, alternative='two-sided')
        stat_dip, p_mw_dip = stats.mannwhitneyu(pos_dip, neg_dip, alternative='two-sided')
        
        print(f"\nMann-Whitney POS vs NEG:")
        print(f"LFR: U={stat_lfr:.1f}, p={p_mw_lfr:.4f}, POS mean={np.mean(pos_lfr):.3f}, NEG mean={np.mean(neg_lfr):.3f}")
        print(f"S:   U={stat_s:.1f}, p={p_mw_s:.4f}, POS mean={np.mean(pos_s):.3f}, NEG mean={np.mean(neg_s):.3f}")
        print(f"DIP: U={stat_dip:.1f}, p={p_mw_dip:.4f}, POS mean={np.mean(pos_dip):.3f}, NEG mean={np.mean(neg_dip):.3f}")
    
    # LFR distribution by category
    print(f"\n## LFR Distribution by Category")
    print("-" * 50)
    print(f"{'Category':<8} {'n':>4} {'LFR mean':>10} {'LFR std':>10} {'S mean':>10} {'DIP mean':>10}")
    for cat in ["POS", "NEG"]:
        cat_repos = [r for r in successful if r["cat"] == cat]
        if cat_repos:
            print(f"{cat:<8} {len(cat_repos):>4} "
                  f"{np.mean([r['lfr'] for r in cat_repos]):>10.4f} "
                  f"{np.std([r['lfr'] for r in cat_repos]):>10.4f} "
                  f"{np.mean([r['S_rescan'] for r in cat_repos]):>10.4f} "
                  f"{np.mean([r['dip'] for r in cat_repos]):>10.4f}")
    
    # Redundancy check: LFR vs S correlation
    print(f"\n## Redundancy Check")
    print("-" * 50)
    rho_lfr_s, p_lfr_s = stats.spearmanr(lfr_raw, s_values)
    rho_dip_s, p_dip_s = stats.spearmanr(dip_raw, s_values)
    print(f"LFR vs S: ρ={rho_lfr_s:.4f}, p={p_lfr_s:.4f}")
    print(f"DIP vs S: ρ={rho_dip_s:.4f}, p={p_dip_s:.4f}")
    
    if abs(rho_lfr_s) > 0.7:
        print("⚠️ LFR is highly correlated with S — may be redundant")
    elif abs(rho_lfr_s) < 0.3:
        print("✓ LFR captures a different dimension than S")
    else:
        print("△ LFR moderately correlated with S — partially overlapping signal")
    
    # PR Gini as hierarchy measure
    print(f"\n## PageRank Gini (hierarchy measure)")
    print("-" * 50)
    pr_gini = [r["pr_gini"] for r in successful]
    rho_gini, p_gini = stats.spearmanr(pr_gini, panels)
    print(f"PR Gini vs Panel: ρ={rho_gini:.4f}, p={p_gini:.4f}")
    
    return gt_results, successful


def phase3_formula_comparison(successful):
    """Phase 3: Compare AGQ with S vs AGQ with LFR."""
    
    print(f"\n\n{'='*70}")
    print("PHASE 3: FORMULA COMPARISON")
    print(f"{'='*70}")
    
    if len(successful) < 20:
        print("Insufficient data for reliable formula comparison")
        return
    
    panels = np.array([r["panel"] for r in successful])
    nodes = np.array([r["nodes"] for r in successful])
    cats = [r["cat"] for r in successful]
    
    # Get component values
    M = np.array([r["components"]["M"] for r in successful])
    A = np.array([r["components"]["A"] for r in successful])
    S = np.array([r["components"]["S"] for r in successful])
    C = np.array([r["components"]["C"] for r in successful])
    CD = np.array([r["components"]["CD"] for r in successful])
    LFR_score = np.array([r["lfr_score"] for r in successful])
    DIP_score = np.array([r["dip_score"] for r in successful])
    
    # Current formula: AGQ_v3c = 0.20*M + 0.20*A + 0.20*S + 0.20*C + 0.20*CD
    agq_current = 0.20*M + 0.20*A + 0.20*S + 0.20*C + 0.20*CD
    
    # Replace S with LFR_score
    agq_lfr = 0.20*M + 0.20*A + 0.20*LFR_score + 0.20*C + 0.20*CD
    
    # Replace S with DIP_score
    agq_dip = 0.20*M + 0.20*A + 0.20*DIP_score + 0.20*C + 0.20*CD
    
    # Weight grid search for LFR
    print(f"\n## Equal-weight comparison (all 0.20)")
    print("-" * 50)
    
    for name, agq in [("AGQ_current (S)", agq_current), 
                       ("AGQ_lfr", agq_lfr),
                       ("AGQ_dip", agq_dip)]:
        rho, p = stats.spearmanr(agq, panels)
        pos_agq = agq[[i for i, c in enumerate(cats) if c == "POS"]]
        neg_agq = agq[[i for i, c in enumerate(cats) if c == "NEG"]]
        stat, p_mw = stats.mannwhitneyu(pos_agq, neg_agq, alternative='two-sided')
        
        # Partial r
        rho_an, _ = stats.spearmanr(agq, nodes)
        rho_pn, _ = stats.spearmanr(panels, nodes)
        denom = math.sqrt((1 - rho_an**2) * (1 - rho_pn**2))
        pr = (rho - rho_an * rho_pn) / denom if denom > 0 else 0
        
        # AUC
        from itertools import product as cartesian
        n_pos = len(pos_agq)
        n_neg = len(neg_agq)
        concordant = sum(1 for p_, n_ in cartesian(pos_agq, neg_agq) if p_ > n_)
        tied = sum(1 for p_, n_ in cartesian(pos_agq, neg_agq) if p_ == n_)
        auc = (concordant + 0.5 * tied) / (n_pos * n_neg) if n_pos * n_neg > 0 else 0.5
        
        print(f"\n{name}:")
        print(f"  Spearman ρ={rho:.4f}, p={p:.4f}")
        print(f"  Partial r|nodes={pr:.4f}")
        print(f"  MW p={p_mw:.4f}")
        print(f"  AUC={auc:.4f}")
        print(f"  POS mean={np.mean(pos_agq):.4f}, NEG mean={np.mean(neg_agq):.4f}, gap={np.mean(pos_agq)-np.mean(neg_agq):.4f}")
    
    # Weight optimization for LFR variant
    print(f"\n## Weight optimization (LFR variant)")
    print("-" * 50)
    
    best_pr = -1
    best_weights = None
    
    # Grid search over weight space
    for wm in np.arange(0.10, 0.35, 0.05):
        for wa in np.arange(0.05, 0.25, 0.05):
            for wlfr in np.arange(0.10, 0.35, 0.05):
                for wc in np.arange(0.10, 0.35, 0.05):
                    wcd = 1.0 - wm - wa - wlfr - wc
                    if wcd < 0.05 or wcd > 0.35:
                        continue
                    
                    agq_test = wm*M + wa*A + wlfr*LFR_score + wc*C + wcd*CD
                    rho_t, _ = stats.spearmanr(agq_test, panels)
                    rho_an, _ = stats.spearmanr(agq_test, nodes)
                    rho_pn, _ = stats.spearmanr(panels, nodes)
                    d = math.sqrt((1 - rho_an**2) * (1 - rho_pn**2))
                    pr_t = (rho_t - rho_an * rho_pn) / d if d > 0 else 0
                    
                    if pr_t > best_pr:
                        best_pr = pr_t
                        best_weights = (wm, wa, wlfr, wc, wcd)
    
    if best_weights:
        print(f"Best weights (LFR): M={best_weights[0]:.2f} A={best_weights[1]:.2f} "
              f"LFR={best_weights[2]:.2f} C={best_weights[3]:.2f} CD={best_weights[4]:.2f}")
        print(f"Best partial r: {best_pr:.4f}")
        
        # Compare with current best
        rho_cur, _ = stats.spearmanr(agq_current, panels)
        rho_cur_n, _ = stats.spearmanr(agq_current, nodes)
        rho_pn, _ = stats.spearmanr(panels, nodes)
        d = math.sqrt((1 - rho_cur_n**2) * (1 - rho_pn**2))
        pr_cur = (rho_cur - rho_cur_n * rho_pn) / d if d > 0 else 0
        
        print(f"\nCurrent (S) partial r: {pr_cur:.4f}")
        print(f"Improvement: {best_pr - pr_cur:+.4f}")
        
        if best_pr > pr_cur + 0.05:
            print(f"\n✓ LFR SIGNIFICANTLY BETTER than S — replacement justified")
        elif best_pr > pr_cur:
            print(f"\n△ LFR marginally better — replacement questionable")
        else:
            print(f"\n✗ LFR NOT better than S — keep S")


def save_all_results(candidates, gt_results, successful):
    """Save everything to artifacts."""
    
    output = {
        "experiment": "E8_LFR_S_Replacement",
        "date": datetime.now(timezone.utc).isoformat(),
        "phase1_candidates": candidates if candidates else [],
        "phase2_gt_results": gt_results,
        "phase2_successful": len(successful),
        "phase2_total": len(gt_results),
    }
    
    with open("artifacts/e8_lfr_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\nAll results saved to artifacts/e8_lfr_results.json")


def main():
    # Phase 1a: Scan candidates
    candidates = phase1_scan_candidates()
    
    # Phase 2: LFR on full GT
    gt_results, successful = phase2_gt_lfr()
    
    # Phase 3: Formula comparison
    if successful:
        phase3_formula_comparison(successful)
    
    # Save
    save_all_results(candidates, gt_results, successful)
    
    print(f"\n\n{'='*70}")
    print("E8 EXPERIMENT COMPLETE")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
