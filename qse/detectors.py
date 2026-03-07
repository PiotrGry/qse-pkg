"""
Universal defect detectors — architecture-agnostic.

Uses ClassFilter predicates instead of hardcoded layer names.
The DDD preset (qse/presets/ddd/detectors.py) delegates here with DDD-specific filters.
"""

import math
import os
from typing import Callable, Dict, List, Optional, Set, Tuple

import networkx as nx

from qse.scanner import ClassInfo, StaticAnalysis

ClassFilter = Callable[[ClassInfo], bool]


def detect_data_only(analysis: StaticAnalysis,
                     repo_dir: str,
                     entity_filter: ClassFilter) -> Set[str]:
    """Detect data-only classes (only __init__, no business methods).

    entity_filter selects which classes to check (e.g. domain entities).
    """
    result = set()
    for cls in analysis.classes.values():
        if entity_filter(cls) and cls.n_init_only and not cls.is_exception:
            result.add(os.path.relpath(cls.file_path, repo_dir))
    return result


def detect_god_class(analysis: StaticAnalysis,
                     repo_dir: str,
                     target_filter: ClassFilter,
                     threshold: int = 8,
                     steepness: float = 1.0) -> Set[str]:
    """Detect god classes (too many methods) using sigmoid scoring.

    Returns files with penalty > 0.5.
    target_filter selects which classes to check (e.g. application services).
    """
    result = set()
    for cls in analysis.classes.values():
        if target_filter(cls):
            penalty = 1.0 / (1.0 + math.exp(-steepness * (cls.n_methods - threshold)))
            if penalty > 0.5:
                result.add(os.path.relpath(cls.file_path, repo_dir))
    return result


def _normalize_name(name: str) -> str:
    """Normalize class/module name for matching."""
    return name.lower().replace("_", "")


def detect_dead_class(analysis: StaticAnalysis,
                      graph: nx.DiGraph,
                      repo_dir: str,
                      entity_filter: ClassFilter,
                      consumer_filter: ClassFilter) -> Set[str]:
    """Detect dead (zombie) classes not referenced by any consumer.

    entity_filter selects which classes are "entities" to check.
    consumer_filter selects which classes are "consumers" that should reference entities.
    """
    all_entities = {cls.name for cls in analysis.classes.values()
                    if entity_filter(cls)}
    referenced = set()

    def _matches(entity_name: str, dep_string: str) -> bool:
        norm_entity = _normalize_name(entity_name)
        norm_segments = {_normalize_name(s)
                         for s in dep_string.replace(".", " ").replace("/", " ").split()}
        return norm_entity in norm_segments

    # Check consumer classes for references
    for cls in analysis.classes.values():
        if consumer_filter(cls):
            for dep in cls.dependencies:
                for ename in all_entities:
                    if _matches(ename, dep):
                        referenced.add(ename)

    # Check graph edges
    for u, v in graph.edges():
        for ename in all_entities:
            if _matches(ename, v):
                referenced.add(ename)

    # Transitive: entity-to-entity references
    changed = True
    while changed:
        changed = False
        for cls in analysis.classes.values():
            if entity_filter(cls) and cls.name in referenced:
                for dep in cls.dependencies:
                    for ename in all_entities:
                        if _matches(ename, dep) and ename not in referenced:
                            referenced.add(ename)
                            changed = True

    result = set()
    for cls in analysis.classes.values():
        if entity_filter(cls) and cls.name not in referenced:
            result.add(os.path.relpath(cls.file_path, repo_dir))
    return result


def detect_policy_violations(analysis: StaticAnalysis,
                             repo_dir: str,
                             layer_order: Dict[str, int]) -> Set[str]:
    """Detect files with dependency direction violations.

    layer_order maps layer names to ordinals (lower = inner).
    Inner importing outer = violation.
    """
    violations: List[Tuple[str, str, str, str]] = []
    for src, tgt in analysis.graph.edges():
        src_layer = analysis.graph.nodes.get(src, {}).get("layer")
        tgt_layer = analysis.graph.nodes.get(tgt, {}).get("layer")
        if src_layer is None or tgt_layer is None:
            continue
        src_ord = layer_order.get(src_layer, -1)
        tgt_ord = layer_order.get(tgt_layer, -1)
        if src_ord < 0 or tgt_ord < 0:
            continue
        if src_ord < tgt_ord:
            violations.append((src, tgt, src_layer, tgt_layer))

    result = set()
    for src, tgt, sl, tl in violations:
        node_data = analysis.graph.nodes.get(src, {})
        if "file" in node_data:
            result.add(os.path.relpath(node_data["file"], repo_dir))
    return result


def detect_all(analysis: StaticAnalysis,
               graph: nx.DiGraph,
               repo_dir: str,
               entity_filter: ClassFilter,
               consumer_filter: ClassFilter,
               target_filter: ClassFilter,
               layer_order: Dict[str, int],
               fat_threshold: int = 8,
               fat_steepness: float = 1.0) -> Dict[str, Set[str]]:
    """Run all universal defect detectors."""
    return {
        "data_only_class": detect_data_only(analysis, repo_dir, entity_filter),
        "god_class": detect_god_class(analysis, repo_dir, target_filter,
                                      fat_threshold, fat_steepness),
        "dead_class": detect_dead_class(analysis, graph, repo_dir,
                                        entity_filter, consumer_filter),
        "policy_violation": detect_policy_violations(analysis, repo_dir,
                                                     layer_order),
    }
