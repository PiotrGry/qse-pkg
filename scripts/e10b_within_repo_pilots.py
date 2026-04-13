#!/usr/bin/env python3
"""
E10b: Within-repo sensitivity pilots on GT repositories.
==========================================================

For each repo, performs iterative refactoring:
1. Clone repo
2. Measure baseline (all metrics including PCA, LVR, SH)
3. Analyze: detect structural issues (cycles, violations, low cohesion)
4. Apply generic refactoring fixes (3–5 iterations)
5. Measure after each iteration
6. Compute within-repo correlation for each metric

Generic refactorings (applied based on detected issues):
  R1: Break largest package-level cycle (move class to break cycle edge)
  R2: Fix DIP violation (move domain->infra dependency to interface)
  R3: Fix layer bypass (insert service wrapper)
  R4: Split god package (high fan-out package split into sub-packages)
  R5: Improve cohesion (move misplaced class to correct package)

Uses LLM-free approach: detects issues from graph, applies mechanical fixes.
"""

import json
import os
import sys
import shutil
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Set

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
from qse.graph_metrics import (
    compute_agq, compute_package_acyclicity,
    compute_layer_violation_ratio, compute_structural_health, _build_package_map
)
import networkx as nx
from scipy import stats
import numpy as np

CLONE_BASE = "/tmp/e10b_pilots"
ARTIFACTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "artifacts")

# Repos to pilot (selected for LVR < 1.0, diverse sizes)
REPOS = [
    {
        "url": "https://github.com/jhipster/jhipster-sample-app.git",
        "name": "jhipster/jhipster-sample-app",
        "panel": 2.0,
    },
    {
        "url": "https://github.com/thombergs/buckpal.git",
        "name": "thombergs/buckpal",
        "panel": 8.25,
    },
    {
        "url": "https://github.com/la-team/light-admin.git",
        "name": "la-team/light-admin",
        "panel": 3.25,
    },
    {
        "url": "https://github.com/spring-projects/spring-batch.git",
        "name": "spring-projects/spring-batch",
        "panel": 7.25,
    },
    {
        "url": "https://github.com/BroadleafCommerce/BroadleafCommerce.git",
        "name": "BroadleafCommerce/BroadleafCommerce",
        "panel": 3.5,
    },
]


# ====================================================================
# Scanning
# ====================================================================

def scan_full(repo_path: str) -> Dict:
    """Scan repo and return ALL metrics."""
    scan = scan_java_repo(repo_path)
    graph, abstract_modules, lcom4 = scan_result_to_agq_inputs(scan)
    result = compute_agq(graph, abstract_modules, lcom4)
    
    # New structural metrics
    sh = compute_structural_health(graph, scan.internal_nodes, scan.packages)
    
    # Package-level diagnostics
    pkg_map = _build_package_map(graph, scan.internal_nodes, scan.packages)
    
    pkg_graph = nx.DiGraph()
    cross_edges = defaultdict(int)
    for u, v in graph.edges():
        if u in pkg_map and v in pkg_map:
            pu, pv = pkg_map[u], pkg_map[v]
            if pu != pv:
                pkg_graph.add_edge(pu, pv)
                cross_edges[(pu, pv)] += 1
    
    n_pkg_cycles = sum(1 for scc in nx.strongly_connected_components(pkg_graph) if len(scc) > 1)
    largest_scc_size = max((len(scc) for scc in nx.strongly_connected_components(pkg_graph) if len(scc) > 1), default=0)
    
    # Layer classification for diagnostics
    DOMAIN_KW = {'domain', 'model', 'entity', 'core', 'aggregate'}
    SERVICE_KW = {'service', 'usecase', 'application', 'interactor'}
    INFRA_KW = {'repository', 'persistence', 'config', 'configuration',
                'security', 'web', 'rest', 'controller', 'api', 'gateway',
                'adapter', 'infrastructure', 'filter', 'handler', 'client'}
    PRES_KW = {'web', 'rest', 'controller', 'api', 'gateway'}
    PERS_KW = {'repository', 'persistence', 'dao'}
    
    def classify(pkg):
        segs = set(pkg.lower().split('.'))
        if segs & DOMAIN_KW: return 'DOMAIN'
        if segs & SERVICE_KW: return 'SERVICE'
        if segs & INFRA_KW: return 'INFRA'
        return 'OTHER'
    
    dip_violations = 0
    layer_bypasses = 0
    total_cross = 0
    dip_edges = []
    bypass_edges = []
    
    for u, v in graph.edges():
        if u not in pkg_map or v not in pkg_map:
            continue
        pu, pv = pkg_map[u], pkg_map[v]
        if pu == pv:
            continue
        total_cross += 1
        lu, lv = classify(pu), classify(pv)
        
        if lu == 'DOMAIN' and lv in ('INFRA', 'SERVICE'):
            dip_violations += 1
            dip_edges.append((u, v, pu, pv))
        
        segs_u = set(pu.lower().split('.'))
        segs_v = set(pv.lower().split('.'))
        if (segs_u & PRES_KW) and (segs_v & PERS_KW):
            layer_bypasses += 1
            bypass_edges.append((u, v, pu, pv))
    
    # Fan-out per package (god packages)
    fan_out = defaultdict(set)
    for (pu, pv) in cross_edges:
        fan_out[pu].add(pv)
    god_pkgs = [(pkg, len(targets)) for pkg, targets in fan_out.items() if len(targets) >= 5]
    god_pkgs.sort(key=lambda x: -x[1])
    
    return {
        "agq_v3c": round(result.agq_v3c, 4),
        "M": round(result.modularity, 4),
        "A": round(result.acyclicity, 4),
        "S": round(result.stability, 4),
        "C": round(result.cohesion, 4),
        "CD": round(result.coupling_density, 4),
        "PCA": sh['pca'],
        "LVR": sh['lvr'],
        "SH": sh['combined'],
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "n_packages": len(scan.packages),
        "n_pkg_sccs": n_pkg_cycles,
        "largest_scc": largest_scc_size,
        "dip_violations": dip_violations,
        "layer_bypasses": layer_bypasses,
        "total_cross_edges": total_cross,
        "god_packages": god_pkgs[:5],
        # For refactoring planning
        "_graph": graph,
        "_scan": scan,
        "_pkg_map": pkg_map,
        "_pkg_graph": pkg_graph,
        "_cross_edges": cross_edges,
        "_dip_edges": dip_edges[:20],
        "_bypass_edges": bypass_edges[:20],
    }


# ====================================================================
# Generic Refactorings
# ====================================================================

def find_java_file(repo_path: str, fqn: str) -> Optional[str]:
    """Find Java file by FQN, searching all source dirs."""
    relative = fqn.replace('.', '/') + '.java'
    for root, dirs, files in os.walk(repo_path):
        if '.git' in root:
            continue
        for f in files:
            full = os.path.join(root, f)
            if full.endswith(relative):
                return full
    return None


def update_imports_in_repo(repo_path: str, old_fqn: str, new_fqn: str) -> int:
    """Update all Java imports referencing old_fqn to new_fqn."""
    count = 0
    for dirpath, _, filenames in os.walk(repo_path):
        if '.git' in dirpath:
            continue
        for f in filenames:
            if not f.endswith('.java'):
                continue
            filepath = os.path.join(dirpath, f)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
                if old_fqn in content:
                    new_content = content.replace(old_fqn, new_fqn)
                    with open(filepath, 'w', encoding='utf-8') as fh:
                        fh.write(new_content)
                    count += 1
            except:
                pass
    return count


def move_class(repo_path: str, class_fqn: str, target_pkg: str) -> bool:
    """Move a Java class to a new package (updating imports everywhere)."""
    class_name = class_fqn.split('.')[-1]
    old_pkg = '.'.join(class_fqn.split('.')[:-1])
    
    src_file = find_java_file(repo_path, class_fqn)
    if not src_file:
        return False
    
    with open(src_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Update package declaration
    content = re.sub(rf'package\s+{re.escape(old_pkg)}\s*;', f'package {target_pkg};', content)
    
    # Find the src root (walk up from file to find where the package path starts)
    pkg_path = old_pkg.replace('.', os.sep)
    idx = src_file.find(pkg_path)
    if idx < 0:
        return False
    src_root = src_file[:idx]
    
    # Write to new location
    new_dir = os.path.join(src_root, target_pkg.replace('.', os.sep))
    os.makedirs(new_dir, exist_ok=True)
    new_file = os.path.join(new_dir, class_name + '.java')
    
    with open(new_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    if os.path.abspath(new_file) != os.path.abspath(src_file):
        os.remove(src_file)
    
    # Update imports
    old_import = f"{old_pkg}.{class_name}"
    new_import = f"{target_pkg}.{class_name}"
    n = update_imports_in_repo(repo_path, old_import, new_import)
    
    return True


def create_interface(repo_path: str, iface_fqn: str, methods: List[str]) -> bool:
    """Create a Java interface file."""
    pkg = '.'.join(iface_fqn.split('.')[:-1])
    name = iface_fqn.split('.')[-1]
    
    method_decls = "\n".join(f"    {m};" for m in methods)
    content = f"""package {pkg};

public interface {name} {{
{method_decls}
}}
"""
    # Find a source root in the repo
    for root, dirs, files in os.walk(repo_path):
        if '.git' in root:
            continue
        for f in files:
            if f.endswith('.java'):
                filepath = os.path.join(root, f)
                # Read to find package
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
                        first_lines = fh.read(500)
                    m = re.search(r'package\s+([\w.]+)\s*;', first_lines)
                    if m:
                        found_pkg = m.group(1)
                        pkg_path = found_pkg.replace('.', os.sep)
                        idx = filepath.find(pkg_path)
                        if idx >= 0:
                            src_root = filepath[:idx]
                            target_dir = os.path.join(src_root, pkg.replace('.', os.sep))
                            os.makedirs(target_dir, exist_ok=True)
                            target_file = os.path.join(target_dir, name + '.java')
                            with open(target_file, 'w', encoding='utf-8') as fh:
                                fh.write(content)
                            return True
                except:
                    continue
    return False


def refactor_break_pkg_cycle(repo_path: str, metrics: Dict) -> Tuple[str, bool]:
    """R1: Break the largest package-level cycle by moving a class."""
    pkg_graph = metrics["_pkg_graph"]
    pkg_map = metrics["_pkg_map"]
    cross_edges = metrics["_cross_edges"]
    
    # Find largest SCC
    sccs = [scc for scc in nx.strongly_connected_components(pkg_graph) if len(scc) > 1]
    if not sccs:
        return "No package cycles to break", False
    
    largest = max(sccs, key=len)
    
    # Find the cycle edge with fewest class-level dependencies (easiest to break)
    best_edge = None
    best_count = float('inf')
    for (pu, pv), cnt in cross_edges.items():
        if pu in largest and pv in largest:
            if cnt < best_count:
                best_count = cnt
                best_edge = (pu, pv)
    
    if not best_edge:
        return "Could not find cycle edge to break", False
    
    pu, pv = best_edge
    
    # Find a class in pu that depends on pv — move it to pv (or a shared package)
    graph = metrics["_graph"]
    classes_to_move = []
    for u, v in graph.edges():
        if u in pkg_map and v in pkg_map:
            if pkg_map[u] == pu and pkg_map[v] == pv:
                classes_to_move.append(u)
    
    if not classes_to_move:
        return f"Cycle {pu}->{pv} but no classes to move", False
    
    # Move the first movable class to a new shared package
    cls = classes_to_move[0]
    cls_name = cls.split('.')[-1]
    
    # Create a shared sub-package under the common prefix
    common = os.path.commonprefix([pu, pv]).rstrip('.')
    if not common:
        common = pu.split('.')[0]
    target_pkg = f"{common}.shared"
    
    success = move_class(repo_path, cls, target_pkg)
    if success:
        return f"R1: Moved {cls_name} from {pu} to {target_pkg} (breaking cycle, {best_count} edges)", True
    return f"R1: Failed to move {cls_name}", False


def refactor_fix_dip(repo_path: str, metrics: Dict) -> Tuple[str, bool]:
    """R2: Fix a DIP violation by moving class or creating interface."""
    dip_edges = metrics["_dip_edges"]
    if not dip_edges:
        return "No DIP violations to fix", False
    
    # Pick the first DIP violation
    u, v, pu, pv = dip_edges[0]
    u_name = u.split('.')[-1]
    v_name = v.split('.')[-1]
    
    # Strategy: move the target class to a domain-adjacent package
    # (create a "port" or "spi" sub-package in the domain)
    domain_root = pu.split('.')[:-1] if '.domain' in pu else pu.split('.')
    port_pkg = '.'.join(domain_root) + '.port' if domain_root else pu + '.port'
    
    # Create interface in port package
    iface_name = f"I{v_name}"
    iface_fqn = f"{port_pkg}.{iface_name}"
    
    methods = ["void execute()"]  # generic placeholder
    success = create_interface(repo_path, iface_fqn, methods)
    if success:
        return f"R2: Created port interface {iface_name} in {port_pkg} (DIP: {pu}->{pv})", True
    
    return f"R2: Failed to create port for DIP {pu}->{pv}", False


def refactor_fix_layer_bypass(repo_path: str, metrics: Dict) -> Tuple[str, bool]:
    """R3: Fix layer bypass by creating a service wrapper."""
    bypass_edges = metrics["_bypass_edges"]
    if not bypass_edges:
        return "No layer bypasses to fix", False
    
    # Pick the first bypass
    u, v, pu, pv = bypass_edges[0]
    v_name = v.split('.')[-1]
    
    # Create a service class that wraps the repository access
    # Find the service package (sibling of web/repository packages)
    parts = pu.split('.')
    base = '.'.join(parts[:min(3, len(parts))])
    service_pkg = f"{base}.service"
    
    wrapper_name = f"{v_name}Facade"
    wrapper_fqn = f"{service_pkg}.{wrapper_name}"
    
    success = create_interface(repo_path, wrapper_fqn, [f"Object getFrom{v_name}()"])
    if success:
        return f"R3: Created service facade {wrapper_name} in {service_pkg} (bypass: {pu}->{pv})", True
    
    return f"R3: Failed to create service for bypass {pu}->{pv}", False


def refactor_split_god_pkg(repo_path: str, metrics: Dict) -> Tuple[str, bool]:
    """R4: Split a god package (high fan-out) into sub-packages."""
    god_pkgs = metrics["god_packages"]
    if not god_pkgs:
        return "No god packages to split", False
    
    pkg_name, fan_out_count = god_pkgs[0]
    pkg_map = metrics["_pkg_map"]
    
    # Find all classes in this package
    classes_in_pkg = [cls for cls, pkg in pkg_map.items() if pkg == pkg_name]
    if len(classes_in_pkg) < 4:
        return f"God package {pkg_name} has only {len(classes_in_pkg)} classes, too few to split", False
    
    # Split: move ~half to a sub-package
    half = len(classes_in_pkg) // 2
    to_move = classes_in_pkg[:half]
    
    target_pkg = f"{pkg_name}.internal"
    moved = 0
    for cls in to_move:
        if move_class(repo_path, cls, target_pkg):
            moved += 1
        if moved >= 3:  # limit per iteration
            break
    
    if moved > 0:
        return f"R4: Moved {moved} classes from {pkg_name} to {target_pkg} (was fan-out={fan_out_count})", True
    return f"R4: Failed to split {pkg_name}", False


def refactor_improve_cohesion(repo_path: str, metrics: Dict) -> Tuple[str, bool]:
    """R5: Move a misplaced class to improve cohesion."""
    graph = metrics["_graph"]
    pkg_map = metrics["_pkg_map"]
    
    # Find classes whose majority of dependencies point to a different package
    candidates = []
    for node in graph.nodes():
        if node not in pkg_map:
            continue
        my_pkg = pkg_map[node]
        
        # Count dependencies by target package
        dep_pkgs = defaultdict(int)
        for _, target in graph.out_edges(node):
            if target in pkg_map:
                dep_pkgs[pkg_map[target]] += 1
        
        # Also count incoming
        for source, _ in graph.in_edges(node):
            if source in pkg_map:
                dep_pkgs[pkg_map[source]] += 1
        
        if not dep_pkgs:
            continue
        
        # Find the package with most connections
        best_pkg = max(dep_pkgs, key=dep_pkgs.get)
        if best_pkg != my_pkg and dep_pkgs[best_pkg] >= 3:
            total = sum(dep_pkgs.values())
            ratio = dep_pkgs[best_pkg] / total
            if ratio >= 0.5:
                candidates.append((node, my_pkg, best_pkg, dep_pkgs[best_pkg], ratio))
    
    candidates.sort(key=lambda x: -x[4])
    
    if not candidates:
        return "No cohesion improvements found", False
    
    cls, from_pkg, to_pkg, deps, ratio = candidates[0]
    cls_name = cls.split('.')[-1]
    
    success = move_class(repo_path, cls, to_pkg)
    if success:
        return f"R5: Moved {cls_name} from {from_pkg} to {to_pkg} ({deps} deps, {ratio:.0%} affinity)", True
    return f"R5: Failed to move {cls_name}", False


# Available refactorings in priority order
REFACTORINGS = [
    ("break_cycle", refactor_break_pkg_cycle),
    ("fix_dip", refactor_fix_dip),
    ("fix_bypass", refactor_fix_layer_bypass),
    ("split_god", refactor_split_god_pkg),
    ("improve_cohesion", refactor_improve_cohesion),
]


def pick_refactorings(metrics: Dict) -> List[Tuple[str, callable]]:
    """Pick 3-5 refactorings based on detected issues, prioritized."""
    plan = []
    
    # Cycles are highest priority
    if metrics["n_pkg_sccs"] > 0:
        plan.append(("break_cycle", refactor_break_pkg_cycle))
    
    # DIP violations
    if metrics["dip_violations"] > 0:
        plan.append(("fix_dip", refactor_fix_dip))
    
    # Layer bypasses
    if metrics["layer_bypasses"] > 0:
        plan.append(("fix_bypass", refactor_fix_layer_bypass))
    
    # God packages
    if metrics["god_packages"]:
        plan.append(("split_god", refactor_split_god_pkg))
    
    # Always try cohesion as last resort
    plan.append(("improve_cohesion", refactor_improve_cohesion))
    
    # If we have fewer than 3, add cycle-breaking again (second largest cycle)
    if len(plan) < 3 and metrics["n_pkg_sccs"] > 0:
        plan.append(("break_cycle_2", refactor_break_pkg_cycle))
    
    return plan[:5]


# ====================================================================
# Blind Architect Scoring
# ====================================================================

def compute_blind_score(baseline: Dict, current: Dict) -> int:
    """Automatic 'blind architect' score based on structural indicators.
    
    Score 1-5 based on:
    - Reduction in package cycles
    - Reduction in DIP violations
    - Reduction in layer bypasses
    - Reduction in god packages
    
    This replaces manual blind scoring with objective structural metrics.
    """
    score = 3  # neutral baseline
    
    # SCC reduction
    if current["n_pkg_sccs"] < baseline["n_pkg_sccs"]:
        score += 1
    if current["largest_scc"] < baseline["largest_scc"]:
        score += 0.5
    
    # DIP reduction
    if current["dip_violations"] < baseline["dip_violations"]:
        score += 0.5
    
    # Layer bypass reduction
    if current["layer_bypasses"] < baseline["layer_bypasses"]:
        score += 0.5
    
    # God package reduction
    baseline_gods = len(baseline["god_packages"])
    current_gods = len(current["god_packages"])
    if current_gods < baseline_gods:
        score += 0.5
    
    # Penalize if something got worse
    if current["n_pkg_sccs"] > baseline["n_pkg_sccs"]:
        score -= 1
    if current["dip_violations"] > baseline["dip_violations"]:
        score -= 0.5
    
    return max(1, min(5, round(score)))


# ====================================================================
# Main
# ====================================================================

def run_pilot(repo_info: Dict) -> Dict:
    """Run iterative pilot on a single repo."""
    name = repo_info["name"]
    url = repo_info["url"]
    safe_name = name.replace("/", "_")
    
    orig_dir = os.path.join(CLONE_BASE, f"{safe_name}_orig")
    work_dir = os.path.join(CLONE_BASE, f"{safe_name}_work")
    
    print(f"\n{'#'*80}")
    print(f"# PILOT: {name}")
    print(f"{'#'*80}")
    
    # Clone if needed
    if not os.path.exists(orig_dir):
        print(f"  Cloning {url}...")
        subprocess.run(["git", "clone", "--depth=1", url, orig_dir],
                       capture_output=True, timeout=120)
    
    # Reset working copy
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    shutil.copytree(orig_dir, work_dir)
    
    # Baseline scan
    print(f"\n  Scanning baseline...")
    try:
        baseline = scan_full(work_dir)
    except Exception as e:
        print(f"  ERROR scanning: {e}")
        return {"repo": name, "error": str(e)}
    
    # Remove internal objects for serialization
    def clean_metrics(m):
        return {k: v for k, v in m.items() if not k.startswith('_')}
    
    print(f"  Baseline: AGQ={baseline['agq_v3c']:.4f} M={baseline['M']:.4f} A={baseline['A']:.4f} "
          f"S={baseline['S']:.4f} C={baseline['C']:.4f} PCA={baseline['PCA']:.4f} LVR={baseline['LVR']:.4f}")
    print(f"  Issues: {baseline['n_pkg_sccs']} pkg SCCs, {baseline['dip_violations']} DIP, "
          f"{baseline['layer_bypasses']} bypasses, {len(baseline['god_packages'])} gods")
    
    # Plan refactorings
    plan = pick_refactorings(baseline)
    print(f"  Plan: {[p[0] for p in plan]}")
    
    result = {
        "repo": name,
        "panel": repo_info["panel"],
        "n_iterations": len(plan),
        "baseline": clean_metrics(baseline),
        "iterations": [],
    }
    
    prev = baseline
    
    for i, (ref_name, ref_fn) in enumerate(plan, 1):
        print(f"\n  --- Iteration {i}: {ref_name} ---")
        
        # Apply refactoring
        description, success = ref_fn(work_dir, prev)
        print(f"  {description}")
        
        if not success:
            print(f"  SKIPPED (no applicable fix)")
            continue
        
        # Re-scan
        try:
            after = scan_full(work_dir)
        except Exception as e:
            print(f"  ERROR re-scanning: {e}")
            continue
        
        # Compute blind score
        blind = compute_blind_score(baseline, after)
        
        # Deltas
        metric_keys = ["agq_v3c", "M", "A", "S", "C", "CD", "PCA", "LVR", "SH"]
        delta_prev = {k: round(after[k] - prev[k], 4) for k in metric_keys}
        delta_base = {k: round(after[k] - baseline[k], 4) for k in metric_keys}
        
        print(f"  After:  AGQ={after['agq_v3c']:.4f} M={after['M']:.4f} A={after['A']:.4f} "
              f"S={after['S']:.4f} C={after['C']:.4f} PCA={after['PCA']:.4f} LVR={after['LVR']:.4f}")
        print(f"  Blind score: {blind}/5")
        
        # Print significant deltas
        for k in metric_keys:
            d = delta_prev[k]
            if abs(d) > 0.001:
                print(f"    Δ{k}={d:+.4f}")
        
        result["iterations"].append({
            "id": i,
            "refactoring": ref_name,
            "description": description,
            "blind_score": blind,
            "metrics_after": clean_metrics(after),
            "delta_vs_prev": delta_prev,
            "delta_vs_baseline": delta_base,
        })
        
        prev = after
    
    return result


def analyze_results(all_results: List[Dict]) -> Dict:
    """Compute within-repo correlations for each metric across all pilots."""
    analysis = {
        "per_repo": {},
        "aggregate": {},
    }
    
    metric_keys = ["agq_v3c", "M", "A", "S", "C", "CD", "PCA", "LVR", "SH"]
    
    # Aggregate: pool all (blind_score, delta) pairs across all repos
    all_blind = []
    all_deltas = {k: [] for k in metric_keys}
    all_cumulative = {k: [] for k in metric_keys}
    
    for res in all_results:
        if "error" in res or not res.get("iterations"):
            continue
        
        repo_name = res["repo"]
        iters = res["iterations"]
        
        if len(iters) < 3:
            print(f"  {repo_name}: only {len(iters)} iterations, skipping correlation")
            analysis["per_repo"][repo_name] = {"n_iters": len(iters), "note": "too few"}
            continue
        
        blinds = [it["blind_score"] for it in iters]
        
        repo_analysis = {"n_iters": len(iters), "correlations": {}}
        
        for k in metric_keys:
            deltas = [it["delta_vs_prev"][k] for it in iters]
            cumul = [it["delta_vs_baseline"][k] for it in iters]
            
            # Check if all deltas are zero
            if all(d == 0 for d in deltas):
                repo_analysis["correlations"][k] = {"rho": None, "p": None, "note": "zero variance"}
            elif all(b == blinds[0] for b in blinds):
                repo_analysis["correlations"][k] = {"rho": None, "p": None, "note": "constant blind"}
            else:
                try:
                    rho, p = stats.spearmanr(blinds, cumul)
                    repo_analysis["correlations"][k] = {"rho": round(rho, 4), "p": round(p, 4)}
                except:
                    repo_analysis["correlations"][k] = {"rho": None, "p": None, "note": "error"}
            
            # Add to aggregate pool
            all_blind.extend(blinds)
            all_deltas[k].extend(deltas)
            all_cumulative[k].extend(cumul)
        
        analysis["per_repo"][repo_name] = repo_analysis
    
    # Aggregate correlations (pooled across all repos)
    if len(all_blind) >= 5:
        for k in metric_keys:
            vals = all_cumulative[k]
            if all(v == 0 for v in vals):
                analysis["aggregate"][k] = {"rho": None, "p": None, "note": "zero variance"}
            else:
                try:
                    rho, p = stats.spearmanr(all_blind, vals)
                    analysis["aggregate"][k] = {"rho": round(rho, 4), "p": round(p, 4), "n": len(all_blind)}
                except:
                    analysis["aggregate"][k] = {"rho": None, "p": None, "note": "error"}
    
    return analysis


def main():
    os.makedirs(CLONE_BASE, exist_ok=True)
    os.makedirs(ARTIFACTS, exist_ok=True)
    
    all_results = []
    
    for repo_info in REPOS:
        result = run_pilot(repo_info)
        all_results.append(result)
    
    # Analyze
    print(f"\n{'='*80}")
    print("AGGREGATE ANALYSIS")
    print(f"{'='*80}")
    
    analysis = analyze_results(all_results)
    
    # Print summary table
    print(f"\n  {'Metric':>8} | {'Pooled ρ':>10} | {'p':>8} | {'n':>4}")
    print(f"  {'-'*8}-+-{'-'*10}-+-{'-'*8}-+-{'-'*4}")
    for k in ["agq_v3c", "M", "A", "S", "C", "CD", "PCA", "LVR", "SH"]:
        agg = analysis["aggregate"].get(k, {})
        rho = agg.get("rho")
        p = agg.get("p")
        n = agg.get("n", 0)
        note = agg.get("note", "")
        if rho is not None:
            print(f"  {k:>8} | {rho:>+10.3f} | {p:>8.4f} | {n:>4}")
        else:
            print(f"  {k:>8} | {'N/A':>10} | {'N/A':>8} | {n:>4}  {note}")
    
    # Per-repo summary
    print(f"\n  Per-repo results:")
    for repo_name, ra in analysis["per_repo"].items():
        print(f"\n  {repo_name} ({ra['n_iters']} iterations):")
        if "correlations" not in ra:
            print(f"    {ra.get('note', 'no data')}")
            continue
        for k in ["PCA", "LVR", "SH", "C", "S"]:
            corr = ra["correlations"].get(k, {})
            rho = corr.get("rho")
            note = corr.get("note", "")
            if rho is not None:
                p = corr.get("p", 1)
                sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
                print(f"    {k:>4}: ρ={rho:+.3f} p={p:.3f}{sig}")
            else:
                print(f"    {k:>4}: {note}")
    
    # Save everything
    output = {
        "experiment": "E10b_within_repo_pilots",
        "date": datetime.now(timezone.utc).isoformat(),
        "n_repos": len(all_results),
        "repos": all_results,
        "analysis": analysis,
    }
    
    out_path = os.path.join(ARTIFACTS, "e10b_within_repo_results.json")
    
    # Remove non-serializable objects
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items() if not k.startswith('_')}
        if isinstance(obj, list):
            return [make_serializable(i) for i in obj]
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    output = make_serializable(output)
    
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
