"""
AGQ Mutation Operators - inject controlled architectural degradations.

Each operator takes a repo path, dose (0.0-1.0), and seed,
modifies files in-place, and returns metadata about what was changed.
Caller is responsible for git checkout after scanning.
"""

import json
import os
import random
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx


def _scan_graph(repo_path: str) -> Tuple[nx.DiGraph, str, dict]:
    """Scan repo and return (nx.DiGraph, language, node_files).

    node_files maps module_id -> file_path for internal modules.
    File paths are reconstructed from module IDs since the Rust scanner
    returns 'internal' flag but not file paths in graph JSON.
    """
    from _qse_core import scan_to_graph_json
    raw = scan_to_graph_json(repo_path)
    data = json.loads(raw)
    lang = data.get("language", "Python")
    G = nx.DiGraph()
    node_files = {}

    for node in data["nodes"]:
        is_internal = node.get("internal", False) or bool(node.get("file"))
        G.add_node(node["id"], internal=is_internal)
        if is_internal:
            # Reconstruct file path from module ID
            fpath = _module_to_filepath(repo_path, node["id"], lang)
            if fpath and os.path.isfile(fpath):
                node_files[node["id"]] = fpath

    for src, tgt in data["edges"]:
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt)
    return G, lang, node_files


_FILE_CACHE: Dict[str, Dict[str, str]] = {}

def _build_file_index(repo_path: str, language: str) -> Dict[str, str]:
    """Build module_name → file_path index by walking repo."""
    cache_key = repo_path
    if cache_key in _FILE_CACHE:
        return _FILE_CACHE[cache_key]

    ext_map = {"Python": ".py", "Java": ".java", "Go": ".go"}
    ext = ext_map.get(language, ".py")
    index = {}

    for root, dirs, files in os.walk(repo_path):
        # Skip hidden dirs, __pycache__, node_modules, .git, test dirs
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and d not in ("__pycache__", "node_modules", ".git", "vendor",
                                 "build", "target", "dist")]
        for fname in files:
            if not fname.endswith(ext):
                continue
            if fname.endswith("_test.go") or fname.startswith("test_"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, repo_path)
            # Convert path to module-like ID
            if language == "Python":
                mod = rel.replace(os.sep, ".").replace(".__init__.py", "").replace(".py", "")
            elif language == "Java":
                mod = rel.replace(os.sep, ".").replace(".java", "")
                # Strip common prefixes
                for prefix in ["src.main.java.", "src."]:
                    if mod.startswith(prefix):
                        mod = mod[len(prefix):]
            elif language == "Go":
                # Go: use directory as package
                mod = os.path.dirname(rel).replace(os.sep, ".")
            else:
                mod = rel.replace(os.sep, ".").replace(ext, "")

            # Store both full module path and leaf name
            index[mod] = fpath
            # Also store by leaf (e.g. "_config" for "httpx._config")
            leaf = mod.split(".")[-1] if "." in mod else mod
            if leaf not in index:
                index[leaf] = fpath
            # Store partial paths (e.g. "_transports.default" for "httpx._transports.default")
            parts = mod.split(".")
            for i in range(1, len(parts)):
                partial = ".".join(parts[i:])
                if partial not in index:
                    index[partial] = fpath

    _FILE_CACHE[cache_key] = index
    return index


def _module_to_filepath(repo_path: str, module_id: str, language: str) -> Optional[str]:
    """Find file path for a module ID using indexed search."""
    index = _build_file_index(repo_path, language)
    # Direct match
    if module_id in index:
        return index[module_id]
    # Try without leading underscore
    if module_id.startswith("_") and module_id[1:] in index:
        return index[module_id[1:]]
    return None


def _get_packages(G: nx.DiGraph) -> Dict[str, List[str]]:
    """Group nodes by second-level package (a.b.c → a.b)."""
    packages = {}
    for node in G.nodes():
        parts = node.split(".")
        pkg = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
        packages.setdefault(pkg, []).append(node)
    return packages


def _get_internal_nodes(G: nx.DiGraph) -> List[str]:
    """Get internal nodes (scanned source modules)."""
    return [n for n, d in G.nodes(data=True) if d.get("internal")]


def _make_import_line(language: str, module_path: str) -> str:
    """Generate an import statement for the given language."""
    if language == "Python":
        return f"import {module_path}\n"
    elif language == "Java":
        return f"import {module_path};\n"
    elif language == "Go":
        # Go imports are paths, not dot-separated
        return f'import _ "{module_path}"\n'
    return f"import {module_path}\n"


def _append_import_to_file(file_path: str, import_line: str, language: str):
    """Append an import to a source file, language-aware placement."""
    if not os.path.isfile(file_path):
        return False
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if language == "Python":
        # Add after last import line or at top
        lines = content.split("\n")
        last_import = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                last_import = i
        if last_import >= 0:
            lines.insert(last_import + 1, import_line.rstrip())
        else:
            lines.insert(0, import_line.rstrip())
        content = "\n".join(lines)
    elif language == "Java":
        # Add after last import line
        lines = content.split("\n")
        last_import = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("import "):
                last_import = i
        if last_import >= 0:
            lines.insert(last_import + 1, import_line.rstrip())
        else:
            # After package declaration
            pkg_line = -1
            for i, line in enumerate(lines):
                if line.strip().startswith("package "):
                    pkg_line = i
                    break
            lines.insert(pkg_line + 1 if pkg_line >= 0 else 0, import_line.rstrip())
        content = "\n".join(lines)
    elif language == "Go":
        # Add inside import block or create one
        if 'import (' in content:
            content = content.replace('import (', f'import (\n\t{import_line.strip()}', 1)
        elif 'import "' in content or "import '" in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.strip().startswith("import "):
                    lines.insert(i + 1, import_line.rstrip())
                    break
            content = "\n".join(lines)
        else:
            lines = content.split("\n")
            # After package line
            for i, line in enumerate(lines):
                if line.strip().startswith("package "):
                    lines.insert(i + 1, import_line.rstrip())
                    break
            content = "\n".join(lines)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


# ---------------------------------------------------------------------------
# Mutation 1: Cycle Injection (→ Acyclicity)
# ---------------------------------------------------------------------------

def inject_cycles(repo_path: str, dose: float, seed: int) -> dict:
    """
    Inject dependency cycles by adding backward imports between packages.
    For each acyclic pair (A→B), add B→A import.
    dose = fraction of eligible pairs to mutate.
    """
    G, lang, node_files = _scan_graph(repo_path)
    internal = _get_internal_nodes(G)
    if len(internal) < 4:
        return {"type": "cycle_injection", "dose": dose, "mutations": 0}

    packages = _get_packages(G.subgraph(internal))

    # Find directed package pairs where A→B exists but B→A does not
    pkg_edges = set()
    for u, v in G.subgraph(internal).edges():
        pu = ".".join(u.split(".")[:2]) if "." in u else u
        pv = ".".join(v.split(".")[:2]) if "." in v else v
        if pu != pv:
            pkg_edges.add((pu, pv))

    acyclic_pairs = [(a, b) for a, b in pkg_edges if (b, a) not in pkg_edges]
    if not acyclic_pairs:
        return {"type": "cycle_injection", "dose": dose, "mutations": 0}

    rng = random.Random(seed)
    n_to_mutate = max(1, int(dose * len(acyclic_pairs)))
    selected = rng.sample(acyclic_pairs, min(n_to_mutate, len(acyclic_pairs)))

    mutations = 0
    for pkg_a, pkg_b in selected:
        # pkg_a→pkg_b exists; add pkg_b→pkg_a
        b_nodes = [n for n in packages.get(pkg_b, []) if n in node_files]
        a_nodes = [n for n in packages.get(pkg_a, []) if n in node_files]
        if not b_nodes or not a_nodes:
            continue
        file_in_b = node_files[rng.choice(b_nodes)]
        module_in_a = rng.choice(a_nodes)
        imp = _make_import_line(lang, module_in_a)
        if _append_import_to_file(file_in_b, imp, lang):
            mutations += 1

    return {"type": "cycle_injection", "dose": dose, "mutations": mutations,
            "eligible": len(acyclic_pairs)}


# ---------------------------------------------------------------------------
# Mutation 2: Layer Violation (→ Stability)
# ---------------------------------------------------------------------------

def inject_layer_violations(repo_path: str, dose: float, seed: int) -> dict:
    """
    Add imports from stable (low I) packages to unstable (high I) packages.
    This flattens instability variance → lowers stability score.
    """
    G, lang, node_files = _scan_graph(repo_path)
    internal = _get_internal_nodes(G)
    if len(internal) < 4:
        return {"type": "layer_violation", "dose": dose, "mutations": 0}

    packages = _get_packages(G.subgraph(internal))
    if len(packages) < 3:
        return {"type": "layer_violation", "dose": dose, "mutations": 0}

    # Compute instability per package
    pkg_instability = {}
    for pkg, members in packages.items():
        member_set = set(members)
        ca = sum(1 for m in members for p in G.predecessors(m)
                 if p in set(internal) and p not in member_set)
        ce = sum(1 for m in members for s in G.successors(m)
                 if s in set(internal) and s not in member_set)
        total = ca + ce
        pkg_instability[pkg] = ce / total if total > 0 else 0.5

    sorted_pkgs = sorted(pkg_instability.items(), key=lambda x: x[1])
    n_pkgs = len(sorted_pkgs)
    stable = [p for p, i in sorted_pkgs[:n_pkgs // 3] if i < 0.4]
    unstable = [p for p, i in sorted_pkgs[-(n_pkgs // 3):] if i > 0.6]

    if not stable or not unstable:
        return {"type": "layer_violation", "dose": dose, "mutations": 0}

    rng = random.Random(seed)
    n_to_mutate = max(1, int(dose * len(stable)))
    selected = rng.sample(stable, min(n_to_mutate, len(stable)))

    mutations = 0
    for pkg in selected:
        tgt_pkg = rng.choice(unstable)
        src_nodes = [n for n in packages.get(pkg, []) if n in node_files]
        tgt_nodes = [n for n in packages.get(tgt_pkg, []) if n in node_files]
        if not src_nodes or not tgt_nodes:
            continue
        file_src = node_files[rng.choice(src_nodes)]
        module_tgt = rng.choice(tgt_nodes)
        imp = _make_import_line(lang, module_tgt)
        if _append_import_to_file(file_src, imp, lang):
            mutations += 1

    return {"type": "layer_violation", "dose": dose, "mutations": mutations,
            "eligible_stable": len(stable), "eligible_unstable": len(unstable)}


# ---------------------------------------------------------------------------
# Mutation 3: Hub Creation (→ Modularity Q)
# ---------------------------------------------------------------------------

def create_hubs(repo_path: str, dose: float, seed: int) -> dict:
    """
    Create hub modules by adding many cross-package imports to selected files.
    This destroys community structure → lowers Louvain Q.
    """
    G, lang, node_files = _scan_graph(repo_path)
    internal = _get_internal_nodes(G)
    if len(internal) < 10:
        return {"type": "hub_creation", "dose": dose, "mutations": 0}

    packages = _get_packages(G.subgraph(internal))
    if len(packages) < 3:
        return {"type": "hub_creation", "dose": dose, "mutations": 0}

    rng = random.Random(seed)

    # Select hub candidates (files with known paths)
    hub_candidates = [n for n in internal if n in node_files]
    n_hubs = max(1, int(dose * len(hub_candidates) * 0.05))
    hubs = rng.sample(hub_candidates, min(n_hubs, len(hub_candidates)))

    mutations = 0
    for hub in hubs:
        hub_pkg = ".".join(hub.split(".")[:2]) if "." in hub else hub
        # Find modules in OTHER packages
        foreign = [n for n in internal if n in node_files
                   and (".".join(n.split(".")[:2]) if "." in n else n) != hub_pkg]
        if not foreign:
            continue
        n_imports = max(3, int(dose * min(20, len(foreign))))
        targets = rng.sample(foreign, min(n_imports, len(foreign)))
        for tgt in targets:
            imp = _make_import_line(lang, tgt)
            if _append_import_to_file(node_files[hub], imp, lang):
                mutations += 1

    return {"type": "hub_creation", "dose": dose, "mutations": mutations,
            "n_hubs": len(hubs)}


# ---------------------------------------------------------------------------
# Mutation 4: Cohesion Degradation (→ Cohesion/LCOM4)
# ---------------------------------------------------------------------------

def degrade_cohesion(repo_path: str, dose: float, seed: int) -> dict:
    """
    Move files to foreign packages, breaking cohesion.
    Scanner will see classes in wrong package → LCOM4 increases.
    """
    G, lang, node_files = _scan_graph(repo_path)
    internal = _get_internal_nodes(G)
    if len(internal) < 6:
        return {"type": "cohesion_degradation", "dose": dose, "mutations": 0}

    packages = _get_packages(G.subgraph(internal))
    if len(packages) < 3:
        return {"type": "cohesion_degradation", "dose": dose, "mutations": 0}

    # Find files we can move (must have actual file paths)
    movable = [(n, node_files[n]) for n in internal
               if n in node_files and os.path.isfile(node_files[n])]
    if not movable:
        return {"type": "cohesion_degradation", "dose": dose, "mutations": 0}

    rng = random.Random(seed)
    n_to_move = max(1, int(dose * len(movable)))
    selected = rng.sample(movable, min(n_to_move, len(movable)))

    pkg_dirs = {}
    for pkg, members in packages.items():
        for m in members:
            if m in node_files and os.path.isfile(node_files[m]):
                pkg_dirs[pkg] = os.path.dirname(node_files[m])
                break

    mutations = 0
    for node, filepath in selected:
        src_pkg = ".".join(node.split(".")[:2]) if "." in node else node
        foreign_pkgs = [p for p in pkg_dirs if p != src_pkg]
        if not foreign_pkgs:
            continue
        tgt_pkg = rng.choice(foreign_pkgs)
        tgt_dir = pkg_dirs[tgt_pkg]
        tgt_path = os.path.join(tgt_dir, os.path.basename(filepath))
        if os.path.exists(tgt_path):
            continue
        try:
            os.rename(filepath, tgt_path)
            mutations += 1
        except OSError:
            continue

    return {"type": "cohesion_degradation", "dose": dose, "mutations": mutations,
            "eligible": len(movable)}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

MUTATIONS = {
    "cycle_injection": inject_cycles,
    "layer_violation": inject_layer_violations,
    "hub_creation": create_hubs,
    "cohesion_degradation": degrade_cohesion,
}
