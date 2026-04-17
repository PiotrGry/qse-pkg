"""
E9: Run all 5 pilots — before/after refactoring sensitivity test.

Each pilot:
  1. Scan BEFORE (unchanged repo)
  2. Apply minimal refactoring (Java file moves + import rewrites)
  3. Scan AFTER
  4. Record deltas
"""

import json
import os
import sys
import shutil
import glob
import re
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
from qse.graph_metrics import compute_agq


def scan_metrics(repo_path):
    """Full metric scan."""
    scan = scan_java_repo(repo_path)
    graph, abstract_modules, lcom4 = scan_result_to_agq_inputs(scan)
    result = compute_agq(graph, abstract_modules, lcom4)
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
    }


def find_java_files(root, package_prefix):
    """Find all .java files in a package directory."""
    results = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.endswith('.java'):
                filepath = os.path.join(dirpath, f)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
                # Check if this file belongs to the package
                pkg_match = re.search(r'package\s+([\w.]+)\s*;', content)
                if pkg_match and pkg_match.group(1).startswith(package_prefix):
                    results.append((filepath, content, pkg_match.group(1)))
    return results


def move_class_to_package(repo_path, class_fqn, new_package, src_dirs=None):
    """
    Move a Java class to a new package:
    1. Find the .java file
    2. Change its package declaration
    3. Update all imports across the repo
    """
    if src_dirs is None:
        src_dirs = ['src/main/java', 'src/test/java', 'src']
    
    class_simple = class_fqn.split('.')[-1]
    old_package = '.'.join(class_fqn.split('.')[:-1])
    
    # Find the source file
    source_file = None
    for sd in src_dirs:
        candidate = os.path.join(repo_path, sd, class_fqn.replace('.', '/') + '.java')
        if os.path.exists(candidate):
            source_file = candidate
            break
    
    if not source_file:
        print(f"    WARNING: Could not find {class_fqn}")
        return False
    
    # Read content
    with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Change package declaration
    content = re.sub(
        rf'package\s+{re.escape(old_package)}\s*;',
        f'package {new_package};',
        content
    )
    
    # Create new directory and write
    new_rel_path = new_package.replace('.', '/')
    for sd in src_dirs:
        new_dir = os.path.join(repo_path, sd, new_rel_path)
        if os.path.exists(os.path.join(repo_path, sd)):
            os.makedirs(new_dir, exist_ok=True)
            new_file = os.path.join(new_dir, class_simple + '.java')
            with open(new_file, 'w', encoding='utf-8') as f:
                f.write(content)
            # Remove old file
            if os.path.abspath(new_file) != os.path.abspath(source_file):
                os.remove(source_file)
            break
    
    # Update all imports across repo
    old_import = f'{old_package}.{class_simple}'
    new_import = f'{new_package}.{class_simple}'
    update_imports_across_repo(repo_path, old_import, new_import)
    
    print(f"    Moved {class_simple}: {old_package} -> {new_package}")
    return True


def update_imports_across_repo(repo_path, old_fqn, new_fqn):
    """Update all import statements in the repo."""
    count = 0
    for dirpath, _, filenames in os.walk(repo_path):
        if '.git' in dirpath:
            continue
        for f in filenames:
            if not f.endswith('.java'):
                continue
            filepath = os.path.join(dirpath, f)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
            if old_fqn in content:
                new_content = content.replace(old_fqn, new_fqn)
                with open(filepath, 'w', encoding='utf-8') as fh:
                    fh.write(new_content)
                count += 1
    return count


def create_interface(repo_path, interface_fqn, method_signatures, src_dir='src/main/java'):
    """Create a new Java interface file."""
    package = '.'.join(interface_fqn.split('.')[:-1])
    name = interface_fqn.split('.')[-1]
    
    methods = '\n'.join(f'    {sig};' for sig in method_signatures)
    content = f"""package {package};

public interface {name} {{
{methods}
}}
"""
    
    dir_path = os.path.join(repo_path, src_dir, package.replace('.', '/'))
    os.makedirs(dir_path, exist_ok=True)
    filepath = os.path.join(dir_path, name + '.java')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"    Created interface: {interface_fqn}")
    return True


def add_implements(repo_path, class_fqn, interface_simple, interface_fqn, src_dir='src/main/java'):
    """Add 'implements InterfaceName' to a class and add import."""
    filepath = os.path.join(repo_path, src_dir, class_fqn.replace('.', '/') + '.java')
    if not os.path.exists(filepath):
        print(f"    WARNING: {filepath} not found")
        return False
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Add import after package declaration
    package_pkg = '.'.join(class_fqn.split('.')[:-1])
    interface_pkg = '.'.join(interface_fqn.split('.')[:-1])
    if package_pkg != interface_pkg:
        content = re.sub(
            r'(package\s+[\w.]+\s*;)',
            rf'\1\n\nimport {interface_fqn};',
            content,
            count=1
        )
    
    # Add implements
    class_simple = class_fqn.split('.')[-1]
    if 'implements' in content:
        content = re.sub(
            rf'(class\s+{class_simple}\s+.*?implements\s+)',
            rf'\1{interface_simple}, ',
            content,
            count=1
        )
    else:
        content = re.sub(
            rf'(class\s+{class_simple}(?:\s+extends\s+\w+)?)\s*\{{',
            rf'\1 implements {interface_simple} {{',
            content,
            count=1
        )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"    {class_fqn.split('.')[-1]} implements {interface_simple}")
    return True


# ==================================================================
# PILOT REFACTORINGS
# ==================================================================

def pilot_jhipster(repo_path):
    """
    JHipster: DIP — domain should NOT depend on config/rest.
    
    Problem: domain -> config, domain -> rest (violations!)
    Fix: Extract interfaces in domain for what config/rest need,
         move the concrete dependencies behind port interfaces.
    
    Minimal: Move domain classes that import config into a separate
    'infrastructure' package, breaking the domain->config dependency.
    """
    info = {
        "name": "jhipster-sample-app",
        "refactoring_type": "DIP: break domain→config dependency",
        "description": "Domain package imports from config (DIP violation). "
                       "Extract domain port interfaces and move infrastructure "
                       "coupling to a new 'infrastructure' package.",
    }
    
    base_pkg = "io.github.jhipster.sample"
    
    # 1. Create port interfaces in domain
    create_interface(
        repo_path,
        f"{base_pkg}.domain.port.DateTimeProvider",
        ["java.time.Instant now()"],
    )
    create_interface(
        repo_path,
        f"{base_pkg}.domain.port.EntityIdGenerator",
        ["String generateId()"],
    )
    
    # 2. Create infrastructure package with implementations
    infra_pkg = f"{base_pkg}.infrastructure"
    infra_dir = os.path.join(repo_path, 'src/main/java', infra_pkg.replace('.', '/'))
    os.makedirs(infra_dir, exist_ok=True)
    
    # Create DateTimeProviderImpl
    with open(os.path.join(infra_dir, 'SystemDateTimeProvider.java'), 'w') as f:
        f.write(f"""package {infra_pkg};

import {base_pkg}.domain.port.DateTimeProvider;
import java.time.Instant;

public class SystemDateTimeProvider implements DateTimeProvider {{
    @Override
    public Instant now() {{
        return Instant.now();
    }}
}}
""")
    print(f"    Created {infra_pkg}.SystemDateTimeProvider")
    
    # 3. Move some domain classes that have wrong dependencies
    # The key DIP violation is domain -> rest. Let's check what's there.
    # domain/BankAccount.java, domain/Label.java, domain/Operation.java 
    # are pure entities. The violation might be from generated code.
    # Instead, let's move the config-dependent classes out of domain.
    
    # Find domain classes that import config
    domain_dir = os.path.join(repo_path, 'src/main/java', 
                              base_pkg.replace('.', '/'), 'domain')
    if os.path.exists(domain_dir):
        for f in os.listdir(domain_dir):
            if f.endswith('.java'):
                filepath = os.path.join(domain_dir, f)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
                if '.config.' in content or '.rest.' in content:
                    class_name = f[:-5]  # remove .java
                    # Move to infrastructure
                    move_class_to_package(
                        repo_path,
                        f"{base_pkg}.domain.{class_name}",
                        infra_pkg
                    )
    
    return info


def pilot_piggymetrics(repo_path):
    """
    Piggymetrics: Break cross-service circular dependencies.
    
    It's a microservices project with account/auth/notification/statistics services.
    Each service has its own domain/service/controller/repository packages.
    
    Minimal: Extract shared DTOs into a shared kernel package,
    reducing cross-service coupling.
    """
    info = {
        "name": "piggymetrics",
        "refactoring_type": "Extract shared kernel",
        "description": "Multiple services share similar domain concepts. "
                       "Extract common DTOs/interfaces into a shared kernel package.",
    }
    
    # Find all service base paths
    src_root = os.path.join(repo_path, 'src/main/java')
    if not os.path.exists(src_root):
        # Piggymetrics has multi-module structure
        # Look for module directories
        for subdir in os.listdir(repo_path):
            module_path = os.path.join(repo_path, subdir)
            if os.path.isdir(module_path) and os.path.exists(
                    os.path.join(module_path, 'src/main/java')):
                # This is a module, refactor within it
                pass
    
    # Actually, let's look at the structure
    base_pkg = "com.piggymetrics"
    
    # Create shared kernel
    # Find any module's src dir
    module_dirs = []
    for subdir in os.listdir(repo_path):
        mod_src = os.path.join(repo_path, subdir, 'src/main/java')
        if os.path.exists(mod_src):
            module_dirs.append((subdir, mod_src))
    
    if not module_dirs:
        # Single src structure
        module_dirs = [("main", os.path.join(repo_path, 'src/main/java'))]
    
    print(f"    Found modules: {[m[0] for m in module_dirs]}")
    
    # For each service module, extract repository interfaces
    for module_name, src_dir in module_dirs:
        # Find service classes that directly depend on repository
        service_files = []
        for dirpath, _, files in os.walk(src_dir):
            for f in files:
                if f.endswith('.java'):
                    fp = os.path.join(dirpath, f)
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as fh:
                        content = fh.read()
                    pkg_m = re.search(r'package\s+([\w.]+);', content)
                    if pkg_m and '.service' in pkg_m.group(1) and 'Impl' not in f:
                        service_files.append((fp, content, pkg_m.group(1)))
        
        # For each service, if it directly imports from repository package,
        # create a port interface
        for fp, content, pkg in service_files:
            if '.repository' in content and 'import' in content:
                # Find repository imports
                repo_imports = re.findall(
                    r'import\s+([\w.]+\.repository\.(\w+));', content
                )
                if repo_imports:
                    # Create port interface in service package
                    class_name = os.path.basename(fp)[:-5]
                    port_pkg = pkg.replace('.service', '.service.port')
                    
                    for full_import, repo_name in repo_imports[:2]:  # limit
                        port_name = f"{repo_name}Port"
                        create_interface(
                            repo_path,
                            f"{port_pkg}.{port_name}",
                            [f"Object findById(String id)", 
                             f"Object save(Object entity)"],
                            src_dir=os.path.relpath(src_dir, repo_path)
                        )
                    break  # One per module is enough for minimal
    
    return info


def pilot_mall_learning(repo_path):
    """
    Mall-learning: Break god packages + extract domain layer.
    
    Problem: controller imports directly from model (skipping service layer),
    impl depends on everything (god package pattern).
    
    Minimal: Move domain models from 'model' into proper 'domain.model' package,
    create repository interfaces in domain layer.
    """
    info = {
        "name": "mall-learning",
        "refactoring_type": "Break god packages, extract domain layer",
        "description": "Controller imports directly from model (bypasses service). "
                       "impl package depends on 6+ other packages (god package). "
                       "Extract domain.model and domain.repository packages.",
    }
    
    base_pkg = "com.macro.mall"
    src_root = None
    
    # Find src root (could be in submodule)
    for dirpath, dirs, files in os.walk(repo_path):
        if dirpath.endswith('src/main/java'):
            src_root = dirpath
            break
    
    if not src_root:
        print("    WARNING: Could not find src/main/java")
        return info
    
    # Find model packages and create domain.model structure
    model_files = []
    for dirpath, _, files in os.walk(src_root):
        for f in files:
            if f.endswith('.java'):
                fp = os.path.join(dirpath, f)
                with open(fp, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
                pkg_m = re.search(r'package\s+([\w.]+);', content)
                if pkg_m and pkg_m.group(1).endswith('.model'):
                    model_files.append((fp, content, pkg_m.group(1), f[:-5]))
    
    # Move first few model classes to domain.model
    moved = 0
    for fp, content, old_pkg, class_name in model_files[:5]:
        new_pkg = old_pkg.replace('.model', '.domain.model')
        # Rewrite package declaration
        new_content = content.replace(f'package {old_pkg};', f'package {new_pkg};')
        
        # Create new dir
        new_dir = os.path.join(src_root, new_pkg.replace('.', '/'))
        os.makedirs(new_dir, exist_ok=True)
        
        # Write new file
        new_fp = os.path.join(new_dir, class_name + '.java')
        with open(new_fp, 'w', encoding='utf-8') as fh:
            fh.write(new_content)
        
        # Remove old file
        if os.path.abspath(new_fp) != os.path.abspath(fp):
            os.remove(fp)
        
        # Update imports
        old_fqn = f"{old_pkg}.{class_name}"
        new_fqn = f"{new_pkg}.{class_name}"
        n = update_imports_across_repo(repo_path, old_fqn, new_fqn)
        print(f"    Moved {class_name}: {old_pkg} -> {new_pkg} ({n} imports updated)")
        moved += 1
    
    # Create repository interfaces in domain
    if model_files:
        domain_base = model_files[0][2].replace('.model', '.domain')
        repo_pkg = f"{domain_base}.repository"
        for _, _, _, class_name in model_files[:3]:
            create_interface(
                repo_path,
                f"{repo_pkg}.{class_name}Repository",
                [f"{class_name} findById(Long id)",
                 f"void save({class_name} entity)",
                 f"void delete(Long id)"],
                src_dir=os.path.relpath(src_root, repo_path)
            )
    
    return info


def pilot_javalin(repo_path):
    """
    Javalin: Extract plugin interface from core.
    
    Problem: javalin core depends on apibuilder, http, testing, websocket.
    Core should define interfaces, extensions should implement them.
    
    Minimal: Create Plugin interface in core, make apibuilder implement it.
    """
    info = {
        "name": "javalin",
        "refactoring_type": "Extract plugin interfaces from core",
        "description": "Core package depends on apibuilder, http, testing, websocket. "
                       "Extract Plugin/Extension interfaces so core defines contracts, "
                       "not implementations.",
    }
    
    # Find src root
    src_root = None
    for dirpath, dirs, files in os.walk(repo_path):
        if dirpath.endswith('src/main/java') or dirpath.endswith('src/main/kotlin'):
            src_root = dirpath
            break
    
    if not src_root:
        # Javalin may use kotlin/mixed sources
        for dirpath, dirs, files in os.walk(repo_path):
            if 'javalin' in dirpath and 'io' in dirpath:
                src_root = dirpath
                break
    
    base_pkg = "io.javalin"
    
    # Search all java/kotlin files
    all_java = []
    for dirpath, _, files in os.walk(repo_path):
        if '.git' in dirpath:
            continue
        for f in files:
            if f.endswith('.java') or f.endswith('.kt'):
                all_java.append(os.path.join(dirpath, f))
    
    print(f"    Found {len(all_java)} source files")
    
    # Find any src/main/java directory  
    src_dirs = set()
    for fp in all_java:
        if 'src/main/java' in fp:
            idx = fp.index('src/main/java')
            src_dirs.add(fp[:idx + len('src/main/java')])
    
    if src_dirs:
        src_root = list(src_dirs)[0]
    else:
        # Create in first available location
        src_root = os.path.join(repo_path, 'src/main/java')
        os.makedirs(src_root, exist_ok=True)
    
    # Create Plugin interface in core
    create_interface(
        repo_path,
        f"{base_pkg}.plugin.Plugin",
        ["void apply(Object app)",
         "String name()"],
        src_dir=os.path.relpath(src_root, repo_path)
    )
    
    create_interface(
        repo_path,
        f"{base_pkg}.plugin.PluginRegistry",
        [f"void register({base_pkg}.plugin.Plugin plugin)",
         f"{base_pkg}.plugin.Plugin get(String name)"],
        src_dir=os.path.relpath(src_root, repo_path)
    )
    
    # Create Extension point interface
    create_interface(
        repo_path,
        f"{base_pkg}.core.Extension",
        ["void init()",
         "void destroy()"],
        src_dir=os.path.relpath(src_root, repo_path)
    )
    
    return info


def pilot_eladmin(repo_path):
    """
    Eladmin: Extract service boundary interfaces.
    
    Problem: rest packages directly depend on impl packages,
    service packages depend on domain + dto + utils.
    Heavy cross-cutting dependencies.
    
    Minimal: Create service interfaces between rest and impl layers.
    Move utils dependencies behind an abstraction.
    """
    info = {
        "name": "eladmin",
        "refactoring_type": "Extract service boundary interfaces",
        "description": "Rest depends directly on impl. Multiple cross-cutting deps. "
                       "Extract service interfaces between rest→impl, "
                       "create utility abstractions.",
    }
    
    # Find all src roots (multi-module project)
    src_roots = []
    for dirpath, dirs, files in os.walk(repo_path):
        if dirpath.endswith('src/main/java'):
            src_roots.append(dirpath)
    
    print(f"    Found {len(src_roots)} source roots")
    
    base_pkg = "me.zhengjie"
    
    for src_root in src_roots:
        # Find service impl classes
        for dirpath, _, files in os.walk(src_root):
            for f in files:
                if f.endswith('.java') and 'ServiceImpl' in f:
                    fp = os.path.join(dirpath, f)
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as fh:
                        content = fh.read()
                    
                    pkg_m = re.search(r'package\s+([\w.]+);', content)
                    if not pkg_m:
                        continue
                    
                    impl_pkg = pkg_m.group(1)
                    class_name = f[:-5]
                    
                    # Find methods to extract to interface
                    methods = re.findall(
                        r'public\s+(\w[\w<>,\s]*?)\s+(\w+)\s*\(([^)]*)\)',
                        content
                    )
                    
                    if methods and '.impl' in impl_pkg:
                        # Create interface in service (non-impl) package
                        svc_pkg = impl_pkg.replace('.impl', '')
                        iface_name = class_name.replace('Impl', '')
                        
                        sigs = [f"{ret} {name}({params})" 
                                for ret, name, params in methods[:5]]
                        
                        create_interface(
                            repo_path,
                            f"{svc_pkg}.{iface_name}",
                            sigs,
                            src_dir=os.path.relpath(src_root, repo_path)
                        )
                        
                        # Make impl implement the interface
                        add_implements(
                            repo_path,
                            f"{impl_pkg}.{class_name}",
                            iface_name,
                            f"{svc_pkg}.{iface_name}",
                            src_dir=os.path.relpath(src_root, repo_path)
                        )
                        break  # One per module is enough
    
    return info


# ==================================================================
# MAIN EXECUTION
# ==================================================================

def run_pilot(name, repo_url, refactoring_fn):
    """Run a single pilot: clone, scan before, refactor, scan after."""
    repo_path = f"/tmp/pilot_{name}"
    
    print(f"\n{'='*70}")
    print(f"  PILOT: {name}")
    print(f"{'='*70}")
    
    # Make a working copy for the refactored version
    refactored_path = f"/tmp/pilot_{name}_refactored"
    if os.path.exists(refactored_path):
        shutil.rmtree(refactored_path)
    shutil.copytree(repo_path, refactored_path)
    
    # 1. Scan BEFORE
    print(f"\n  [1/3] Scanning BEFORE...")
    before = scan_metrics(repo_path)
    print(f"    AGQ={before['agq_v3c']:.4f}  M={before['M']:.4f}  A={before['A']:.4f}  "
          f"S={before['S']:.4f}  C={before['C']:.4f}  CD={before['CD']:.4f}")
    
    # 2. Apply refactoring
    print(f"\n  [2/3] Applying refactoring...")
    info = refactoring_fn(refactored_path)
    
    # 3. Scan AFTER
    print(f"\n  [3/3] Scanning AFTER...")
    after = scan_metrics(refactored_path)
    print(f"    AGQ={after['agq_v3c']:.4f}  M={after['M']:.4f}  A={after['A']:.4f}  "
          f"S={after['S']:.4f}  C={after['C']:.4f}  CD={after['CD']:.4f}")
    
    # 4. Compute deltas
    print(f"\n  DELTAS:")
    deltas = {}
    for comp in ["agq_v3c", "M", "A", "S", "C", "CD"]:
        d = after[comp] - before[comp]
        deltas[comp] = round(d, 4)
        pct = (d / before[comp] * 100) if before[comp] > 0 else 0
        marker = " <<<" if abs(d) > 0.005 else ""
        print(f"    {comp:8s}  {before[comp]:>8.4f} -> {after[comp]:>8.4f}  "
              f"delta={d:>+8.4f}  ({pct:>+6.1f}%){marker}")
    
    # Structural changes
    print(f"\n  STRUCTURAL:")
    print(f"    Nodes:    {before['nodes']} -> {after['nodes']}  (delta={after['nodes']-before['nodes']})")
    print(f"    Edges:    {before['edges']} -> {after['edges']}  (delta={after['edges']-before['edges']})")
    print(f"    Packages: {before['n_packages']} -> {after['n_packages']}  (delta={after['n_packages']-before['n_packages']})")
    
    # Cleanup
    shutil.rmtree(refactored_path)
    
    return {
        "name": name,
        "refactoring_type": info["refactoring_type"],
        "description": info["description"],
        "before": before,
        "after": after,
        "deltas": deltas,
    }


def main():
    pilots = [
        ("jhipster", "https://github.com/jhipster/jhipster-sample-app", pilot_jhipster),
        ("piggymetrics", "https://github.com/sqshq/piggymetrics", pilot_piggymetrics),
        ("mall-learning", "https://github.com/macrozheng/mall-learning", pilot_mall_learning),
        ("javalin", "https://github.com/javalin/javalin", pilot_javalin),
        ("eladmin", "https://github.com/elunez/eladmin", pilot_eladmin),
    ]
    
    results = {
        "experiment": "E9_Pilot_Battery",
        "date": datetime.now(timezone.utc).isoformat(),
        "pilots": [],
    }
    
    for name, url, fn in pilots:
        try:
            result = run_pilot(name, url, fn)
            results["pilots"].append(result)
        except Exception as e:
            print(f"\n  ERROR in {name}: {e}")
            import traceback
            traceback.print_exc()
            results["pilots"].append({
                "name": name,
                "error": str(e),
            })
    
    # Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"\n  {'Name':20s} {'AGQ':>8s} {'M':>8s} {'A':>8s} {'S':>8s} {'C':>8s} {'CD':>8s}")
    print(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for p in results["pilots"]:
        if "error" in p:
            print(f"  {p['name']:20s} ERROR: {p['error'][:50]}")
        else:
            d = p["deltas"]
            print(f"  {p['name']:20s} {d['agq_v3c']:>+8.4f} {d['M']:>+8.4f} {d['A']:>+8.4f} "
                  f"{d['S']:>+8.4f} {d['C']:>+8.4f} {d['CD']:>+8.4f}")
    
    # Save
    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "artifacts", "e9_pilot_results.json"
    )
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
