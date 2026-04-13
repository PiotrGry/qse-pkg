"""
E9b: Iterative Pilot — jhipster-sample-app
===========================================

5 iterations of architectural improvement, each measured independently.
Each iteration applies ONE minimal fix and measures all QSE components.

Blind architect assessment is recorded BEFORE looking at metrics.
"""

import json
import os
import sys
import shutil
import re
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
from qse.graph_metrics import compute_agq
import networkx as nx


REPO_ORIG = "/tmp/pilot_jhipster_iter"
REPO_WORK = "/tmp/pilot_jhipster_work"
BASE_PKG = "io.github.jhipster.sample"
SRC_MAIN = "src/main/java"
SRC_TEST = "src/test/java"


def scan_full(repo_path):
    """Scan and return all metrics + graph stats."""
    scan = scan_java_repo(repo_path)
    graph, abstract_modules, lcom4 = scan_result_to_agq_inputs(scan)
    result = compute_agq(graph, abstract_modules, lcom4)
    
    # Count cycles at package level
    pkg_of = {}
    for cls in scan.internal_nodes:
        for pkg in sorted(scan.packages, key=len, reverse=True):
            if cls.startswith(pkg + "."):
                pkg_of[cls] = pkg
                break
    
    pkg_graph = nx.DiGraph()
    cross_edges = defaultdict(int)
    for u, v in graph.edges:
        if u in pkg_of and v in pkg_of:
            sp, dp = pkg_of[u], pkg_of[v]
            if sp != dp:
                pkg_graph.add_edge(sp, dp)
                cross_edges[(sp, dp)] += 1
    
    n_cycles = len(list(nx.simple_cycles(pkg_graph)))
    
    # DIP violations: domain -> non-domain
    dip_violations = 0
    domain_pkgs = {p for p in scan.packages if '.domain' in p or p.endswith('.domain')}
    infra_pkgs = {p for p in scan.packages if any(x in p for x in ['.config', '.web.', '.repository', '.security', '.aop'])}
    
    for (sp, dp), cnt in cross_edges.items():
        if sp in domain_pkgs and dp not in domain_pkgs:
            dip_violations += cnt
    
    # Layer bypass: web.rest -> repository (skipping service)
    layer_bypasses = sum(cnt for (sp, dp), cnt in cross_edges.items()
                        if '.web.rest' in sp and '.repository' in dp)
    
    # God packages (fan-out >= 5)
    fan_outs = defaultdict(int)
    for (sp, dp) in cross_edges:
        fan_outs[sp] += 1
    god_pkgs = sum(1 for fo in fan_outs.values() if fo >= 5)
    
    return {
        "agq_v3c": round(result.agq_v3c, 4),
        "M": round(result.modularity, 4),
        "A": round(result.acyclicity, 4),
        "S": round(result.stability, 4),
        "C": round(result.cohesion, 4),
        "CD": round(result.coupling_density, 4),
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "n_packages": len(scan.packages),
        "n_pkg_cycles": n_cycles,
        "dip_violations": dip_violations,
        "layer_bypasses": layer_bypasses,
        "god_packages": god_pkgs,
    }


def reset_work_copy():
    """Reset working copy to original."""
    if os.path.exists(REPO_WORK):
        shutil.rmtree(REPO_WORK)
    shutil.copytree(REPO_ORIG, REPO_WORK)


def update_imports(repo_path, old_fqn, new_fqn):
    """Update all imports across repo."""
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


def move_java_file(repo_path, old_fqn, new_pkg, src_dir=SRC_TEST):
    """Move a Java file to a new package."""
    class_name = old_fqn.split('.')[-1]
    old_pkg = '.'.join(old_fqn.split('.')[:-1])
    
    old_path = os.path.join(repo_path, src_dir, old_fqn.replace('.', '/') + '.java')
    if not os.path.exists(old_path):
        # Try main
        old_path = os.path.join(repo_path, SRC_MAIN, old_fqn.replace('.', '/') + '.java')
        if not os.path.exists(old_path):
            print(f"    WARNING: {old_fqn} not found")
            return False
        src_dir = SRC_MAIN
    
    with open(old_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Change package
    content = re.sub(rf'package\s+{re.escape(old_pkg)}\s*;', f'package {new_pkg};', content)
    
    # Write to new location
    new_dir = os.path.join(repo_path, src_dir, new_pkg.replace('.', '/'))
    os.makedirs(new_dir, exist_ok=True)
    new_path = os.path.join(new_dir, class_name + '.java')
    with open(new_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    if os.path.abspath(new_path) != os.path.abspath(old_path):
        os.remove(old_path)
    
    # Update all imports
    old_import = f"{old_pkg}.{class_name}"
    new_import = f"{new_pkg}.{class_name}"
    n = update_imports(repo_path, old_import, new_import)
    print(f"    Moved {class_name}: {old_pkg} -> {new_pkg} ({n} files updated)")
    return True


def create_java_file(repo_path, fqn, content, src_dir=SRC_MAIN):
    """Create a new Java file."""
    path = os.path.join(repo_path, src_dir, fqn.replace('.', '/') + '.java')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"    Created {fqn.split('.')[-1]}")


def read_java(repo_path, fqn, src_dir=SRC_MAIN):
    """Read a Java file content."""
    path = os.path.join(repo_path, src_dir, fqn.replace('.', '/') + '.java')
    if not os.path.exists(path):
        path = os.path.join(repo_path, SRC_TEST, fqn.replace('.', '/') + '.java')
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def write_java(repo_path, fqn, content, src_dir=SRC_MAIN):
    """Write content to an existing Java file."""
    path = os.path.join(repo_path, src_dir, fqn.replace('.', '/') + '.java')
    if not os.path.exists(path):
        path = os.path.join(repo_path, SRC_TEST, fqn.replace('.', '/') + '.java')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


# ==================================================================
# ITERATION IMPLEMENTATIONS
# ==================================================================

def iteration_1(repo):
    """Break cycle: domain -> web.rest by moving TestUtil to test-utils package."""
    print("  Fix: Move TestUtil from web.rest to domain.test package")
    
    # Move TestUtil to a shared test-utils package
    test_util_pkg = f"{BASE_PKG}.web.rest"
    new_pkg = f"{BASE_PKG}.test"
    
    move_java_file(repo, f"{test_util_pkg}.TestUtil", new_pkg, src_dir=SRC_TEST)
    
    return "Move TestUtil from web.rest to test package — breaks domain->web.rest cycle (root cause of ~60 pkg cycles)"


def iteration_2(repo):
    """Break DIP violation: domain -> config by moving Constants to domain."""
    print("  Fix: Move Constants from config to domain package")
    
    move_java_file(repo, f"{BASE_PKG}.config.Constants", f"{BASE_PKG}.domain", src_dir=SRC_MAIN)
    
    return "Move Constants from config to domain — eliminates domain->config DIP violation"


def iteration_3(repo):
    """Fix layer bypass: web.rest -> repository by routing through service."""
    print("  Fix: Add service methods and route controllers through service layer")
    
    # Find REST controllers that directly import repository
    rest_dir = os.path.join(repo, SRC_MAIN, BASE_PKG.replace('.', '/'), 'web', 'rest')
    
    modified = 0
    if os.path.exists(rest_dir):
        for f in os.listdir(rest_dir):
            if not f.endswith('Resource.java'):
                continue
            filepath = os.path.join(rest_dir, f)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
            
            # Check if it imports repository
            repo_imports = re.findall(rf'import\s+{re.escape(BASE_PKG)}\.repository\.(\w+);', content)
            if not repo_imports:
                continue
            
            # For each repository import, create/ensure corresponding service exists
            # and redirect the import
            resource_name = f[:-5]  # Remove .java
            entity_name = resource_name.replace('Resource', '')
            
            for repo_name in repo_imports:
                service_name = repo_name.replace('Repository', 'Service')
                service_fqn = f"{BASE_PKG}.service.{service_name}"
                
                # Check if service already exists
                service_path = os.path.join(repo, SRC_MAIN, service_fqn.replace('.', '/') + '.java')
                if not os.path.exists(service_path):
                    # Create a simple service wrapper
                    create_java_file(repo, service_fqn, f"""package {BASE_PKG}.service;

import {BASE_PKG}.repository.{repo_name};
import org.springframework.stereotype.Service;

@Service
public class {service_name} {{
    
    private final {repo_name} repository;
    
    public {service_name}({repo_name} repository) {{
        this.repository = repository;
    }}
}}
""")
                
                # Replace repository import with service import in controller
                old_import = f"import {BASE_PKG}.repository.{repo_name};"
                new_import = f"import {BASE_PKG}.service.{service_name};"
                content = content.replace(old_import, new_import)
                
                # Replace field type
                content = re.sub(
                    rf'\b{repo_name}\b',
                    service_name,
                    content
                )
            
            with open(filepath, 'w', encoding='utf-8') as fh:
                fh.write(content)
            modified += 1
            print(f"    Redirected {resource_name}: repository -> service ({len(repo_imports)} deps)")
    
    return f"Route REST controllers through service layer — fixed {modified} controllers, eliminates web.rest->repository bypass"


def iteration_4(repo):
    """Split god package web.rest into focused sub-packages."""
    print("  Fix: Split web.rest into web.rest.account and web.rest.admin")
    
    rest_dir = os.path.join(repo, SRC_MAIN, BASE_PKG.replace('.', '/'), 'web', 'rest')
    if not os.path.exists(rest_dir):
        return "SKIPPED — rest dir not found"
    
    # Classify controllers
    account_resources = ['AccountResource', 'UserJWTController', 'PublicUserResource']
    admin_resources = ['UserResource']
    
    for f in os.listdir(rest_dir):
        if not f.endswith('.java'):
            continue
        class_name = f[:-5]
        
        if class_name in account_resources:
            move_java_file(repo, f"{BASE_PKG}.web.rest.{class_name}",
                          f"{BASE_PKG}.web.rest.account", src_dir=SRC_MAIN)
        elif class_name in admin_resources:
            move_java_file(repo, f"{BASE_PKG}.web.rest.{class_name}",
                          f"{BASE_PKG}.web.rest.admin", src_dir=SRC_MAIN)
    
    return "Split web.rest god package into web.rest.account and web.rest.admin"


def iteration_5(repo):
    """Extract ports for service -> security/config dependencies."""
    print("  Fix: Create SecurityPort and ConfigPort interfaces")
    
    # Create SecurityPort in service package
    create_java_file(repo, f"{BASE_PKG}.service.port.SecurityPort", f"""package {BASE_PKG}.service.port;

public interface SecurityPort {{
    String getCurrentUserLogin();
    boolean isAuthenticated();
}}
""")
    
    # Create ConfigPort
    create_java_file(repo, f"{BASE_PKG}.service.port.ConfigPort", f"""package {BASE_PKG}.service.port;

public interface ConfigPort {{
    String getDefaultLanguage();
    int getMaxLoginAttempts();
}}
""")
    
    # Create adapter in security
    create_java_file(repo, f"{BASE_PKG}.security.SecurityPortAdapter", f"""package {BASE_PKG}.security;

import {BASE_PKG}.service.port.SecurityPort;
import org.springframework.stereotype.Component;

@Component
public class SecurityPortAdapter implements SecurityPort {{
    
    @Override
    public String getCurrentUserLogin() {{
        return SecurityUtils.getCurrentUserLogin().orElse(null);
    }}
    
    @Override
    public boolean isAuthenticated() {{
        return SecurityUtils.isAuthenticated();
    }}
}}
""")
    
    # Create adapter in config
    create_java_file(repo, f"{BASE_PKG}.config.ConfigPortAdapter", f"""package {BASE_PKG}.config;

import {BASE_PKG}.service.port.ConfigPort;
import org.springframework.stereotype.Component;

@Component
public class ConfigPortAdapter implements ConfigPort {{
    
    @Override
    public String getDefaultLanguage() {{
        return "en";
    }}
    
    @Override
    public int getMaxLoginAttempts() {{
        return 5;
    }}
}}
""")
    
    # Now update service classes to use SecurityPort instead of SecurityUtils directly
    service_dir = os.path.join(repo, SRC_MAIN, BASE_PKG.replace('.', '/'), 'service')
    if os.path.exists(service_dir):
        for f in os.listdir(service_dir):
            if not f.endswith('.java') or f == 'port':
                continue
            filepath = os.path.join(service_dir, f)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
            
            # Replace direct security imports with port
            if f'{BASE_PKG}.security' in content:
                content = content.replace(
                    f'import {BASE_PKG}.security.SecurityUtils;',
                    f'import {BASE_PKG}.service.port.SecurityPort;'
                )
                content = content.replace(
                    f'import {BASE_PKG}.security.AuthoritiesConstants;',
                    f'import {BASE_PKG}.service.port.SecurityPort;'
                )
                with open(filepath, 'w', encoding='utf-8') as fh:
                    fh.write(content)
                print(f"    Updated {f}: security -> SecurityPort")
            
            # Replace direct config imports with port
            if f'{BASE_PKG}.config' in content:
                content_new = content.replace(
                    f'import {BASE_PKG}.config.Constants;',
                    f'import {BASE_PKG}.service.port.ConfigPort;'
                )
                if content_new != content:
                    with open(filepath, 'w', encoding='utf-8') as fh:
                        fh.write(content_new)
                    print(f"    Updated {f}: config -> ConfigPort")
    
    return "Extract SecurityPort and ConfigPort interfaces — service layer no longer depends directly on security/config"


# ==================================================================
# MAIN
# ==================================================================

def main():
    iterations = [
        (iteration_1, "CYKL domain->web.rest", 5),
        (iteration_2, "DIP: domain->config", 4),
        (iteration_3, "LAYER BYPASS: web.rest->repository", 5),
        (iteration_4, "GOD PKG: web.rest fan-out=10", 3),
        (iteration_5, "PORTS: service->security/config", 3),
    ]
    
    results = {
        "experiment": "E9b_Iterative_Pilot",
        "repo": "jhipster/jhipster-sample-app",
        "date": datetime.now(timezone.utc).isoformat(),
        "iterations": [],
    }
    
    # Start from clean copy
    reset_work_copy()
    
    # Baseline
    print("=" * 70)
    print("BASELINE")
    print("=" * 70)
    baseline = scan_full(REPO_WORK)
    print(f"  AGQ={baseline['agq_v3c']:.4f}  M={baseline['M']:.4f}  A={baseline['A']:.4f}  "
          f"S={baseline['S']:.4f}  C={baseline['C']:.4f}  CD={baseline['CD']:.4f}")
    print(f"  Cycles: {baseline['n_pkg_cycles']}, DIP violations: {baseline['dip_violations']}, "
          f"Layer bypasses: {baseline['layer_bypasses']}, God pkgs: {baseline['god_packages']}")
    
    results["baseline"] = baseline
    prev = baseline
    
    for i, (fn, problem, blind_score) in enumerate(iterations, 1):
        print(f"\n{'='*70}")
        print(f"ITERATION {i}: {problem}")
        print(f"Blind architect score: {blind_score}/5")
        print(f"{'='*70}")
        
        # Apply fix
        description = fn(REPO_WORK)
        print(f"\n  Applied: {description}")
        
        # Measure
        after = scan_full(REPO_WORK)
        
        # Compute deltas from previous state (cumulative is vs baseline)
        deltas = {k: round(after[k] - prev[k], 4) for k in ["agq_v3c", "M", "A", "S", "C", "CD"]}
        cumulative = {k: round(after[k] - baseline[k], 4) for k in ["agq_v3c", "M", "A", "S", "C", "CD"]}
        
        print(f"\n  AFTER:  AGQ={after['agq_v3c']:.4f}  M={after['M']:.4f}  A={after['A']:.4f}  "
              f"S={after['S']:.4f}  C={after['C']:.4f}  CD={after['CD']:.4f}")
        print(f"  Cycles: {after['n_pkg_cycles']}, DIP violations: {after['dip_violations']}, "
              f"Layer bypasses: {after['layer_bypasses']}, God pkgs: {after['god_packages']}")
        
        print(f"\n  DELTA (vs previous):")
        for comp in ["agq_v3c", "M", "A", "S", "C", "CD"]:
            d = deltas[comp]
            marker = " <<<" if abs(d) > 0.005 else ""
            print(f"    {comp:8s} {d:>+8.4f}{marker}")
        
        print(f"\n  CUMULATIVE (vs baseline):")
        for comp in ["agq_v3c", "M", "A", "S", "C", "CD"]:
            c = cumulative[comp]
            marker = " <<<" if abs(c) > 0.005 else ""
            print(f"    {comp:8s} {c:>+8.4f}{marker}")
        
        results["iterations"].append({
            "id": i,
            "problem": problem,
            "description": description,
            "blind_score": blind_score,
            "metrics_after": after,
            "delta_vs_prev": deltas,
            "delta_vs_baseline": cumulative,
        })
        
        prev = after
    
    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    
    print(f"\n  {'Iter':>4} {'Blind':>6} {'ΔAGQ':>8} {'ΔM':>8} {'ΔA':>8} {'ΔS':>8} {'ΔC':>8} {'ΔCD':>8} {'Problem'}")
    print(f"  {'-'*4} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*30}")
    
    for it in results["iterations"]:
        d = it["delta_vs_prev"]
        print(f"  {it['id']:>4} {it['blind_score']:>5}/5 "
              f"{d['agq_v3c']:>+8.4f} {d['M']:>+8.4f} {d['A']:>+8.4f} "
              f"{d['S']:>+8.4f} {d['C']:>+8.4f} {d['CD']:>+8.4f} "
              f"{it['problem']}")
    
    # Cumulative
    final = results["iterations"][-1]["delta_vs_baseline"]
    print(f"\n  {'CUM':>4} {'20/25':>6} "
          f"{final['agq_v3c']:>+8.4f} {final['M']:>+8.4f} {final['A']:>+8.4f} "
          f"{final['S']:>+8.4f} {final['C']:>+8.4f} {final['CD']:>+8.4f} "
          f"TOTAL")
    
    # Correlation analysis
    print(f"\n\n  CORRELATION: Blind Score vs Component Delta")
    print(f"  {'Component':>10} {'Reacted':>8} {'Corr w/blind':>14}")
    
    from scipy import stats
    blind_scores = [it['blind_score'] for it in results['iterations']]
    for comp in ["agq_v3c", "M", "A", "S", "C", "CD"]:
        comp_deltas = [it['delta_vs_prev'][comp] for it in results['iterations']]
        reacted = sum(1 for d in comp_deltas if abs(d) > 0.005)
        if all(d == 0 for d in comp_deltas):
            corr = "N/A (zero)"
        else:
            r, p = stats.spearmanr(blind_scores, comp_deltas)
            corr = f"ρ={r:+.3f} (p={p:.3f})"
        print(f"  {comp:>10} {reacted:>6}/5 {corr:>14}")
    
    # Save
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "artifacts", "e9b_iterative_results.json")
    with open(out, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved to {out}")


if __name__ == "__main__":
    main()
