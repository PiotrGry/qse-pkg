"""DDD defect detectors — thin wrappers over universal qse.detectors."""

import os
from typing import Dict, Set

import networkx as nx

from qse.scanner import LAYER_ORDER, StaticAnalysis
from qse.presets.ddd.config import QSEConfig
from qse.presets.ddd.symbol_map import detect_zombie_v2
from qse import detectors as _u


# DDD ClassFilters
def _is_domain(c) -> bool:
    return c.layer == "domain"

def _is_domain_no_exc(c) -> bool:
    return c.layer == "domain" and not c.is_exception

def _is_not_domain(c) -> bool:
    return c.layer != "domain"

def _is_application(c) -> bool:
    return c.layer == "application"


def detect_anemic(analysis: StaticAnalysis, repo_dir: str) -> Set[str]:
    """Detect anemic domain entities (only __init__, no domain methods)."""
    return _u.detect_data_only(analysis, repo_dir, _is_domain)


def detect_fat(analysis: StaticAnalysis, repo_dir: str,
               threshold: int = 8, steepness: float = 1.0) -> Set[str]:
    """Detect fat services using sigmoid scoring. Returns files with penalty > 0.5."""
    return _u.detect_god_class(analysis, repo_dir, _is_application,
                                threshold, steepness)


def _normalize_name(name: str) -> str:
    """Normalize class/module name for matching: LineItem -> lineitem, line_item -> lineitem."""
    return name.lower().replace("_", "")


def detect_zombie(analysis: StaticAnalysis, graph: nx.DiGraph,
                  repo_dir: str) -> Set[str]:
    """Detect zombie domain entities not referenced by any service."""
    return _u.detect_dead_class(analysis, graph, repo_dir,
                                 _is_domain_no_exc, _is_not_domain)


def detect_layer_violations_set(analysis: StaticAnalysis, graph: nx.DiGraph,
                                repo_dir: str) -> Set[str]:
    """Detect files with layer violations."""
    return _u.detect_policy_violations(analysis, repo_dir, LAYER_ORDER)


def detect_all(analysis: StaticAnalysis, graph: nx.DiGraph,
               repo_dir: str, config: QSEConfig = None) -> Dict[str, Set[str]]:
    """Run all defect detectors. Returns {defect_type: set_of_files}.

    Zombie detection uses v2 (AST symbol-map, F1=0.964) when a domain/
    directory exists; falls back to v1 (string matching) otherwise.
    """
    if config is None:
        config = QSEConfig()

    layer_map = config.layer_map if config else {}
    # v2 when any directory maps to "domain" (including via layer_map)
    domain_dirs = [os.path.join(repo_dir, d) for d, l in (layer_map or {}).items() if l == "domain"]
    domain_dirs.append(os.path.join(repo_dir, "domain"))
    if any(os.path.isdir(d) for d in domain_dirs):
        zombie = detect_zombie_v2(repo_dir, mode="conservative", layer_map=layer_map or None)
    else:
        zombie = detect_zombie(analysis, graph, repo_dir)

    return {
        "anemic_entity": detect_anemic(analysis, repo_dir),
        "fat_service": detect_fat(analysis, repo_dir,
                                  config.fat_threshold, config.fat_steepness),
        "zombie_entity": zombie,
        "layer_violation": detect_layer_violations_set(analysis, graph, repo_dir),
    }
