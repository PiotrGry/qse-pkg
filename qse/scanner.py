"""
Static AST analysis: parse Python files, extract import graph,
detect layer membership, count methods/attributes per class.
"""

import ast
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import networkx as nx

# Canonical DDD layers ordered from inner to outer
LAYER_ORDER = {"domain": 0, "application": 1, "infrastructure": 2, "presentation": 3}

# Path patterns excluded by default from health/gate-diff scans. Vendored deps,
# build outputs, cloned third-party repos in artifacts/, hidden tooling dirs.
# Callers that genuinely want to scan these (e.g. raw `qse agq` on a vendored
# tree) can pass exclude=[] to override.
DEFAULT_EXCLUDES = [
    "**/__pycache__/**", "**/_vendor/**", "**/vendor/**",
    "**/build/**", "**/dist/**", "**/node_modules/**",
    "**/.tox/**", "**/.venv/**", "**/venv/**",
    "**/.git/**", "**/.claude/**", "**/.gstack/**",
    "**/.pytest_cache/**", "**/artifacts/**",
]


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
    is_exception: bool = False  # True if class inherits from Exception/BaseException
    is_abstract: bool = False   # True if class uses ABC, Protocol, or @abstractmethod
    method_attrs: List[tuple] = field(default_factory=list)  # [(method_name, {attr1, ...}), ...]


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


def _extract_imports(tree: ast.AST, pkg: str = "") -> List[str]:
    """Extract all imported module strings from AST.

    pkg: dotted package of the file being scanned, used to resolve relative
    imports (`from . import x`, `from ..foo import bar`). Empty string for
    top-level files.
    """
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                imports.append(node.module)
            elif node.level > 0:
                base_parts = pkg.split(".") if pkg else []
                keep = max(0, len(base_parts) - node.level + 1)
                base = ".".join(base_parts[:keep])
                if node.module:
                    dep = f"{base}.{node.module}".lstrip(".")
                    if dep:
                        imports.append(dep)
                else:
                    if base:
                        imports.append(base)
    return imports


def _extract_imports_with_aliases(
    tree: ast.AST, pkg: str = "",
) -> List[tuple[str, list[str]]]:
    """Like _extract_imports but also returns names imported via ImportFrom.

    Returns [(module_name, [name, ...]), ...] so callers can wire edges to
    re-exported submodules: `from pkg import sub` produces edge to pkg.sub
    when that module exists.
    """
    out: List[tuple[str, list[str]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append((alias.name, []))
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                base = node.module or ""
            else:
                base_parts = pkg.split(".") if pkg else []
                keep = max(0, len(base_parts) - node.level + 1)
                base = ".".join(base_parts[:keep])
                if node.module:
                    base = f"{base}.{node.module}".lstrip(".")
            if base:
                names = [a.name for a in node.names]
                out.append((base, names))
    return out


def _extract_classes(tree: ast.AST, file_path: str,
                     layer: str) -> List[ClassInfo]:
    """Extract class metadata from AST."""
    classes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        n_methods = len(methods)
        n_init_only = (n_methods == 1 and methods[0].name == "__init__")

        # Count attributes assigned in __init__
        n_attrs = 0
        for m in methods:
            if m.name == "__init__":
                for stmt in ast.walk(m):
                    if isinstance(stmt, ast.Attribute) and isinstance(stmt.ctx, ast.Store):
                        n_attrs += 1

        # Extract method->attribute map for LCOM4
        # Includes both self.attr reads/writes AND self.method() calls
        method_attrs = []
        for m in methods:
            attrs = set()
            for stmt in ast.walk(m):
                if isinstance(stmt, ast.Attribute) and isinstance(getattr(stmt, 'value', None), ast.Name):
                    if stmt.value.id == 'self':
                        attrs.add(stmt.attr)
            method_attrs.append((m.name, attrs))

        # Detect abstract classes: ABC, Protocol, @abstractmethod
        _abstract_bases = {"ABC", "ABCMeta", "Protocol"}
        base_names = {b.id for b in node.bases if isinstance(b, ast.Name)}
        # Also check dotted bases like abc.ABC
        for b in node.bases:
            if isinstance(b, ast.Attribute):
                base_names.add(b.attr)

        is_abstract = bool(base_names & _abstract_bases)
        # Check for @abstractmethod on any method
        if not is_abstract:
            for m in methods:
                for dec in m.decorator_list:
                    dec_name = ""
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Attribute):
                        dec_name = dec.attr
                    if dec_name == "abstractmethod":
                        is_abstract = True
                        break
                if is_abstract:
                    break

        _exception_bases = {"Exception", "BaseException", "ValueError", "RuntimeError",
                            "TypeError", "KeyError", "IOError", "OSError", "AttributeError"}
        base_names = {b.id for b in node.bases if isinstance(b, ast.Name)}
        is_exception = bool(base_names & _exception_bases) or node.name.endswith("Error") or node.name.endswith("Exception")

        info = ClassInfo(
            name=node.name,
            file_path=file_path,
            layer=layer or "unknown",
            n_methods=n_methods,
            n_init_only=n_init_only,
            n_attributes=n_attrs,
            is_exception=is_exception,
            is_abstract=is_abstract,
            method_attrs=method_attrs,
        )
        classes.append(info)
    return classes


def scan_repo(
    base_dir: str,
    layer_map: dict = None,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> StaticAnalysis:
    """
    Perform static analysis on .py files under base_dir.

    include: glob patterns (repo-relative). Default ["**/*.py"].
    exclude: glob patterns (repo-relative). Default []. Excludes win
             over includes.

    `__init__.py` is now scanned — package-level `from .x import y`
    statements are real edges in the dependency graph and must
    participate in cycle/layer/boundary analysis.
    """
    import re as _re

    include = include or ["**/*.py"]
    exclude = exclude or []

    def _glob_to_re(pattern: str) -> _re.Pattern:
        """Convert a gitignore-style glob to a compiled regex.

        **/   -> zero or more path components (works at start, middle, end)
        **    -> any sequence including separators
        *     -> any sequence excluding '/'
        ?     -> single character excluding '/'
        rest  -> literal (escaped)
        """
        regex = ""
        i = 0
        while i < len(pattern):
            if pattern[i:i + 3] == "**/":
                # Zero or more path components: "qse/**/*.py" matches "qse/foo.py"
                # AND "qse/a/b/foo.py" — the (.+/)? form handles both.
                regex += "(.+/)?"
                i += 3
            elif pattern[i:i + 2] == "**":
                regex += ".*"
                i += 2
            elif pattern[i] == "*":
                regex += "[^/]*"
                i += 1
            elif pattern[i] == "?":
                regex += "[^/]"
                i += 1
            elif pattern[i] == "[":
                # Character class — pass through verbatim until closing "]".
                # re.escape would escape the brackets, breaking [abc] / [!abc].
                # Convert fnmatch-style negation [!...] to re-style [^...].
                j = i + 1
                char_class = "["
                if j < len(pattern) and pattern[j] == "!":
                    char_class += "^"
                    j += 1
                elif j < len(pattern) and pattern[j] == "]":
                    # Literal ] at start of class is valid in fnmatch
                    char_class += "]"
                    j += 1
                while j < len(pattern) and pattern[j] != "]":
                    char_class += pattern[j]
                    j += 1
                char_class += "]"
                regex += char_class
                i = j + 1  # skip past the closing ]
            else:
                regex += _re.escape(pattern[i])
                i += 1
        return _re.compile(r"\A" + regex + r"\Z")

    _compiled_include = [(_glob_to_re(g), g) for g in include]
    _compiled_exclude = [(_glob_to_re(g), g) for g in exclude]

    def _keep(rel_path: str) -> bool:
        if not any(rx.match(rel_path) for rx, _ in _compiled_include):
            return False
        if any(rx.match(rel_path) for rx, _ in _compiled_exclude):
            return False
        return True

    graph = nx.DiGraph()
    all_classes: Dict[str, ClassInfo] = {}
    all_files: List[str] = []

    py_files = []
    for root, _dirs, files in os.walk(base_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, base_dir).replace(os.sep, "/")
            if not _keep(rel):
                continue
            py_files.append(full)

    # First pass: register all internal modules as nodes
    parsed: Dict[str, tuple[str, str, ast.AST | None]] = {}
    for fpath in sorted(py_files):
        all_files.append(fpath)
        mod = _module_path(fpath, base_dir)
        layer = _detect_layer(fpath, base_dir, layer_map=layer_map)
        graph.add_node(mod, layer=layer, file=fpath)
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
            tree = ast.parse(source, filename=fpath)
        except (OSError, SyntaxError):
            tree = None
        parsed[fpath] = (mod, layer, tree)

    # Second pass: edges (with relative-import resolution + re-export
    # expansion). Edges to non-internal targets are kept (matches earlier
    # scan_repo behavior; consumers filter via _internal_subgraph).
    for fpath in sorted(py_files):
        mod, layer, tree = parsed[fpath]
        if tree is None:
            continue
        pkg = ".".join(mod.split(".")[:-1])
        for base, names in _extract_imports_with_aliases(tree, pkg=pkg):
            graph.add_edge(mod, base)
            # Re-export expansion: `from pkg import sub` → edge mod→pkg.sub
            # if pkg.sub is itself an internal module.
            for name in names:
                full = f"{base}.{name}"
                if full in graph and graph.nodes[full].get("file"):
                    graph.add_edge(mod, full)

        # Class info
        for cls_info in _extract_classes(tree, fpath, layer):
            cls_info.dependencies = _extract_imports(tree, pkg=pkg)
            all_classes[cls_info.name] = cls_info

    return StaticAnalysis(graph=graph, classes=all_classes, files=all_files)


def detect_layer_violations(analysis: StaticAnalysis,
                            layer_order: dict = None) -> List[Tuple[str, str, str, str]]:
    """
    Detect edges that violate layering rules.

    layer_order: dict mapping layer names to ordinals (lower = inner).
                 Defaults to DDD LAYER_ORDER if not provided.

    The Dependency Rule: dependencies must point inward (outer→inner).

    Violations:
    - Inner layer imports outer layer (dependency inversion)

    Allowed:
    - Outer layer importing any inner layer
    - Same-layer imports

    Returns list of (source_mod, target_mod, source_layer, target_layer).
    """
    if layer_order is None:
        layer_order = LAYER_ORDER

    violations = []
    for src, tgt in analysis.graph.edges():
        src_layer = analysis.graph.nodes.get(src, {}).get("layer")
        tgt_layer = analysis.graph.nodes.get(tgt, {}).get("layer")
        if src_layer is None or tgt_layer is None:
            continue
        src_ord = layer_order.get(src_layer, -1)
        tgt_ord = layer_order.get(tgt_layer, -1)
        if src_ord < 0 or tgt_ord < 0:
            continue

        # Violation: inner layer imports outer layer (dependency inversion)
        if src_ord < tgt_ord:
            violations.append((src, tgt, src_layer, tgt_layer))

    return violations


# ── Canonical graph-only entry point ──────────────────────────────────────────
# Used by health, gate-diff, pre-commit hook, archeology — any caller that
# wants just the dependency DiGraph without class metadata. Internally
# delegates to scan_repo() to keep import resolution + class extraction
# identical across the product.

def scan_dependency_graph(
    base_dir: str,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> nx.DiGraph:
    """Return only the dependency graph for `base_dir`.

    Identical resolution semantics as scan_repo: relative imports resolved,
    re-exported submodules wired as edges, internal nodes carry `file=`
    attribute. External imports become edge targets without `file=` so
    consumers can filter via _internal_subgraph.
    """
    if include is None:
        include = ["**/*.py"]
    if exclude is None:
        exclude = []
    exclude = list(exclude) + [e for e in DEFAULT_EXCLUDES if e not in exclude]
    return scan_repo(base_dir, include=include, exclude=exclude).graph
