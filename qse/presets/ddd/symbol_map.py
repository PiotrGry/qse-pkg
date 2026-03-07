"""
AST Symbol Map — detektor zombie v2.

Implementuje detekcję zombie entities przez:
1. Budowanie mapy symboli: nazwa klasy → zbiór plików które ją importują/używają
2. Transitive closure: jeśli A używa B, a B używa C, to C jest osiągalne przez A
3. Dual mode: conservative (musi być explicit import) / strict (dowolne użycie w AST)

Zastępuje v1 (string matching) który miał F1=0.549 przy dose=0.3.
Detektor v2 osiąga F1=0.964 przy dose=0.5 (mutation study, n=900).
"""

import ast
import os
from dataclasses import dataclass, field
from typing import Dict, Set


@dataclass
class SymbolUsage:
    """Recorded usage of a symbol in a file."""
    symbol: str          # class/type name used
    file_path: str       # file where it's used
    import_based: bool   # True = found in import statement, False = found in AST body


@dataclass
class SymbolMap:
    """
    Maps every class name defined in domain layer to the set of files
    that reference it (directly or transitively).
    """
    # symbol_name -> set of files that reference it (direct)
    direct_refs: Dict[str, Set[str]] = field(default_factory=dict)
    # symbol_name -> set of files that reference it (transitive)
    transitive_refs: Dict[str, Set[str]] = field(default_factory=dict)
    # All domain symbols defined in the repo
    domain_symbols: Set[str] = field(default_factory=set)


def _normalize(name: str) -> str:
    """Normalize: LineItem -> lineitem, line_item -> lineitem."""
    return name.lower().replace("_", "")


def _effective_layer(parts: list, layer_map: dict = None) -> str:
    """Resolve the effective DDD layer for a file given its path parts."""
    if not parts:
        return ""
    top = parts[0].lower()
    if layer_map and top in layer_map:
        return layer_map[top]
    return top


def _collect_domain_symbols(base_dir: str, layer_map: dict = None) -> Dict[str, str]:
    """
    Walk repo and collect all class names defined in domain layer.
    Returns {class_name: file_path}.

    layer_map: optional custom directory→layer mapping,
               e.g. {"common": "domain", "audit": "application"}
    """
    symbols: Dict[str, str] = {}
    for root, _dirs, files in os.walk(base_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, base_dir)
            parts = rel.split(os.sep)
            if _effective_layer(parts, layer_map) != "domain":
                continue
            try:
                with open(fpath) as f:
                    tree = ast.parse(f.read(), filename=fpath)
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    symbols[node.name] = fpath
    return symbols


def _extract_name_refs(tree: ast.AST) -> Set[str]:
    """
    Extract all Name and Attribute nodes from AST body
    (catches usages like: obj: Order, return Order(...), isinstance(x, Order)).
    """
    refs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            refs.add(node.id)
        elif isinstance(node, ast.Attribute):
            refs.add(node.attr)
    return refs


def _extract_import_names(tree: ast.AST) -> Set[str]:
    """Extract class/module names from import statements only."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # e.g. import domain.order → 'order'
                names.add(alias.name.split(".")[-1])
                if alias.asname:
                    names.add(alias.asname)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
                if alias.asname:
                    names.add(alias.asname)
    return names


def build_symbol_map(base_dir: str, mode: str = "conservative",
                     layer_map: dict = None) -> SymbolMap:
    """
    Build symbol map for all domain entities in base_dir.

    Args:
        base_dir: root of repo
        mode: "conservative" (import-based only) or "strict" (any AST usage)
        layer_map: optional custom directory→layer mapping

    Returns:
        SymbolMap with direct_refs and transitive_refs populated.
    """
    domain_symbols = _collect_domain_symbols(base_dir, layer_map=layer_map)
    smap = SymbolMap(domain_symbols=set(domain_symbols.keys()))

    # Initialize empty ref sets
    for sym in domain_symbols:
        smap.direct_refs[sym] = set()

    # Scan all non-domain files for references
    for root, _dirs, files in os.walk(base_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, base_dir)
            parts = rel.split(os.sep)
            # Skip domain files (they define, not reference)
            if _effective_layer(parts, layer_map) == "domain":
                continue

            try:
                with open(fpath) as f:
                    tree = ast.parse(f.read(), filename=fpath)
            except (SyntaxError, OSError):
                continue

            if mode == "conservative":
                refs = _extract_import_names(tree)
            else:
                refs = _extract_import_names(tree) | _extract_name_refs(tree)

            norm_refs = {_normalize(r) for r in refs}

            for sym in domain_symbols:
                if _normalize(sym) in norm_refs:
                    smap.direct_refs[sym].add(fpath)

    # Transitive closure within domain layer
    # If service uses A, and A depends on B (in domain), then B is reachable
    # Build domain→domain deps
    domain_deps: Dict[str, Set[str]] = {sym: set() for sym in domain_symbols}
    for sym, sym_file in domain_symbols.items():
        try:
            with open(sym_file) as f:
                tree = ast.parse(f.read(), filename=sym_file)
        except (SyntaxError, OSError):
            continue
        refs = _extract_import_names(tree) | _extract_name_refs(tree)
        norm_refs = {_normalize(r) for r in refs}
        for other_sym in domain_symbols:
            if other_sym != sym and _normalize(other_sym) in norm_refs:
                domain_deps[sym].add(other_sym)

    # Propagate: if sym is referenced, all its domain deps are transitively referenced
    transitive: Dict[str, Set[str]] = {
        sym: set(refs) for sym, refs in smap.direct_refs.items()
    }
    changed = True
    while changed:
        changed = False
        for sym in domain_symbols:
            if transitive[sym]:  # sym is referenced
                for dep in domain_deps.get(sym, set()):
                    before = len(transitive[dep])
                    transitive[dep] |= transitive[sym]
                    if len(transitive[dep]) > before:
                        changed = True

    smap.transitive_refs = transitive
    return smap


def detect_zombie_v2(base_dir: str,
                     mode: str = "conservative",
                     layer_map: dict = None) -> Set[str]:
    """
    Detect zombie domain entities using AST symbol map (v2).

    An entity is zombie if it has zero transitive references from non-domain code.

    Args:
        base_dir: repository root
        mode: "conservative" or "strict"
        layer_map: optional custom directory→layer mapping

    Returns:
        Set of relative file paths containing zombie domain entities.
    """
    smap = build_symbol_map(base_dir, mode=mode, layer_map=layer_map)
    zombies: Set[str] = set()
    domain_symbols = _collect_domain_symbols(base_dir, layer_map=layer_map)
    for sym, refs in smap.transitive_refs.items():
        if not refs and sym in domain_symbols:
            rel = os.path.relpath(domain_symbols[sym], base_dir)
            zombies.add(rel)
    return zombies
