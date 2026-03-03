"""
Static AST analysis: parse Python files, extract import graph,
detect layer membership, count methods/attributes per class.
"""

import ast
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

# Canonical DDD layers ordered from inner to outer
LAYER_ORDER = {"domain": 0, "application": 1, "infrastructure": 2, "presentation": 3}


@dataclass
class ClassInfo:
    """Extracted metadata about a single class."""
    name: str
    file_path: str
    layer: str
    n_methods: int = 0
    n_init_only: bool = False  # True if only __init__ exists
    n_attributes: int = 0
    dependencies: List[str] = field(default_factory=list)  # imported class names


@dataclass
class StaticAnalysis:
    """Result of scanning a repository."""
    graph: nx.DiGraph  # nodes = module paths, edges = imports
    classes: Dict[str, ClassInfo] = field(default_factory=dict)  # class_name -> info
    files: List[str] = field(default_factory=list)


def _detect_layer(file_path: str, base_dir: str,
                  layer_map: dict = None) -> Optional[str]:
    """Determine DDD layer from file path relative to base_dir.

    layer_map: optional custom mapping e.g. {"common": "domain", "audit": "application"}
    """
    rel = os.path.relpath(file_path, base_dir)
    parts = rel.split(os.sep)
    if parts:
        candidate = parts[0].lower()
        if layer_map and candidate in layer_map:
            return layer_map[candidate]
        if candidate in LAYER_ORDER:
            return candidate
    return None


def _module_path(file_path: str, base_dir: str) -> str:
    """Convert file path to dotted module path."""
    rel = os.path.relpath(file_path, base_dir).replace(os.sep, ".")
    if rel.endswith(".py"):
        rel = rel[:-3]
    return rel


def _extract_imports(tree: ast.AST) -> List[str]:
    """Extract all imported module strings from AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _extract_classes(tree: ast.AST, file_path: str,
                     layer: str) -> List[ClassInfo]:
    """Extract class metadata from AST."""
    classes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        n_methods = len(methods)
        n_init_only = (n_methods == 1 and methods[0].name == "__init__") if methods else n_methods == 0

        # Count attributes assigned in __init__
        n_attrs = 0
        for m in methods:
            if m.name == "__init__":
                for stmt in ast.walk(m):
                    if isinstance(stmt, ast.Attribute) and isinstance(stmt.ctx, ast.Store):
                        n_attrs += 1

        info = ClassInfo(
            name=node.name,
            file_path=file_path,
            layer=layer or "unknown",
            n_methods=n_methods,
            n_init_only=n_init_only,
            n_attributes=n_attrs,
        )
        classes.append(info)
    return classes


def scan_repo(base_dir: str, layer_map: dict = None) -> StaticAnalysis:
    """
    Perform static analysis on all .py files under base_dir.

    Returns a StaticAnalysis containing:
    - Import dependency graph (DiGraph)
    - Per-class metadata
    - File list

    layer_map: optional custom directory→layer mapping,
               e.g. {"common": "domain", "audit": "application"}
    """
    graph = nx.DiGraph()
    all_classes: Dict[str, ClassInfo] = {}
    all_files: List[str] = []

    py_files = []
    for root, _dirs, files in os.walk(base_dir):
        for fname in files:
            if fname.endswith(".py") and fname != "__init__.py":
                py_files.append(os.path.join(root, fname))

    for fpath in sorted(py_files):
        all_files.append(fpath)
        mod = _module_path(fpath, base_dir)
        layer = _detect_layer(fpath, base_dir, layer_map=layer_map)
        graph.add_node(mod, layer=layer, file=fpath)

        try:
            with open(fpath, "r") as f:
                source = f.read()
            tree = ast.parse(source, filename=fpath)
        except SyntaxError:
            continue

        # Import edges
        for imp in _extract_imports(tree):
            graph.add_edge(mod, imp)

        # Class info
        for cls_info in _extract_classes(tree, fpath, layer):
            cls_info.dependencies = _extract_imports(tree)
            all_classes[cls_info.name] = cls_info

    return StaticAnalysis(graph=graph, classes=all_classes, files=all_files)


def detect_layer_violations(analysis: StaticAnalysis) -> List[Tuple[str, str, str, str]]:
    """
    Detect edges that violate DDD layering (outer → inner skipping layers,
    or presentation importing domain directly).

    Returns list of (source_mod, target_mod, source_layer, target_layer).
    """
    violations = []
    for src, tgt in analysis.graph.edges():
        src_layer = analysis.graph.nodes.get(src, {}).get("layer")
        tgt_layer = analysis.graph.nodes.get(tgt, {}).get("layer")
        if src_layer is None or tgt_layer is None:
            continue
        src_ord = LAYER_ORDER.get(src_layer, -1)
        tgt_ord = LAYER_ORDER.get(tgt_layer, -1)
        # Violation: presentation (3) imports domain (0) directly
        if src_layer == "presentation" and tgt_layer == "domain":
            violations.append((src, tgt, src_layer, tgt_layer))
    return violations
