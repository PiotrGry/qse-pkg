"""
Pure-Python Java scanner using tree-sitter.

Produces a NetworkX DiGraph + class metadata compatible with
qse.graph_metrics.compute_agq(). This replaces the Rust scanner
(_qse_core) when it's unavailable.

Matches the Rust scanner's output format:
  - Nodes = Java files as "package.ClassName" (file-level granularity)
  - Edges = import dependencies between files
  - Internal graph = scanned files + their direct import targets
  - Classes = per-class metadata (name, file, is_abstract, methods, fields)
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

import networkx as nx
import tree_sitter_java as tsjava
from tree_sitter import Language, Parser

# ── Tree-sitter setup ──
JAVA_LANGUAGE = Language(tsjava.language())


@dataclass
class JavaClassInfo:
    name: str
    fqn: str  # fully qualified: package.ClassName
    file_path: str
    package: str
    is_abstract: bool = False
    is_interface: bool = False
    methods: List[str] = field(default_factory=list)
    fields: List[str] = field(default_factory=list)
    # (method_name, {field_names_used}) for LCOM4
    method_attrs: List[Tuple[str, Set[str]]] = field(default_factory=list)


@dataclass
class JavaScanResult:
    graph: nx.DiGraph  # internal-only graph (file-level nodes)
    classes: Dict[str, JavaClassInfo]  # key = FQN
    files: List[str]
    packages: Set[str]
    internal_nodes: Set[str]  # module paths of scanned files
    n_external_imports: int = 0


def _get_text(node) -> str:
    """Extract UTF-8 text from a tree-sitter node."""
    return node.text.decode("utf-8") if node.text else ""


def _scoped_name(node) -> str:
    """Recursively extract a scoped_identifier like com.example.domain."""
    if node.type == "identifier":
        return _get_text(node)
    if node.type == "scoped_identifier":
        parts = []
        for child in node.children:
            if child.type in ("identifier", "scoped_identifier"):
                parts.append(_scoped_name(child))
        return ".".join(parts)
    return _get_text(node)


def _extract_package(root_node) -> Optional[str]:
    """Extract package declaration from a Java file's AST."""
    for child in root_node.children:
        if child.type == "package_declaration":
            for sub in child.children:
                if sub.type in ("scoped_identifier", "identifier"):
                    return _scoped_name(sub)
    return None


def _extract_imports(root_node) -> List[str]:
    """Extract all import declarations, return list of fully-qualified names.
    
    Returns the raw import paths (e.g. com.example.domain.Entity).
    """
    imports = []
    for child in root_node.children:
        if child.type == "import_declaration":
            for sub in child.children:
                if sub.type in ("scoped_identifier", "identifier"):
                    imp = _scoped_name(sub)
                    imports.append(imp)
    return imports


def _is_abstract_class(node) -> bool:
    """Check if a class_declaration has 'abstract' modifier."""
    for child in node.children:
        if child.type == "modifiers":
            for mod in child.children:
                if _get_text(mod) == "abstract":
                    return True
    return False


def _extract_fields_from_body(class_body_node) -> List[str]:
    """Extract field names from a class body."""
    fields = []
    for child in class_body_node.children:
        if child.type == "field_declaration":
            for sub in child.children:
                if sub.type == "variable_declarator":
                    for ident in sub.children:
                        if ident.type == "identifier":
                            fields.append(_get_text(ident))
                            break
    return fields


def _extract_methods_and_fields(class_body_node, all_fields: List[str]) -> List[Tuple[str, Set[str]]]:
    """Extract method-to-field mappings for LCOM4 computation."""
    method_attrs = []
    for child in class_body_node.children:
        if child.type == "method_declaration":
            method_name = None
            for sub in child.children:
                if sub.type == "identifier":
                    method_name = _get_text(sub)
                    break
            if method_name:
                body_text = _get_text(child)
                accessed = set()
                for f in all_fields:
                    if f in body_text:
                        accessed.add(f)
                method_attrs.append((method_name, accessed))
    return method_attrs


def _extract_classes(root_node, file_path: str, package: str) -> List[JavaClassInfo]:
    """Extract all class/interface declarations from a Java file."""
    classes = []
    for child in root_node.children:
        if child.type in ("class_declaration", "interface_declaration",
                          "enum_declaration", "record_declaration"):
            name = None
            is_interface = child.type == "interface_declaration"
            is_abstract = is_interface or _is_abstract_class(child)

            for sub in child.children:
                if sub.type == "identifier":
                    name = _get_text(sub)
                    break

            if not name:
                continue

            fqn = f"{package}.{name}" if package else name
            methods = []
            fields = []
            method_attrs = []

            for sub in child.children:
                if sub.type in ("class_body", "interface_body", "enum_body"):
                    fields = _extract_fields_from_body(sub)
                    method_attrs = _extract_methods_and_fields(sub, fields)
                    methods = [m[0] for m in method_attrs]
                    break

            cls = JavaClassInfo(
                name=name,
                fqn=fqn,
                file_path=file_path,
                package=package or "",
                is_abstract=is_abstract,
                is_interface=is_interface,
                methods=methods,
                fields=fields,
                method_attrs=method_attrs,
            )
            classes.append(cls)
    return classes


def _find_source_root(base_dir: str) -> str:
    """Find the Java source root (look for src/main/java or src/)."""
    base = Path(base_dir)
    candidates = [
        base / "src" / "main" / "java",
        base / "src",
        base,
    ]
    # Also check for multi-module projects
    for d in base.iterdir():
        if d.is_dir() and (d / "src" / "main" / "java").exists():
            # Multi-module — scan from base
            return str(base)
    
    for c in candidates:
        if c.exists():
            return str(c)
    return str(base)


def scan_java_repo(base_dir: str) -> JavaScanResult:
    """
    Scan a Java repository and build the internal dependency graph.

    Matches the Rust scanner's behavior:
    - Each .java file becomes a node: "package.ClassName"
    - Edges are import dependencies (mapped to file-level targets)
    - Internal graph includes scanned files + their direct neighbors
    - External (stdlib/third-party) imports are resolved as nodes too
      (for correct graph structure) but marked non-internal

    Parameters
    ----------
    base_dir : str
        Root directory of the Java project.

    Returns
    -------
    JavaScanResult
    """
    parser = Parser(JAVA_LANGUAGE)

    # Find all .java files (skip test files matching common patterns)
    java_files = []
    base = Path(base_dir)
    for root, dirs, files in os.walk(base):
        # Skip common non-source directories
        dirs[:] = [d for d in dirs if d not in 
                   ('.git', 'target', 'build', 'node_modules', '.gradle', '.mvn')]
        for fname in files:
            if fname.endswith(".java"):
                java_files.append(os.path.join(root, fname))

    # Phase 1: Parse all files
    file_results = []  # (mod_path, imports_raw, classes)
    internal_nodes: Set[str] = set()
    all_classes: Dict[str, JavaClassInfo] = {}
    all_packages: Set[str] = set()

    for fpath in sorted(java_files):
        try:
            with open(fpath, "rb") as f:
                source = f.read()
            # Skip very large files (likely generated)
            if len(source) > 1_048_576:
                continue
            tree = parser.parse(source)
        except Exception:
            continue

        root_node = tree.root_node
        package = _extract_package(root_node)
        imports_raw = _extract_imports(root_node)
        classes = _extract_classes(root_node, fpath, package)

        if package:
            all_packages.add(package)

        # Module path = "package.ClassName" (matches Rust scanner)
        class_name = Path(fpath).stem
        if package:
            mod_path = f"{package}.{class_name}"
        else:
            mod_path = class_name

        internal_nodes.add(mod_path)

        for cls in classes:
            all_classes[cls.fqn] = cls

        file_results.append((mod_path, imports_raw, classes))

    # Phase 2: Build full graph (all nodes including external)
    full_graph = nx.DiGraph()

    for mod_path, imports_raw, classes in file_results:
        full_graph.add_node(mod_path)
        for imp in imports_raw:
            # Import is already a fully-qualified name (e.g. com.example.Entity)
            # Add edge from this file's mod_path to the import target
            if imp != mod_path:
                full_graph.add_node(imp)
                full_graph.add_edge(mod_path, imp)

    # Phase 3: Build internal graph (mirrors Rust's internal_graph)
    # Internal graph = internal nodes + their direct neighbors + edges between them
    connected: Set[str] = set()
    for node in internal_nodes:
        if node in full_graph:
            connected.add(node)
            for neighbor in full_graph.neighbors(node):
                connected.add(neighbor)

    internal_graph = nx.DiGraph()
    for node in connected:
        internal_graph.add_node(node)

    for u, v in full_graph.edges():
        if u in connected and v in connected:
            internal_graph.add_edge(u, v)

    n_external = sum(1 for n in connected if n not in internal_nodes)

    return JavaScanResult(
        graph=internal_graph,
        classes=all_classes,
        files=java_files,
        packages=all_packages,
        internal_nodes=internal_nodes,
        n_external_imports=n_external,
    )


def scan_result_to_agq_inputs(result: JavaScanResult):
    """
    Convert JavaScanResult into inputs for compute_agq().

    Returns
    -------
    graph : nx.DiGraph
        Internal dependency graph.
    abstract_modules : set
        Set of module paths containing abstract classes/interfaces.
    lcom4_values : list
        LCOM4 values for each class (for cohesion metric).
    """
    from qse.graph_metrics import compute_lcom4

    # Abstract modules: files that contain abstract classes/interfaces
    abstract_modules = set()
    for cls in result.classes.values():
        if cls.is_abstract:
            mod_path = f"{cls.package}.{cls.name}" if cls.package else cls.name
            abstract_modules.add(mod_path)

    # LCOM4 per class
    lcom4_values = []
    for cls in result.classes.values():
        if cls.method_attrs:
            lcom4 = compute_lcom4(cls.method_attrs)
            lcom4_values.append(lcom4)

    return result.graph, abstract_modules, lcom4_values
