"""Heuristic defect detectors extracted from run_poc.py."""

import math
import os
from typing import Dict, Set

import networkx as nx

from qse.scanner import StaticAnalysis, detect_layer_violations
from qse.config import QSEConfig
from qse.symbol_map import detect_zombie_v2


def detect_anemic(analysis: StaticAnalysis, repo_dir: str) -> Set[str]:
    """Detect anemic domain entities (only __init__, no domain methods)."""
    result = set()
    for cls in analysis.classes.values():
        if cls.layer == "domain" and cls.n_init_only:
            result.add(os.path.relpath(cls.file_path, repo_dir))
    return result


def detect_fat(analysis: StaticAnalysis, repo_dir: str,
               threshold: int = 8, steepness: float = 1.0) -> Set[str]:
    """Detect fat services using sigmoid scoring. Returns files with penalty > 0.5."""
    result = set()
    for cls in analysis.classes.values():
        if cls.layer == "application":
            penalty = 1.0 / (1.0 + math.exp(-steepness * (cls.n_methods - threshold)))
            if penalty > 0.5:
                result.add(os.path.relpath(cls.file_path, repo_dir))
    return result


def _normalize_name(name: str) -> str:
    """Normalize class/module name for matching: LineItem -> lineitem, line_item -> lineitem."""
    return name.lower().replace("_", "")


def detect_zombie(analysis: StaticAnalysis, graph: nx.DiGraph,
                  repo_dir: str) -> Set[str]:
    """Detect zombie domain entities not referenced by any service."""
    all_domain = {cls.name for cls in analysis.classes.values()
                  if cls.layer == "domain"}
    referenced = set()

    def _matches(entity_name: str, dep_string: str) -> bool:
        """Check if entity name matches a dependency string (handles snake_case vs CamelCase)."""
        norm_entity = _normalize_name(entity_name)
        norm_dep = _normalize_name(dep_string)
        return norm_entity in norm_dep

    # Check non-domain classes for references
    for cls in analysis.classes.values():
        if cls.layer != "domain":
            for dep in cls.dependencies:
                for ename in all_domain:
                    if _matches(ename, dep):
                        referenced.add(ename)

    # Check graph edges
    for u, v in graph.edges():
        for ename in all_domain:
            if _matches(ename, v):
                referenced.add(ename)

    # Check domain-to-domain dependencies (indirect references):
    # If Order references LineItem, and Order is referenced by a service,
    # then LineItem is also reachable (not a zombie).
    changed = True
    while changed:
        changed = False
        for cls in analysis.classes.values():
            if cls.layer == "domain" and cls.name in referenced:
                for dep in cls.dependencies:
                    for ename in all_domain:
                        if _matches(ename, dep) and ename not in referenced:
                            referenced.add(ename)
                            changed = True

    result = set()
    for cls in analysis.classes.values():
        if cls.layer == "domain" and cls.name not in referenced:
            result.add(os.path.relpath(cls.file_path, repo_dir))
    return result


def detect_layer_violations_set(analysis: StaticAnalysis, graph: nx.DiGraph,
                                repo_dir: str) -> Set[str]:
    """Detect files with layer violations."""
    violations = detect_layer_violations(analysis)
    result = set()
    for src, tgt, sl, tl in violations:
        node_data = analysis.graph.nodes.get(src, {})
        if "file" in node_data:
            result.add(os.path.relpath(node_data["file"], repo_dir))
    for src, tgt in graph.edges():
        src_layer = graph.nodes.get(src, {}).get("layer")
        tgt_layer = graph.nodes.get(tgt, {}).get("layer")
        if src_layer == "presentation" and tgt_layer == "domain":
            node_data = graph.nodes.get(src, {})
            if "file" in node_data:
                result.add(os.path.relpath(node_data["file"], repo_dir))
    return result


def detect_all(analysis: StaticAnalysis, graph: nx.DiGraph,
               repo_dir: str, config: QSEConfig = None) -> Dict[str, Set[str]]:
    """Run all defect detectors. Returns {defect_type: set_of_files}.

    Zombie detection uses v2 (AST symbol-map, F1=0.964) when a domain/
    directory exists; falls back to v1 (string matching) otherwise.
    """
    if config is None:
        config = QSEConfig()

    domain_dir = os.path.join(repo_dir, "domain")
    if os.path.isdir(domain_dir):
        zombie = detect_zombie_v2(repo_dir, mode="conservative")
    else:
        zombie = detect_zombie(analysis, graph, repo_dir)

    return {
        "anemic_entity": detect_anemic(analysis, repo_dir),
        "fat_service": detect_fat(analysis, repo_dir,
                                  config.fat_threshold, config.fat_steepness),
        "zombie_entity": zombie,
        "layer_violation": detect_layer_violations_set(analysis, graph, repo_dir),
    }
