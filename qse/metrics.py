"""
Universal QSE sub-metrics: richness, compliance, coupling, complexity, risk.

Architecture-agnostic — works with any layered or non-layered codebase.
The DDD preset (qse/presets/ddd/metrics.py) delegates here with DDD-specific filters.

All metrics normalized to [0, 1] where 1 = best quality.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set

import networkx as nx

from qse.scanner import ClassInfo, StaticAnalysis


# Type alias: predicate selecting which classes to consider
ClassFilter = Callable[[ClassInfo], bool]

# --- Fixed hyperparameters ---
BETA = 3.0        # Sigmoid steepness for coupling normalization
ALPHA = (1/3, 1/3, 1/3)  # Weights for compliance sub-components
GAMMA = (0.5, 0.5)       # Weights for risk sub-components


@dataclass
class SubMetrics:
    """All QSE sub-metrics for a single repository snapshot."""
    richness: float     # [0,1]: 1 = no data-only classes among entities
    compliance: float   # [0,1]: 1 = fully conformant to layer rules
    coupling: float     # [0,1]: 1 = low coupling
    complexity: float   # [0,1]: 1 = no excess complexity
    risk: float         # [0,1]: 1 = no temporal risk

    def as_vector(self) -> List[float]:
        return [self.richness, self.compliance, self.coupling,
                self.complexity, self.risk]


def compute_richness(analysis: StaticAnalysis,
                     entity_filter: ClassFilter) -> float:
    """
    Structural quality: ratio of non-data-only entities.

    richness = 1 - (n_data_only / n_total_entities)

    An entity is data-only if it has only __init__ and no business methods.
    entity_filter selects which classes count as "entities" (e.g. domain classes).
    """
    entities = [c for c in analysis.classes.values() if entity_filter(c)]
    if not entities:
        return 1.0
    n_data_only = sum(1 for e in entities if e.n_init_only)
    return 1.0 - (n_data_only / len(entities))


def compute_compliance(analysis: StaticAnalysis,
                       graph: nx.DiGraph,
                       layer_order: Dict[str, int],
                       entity_filter: Optional[ClassFilter] = None,
                       consumer_filter: Optional[ClassFilter] = None,
                       n_constraint_violations: int = 0) -> float:
    """
    Compliance score combining:
    - T_layer: fraction of edges respecting layer ordering
    - T_zombie: fraction of entities referenced by at least one consumer
    - T_naming: fraction of entities with appropriate naming

    compliance = α₁·T_layer + α₂·T_zombie + α₃·T_naming

    layer_order: dict mapping layer names to ordinal (lower = inner).
    entity_filter: selects "entity" classes (for zombie/naming checks).
    consumer_filter: selects "consumer" classes that should reference entities.
    """
    # T_layer: fraction of layered nodes that do NOT violate dependency direction
    layered_nodes = {n for n, d in graph.nodes(data=True)
                     if d.get("layer") in layer_order}
    violating_nodes: Set[str] = set()
    for src, tgt in graph.edges():
        src_layer = graph.nodes.get(src, {}).get("layer")
        tgt_layer = graph.nodes.get(tgt, {}).get("layer")
        if src_layer is None or tgt_layer is None:
            continue
        src_ord = layer_order.get(src_layer, -1)
        tgt_ord = layer_order.get(tgt_layer, -1)
        if src_ord < 0 or tgt_ord < 0:
            continue
        # Inner layer importing outer layer = violation
        if src_ord < tgt_ord:
            violating_nodes.add(src)
    T_layer = 1.0 - (len(violating_nodes) / max(len(layered_nodes), 1))

    # T_zombie: fraction of entity classes referenced by at least one consumer
    if entity_filter is not None:
        domain_entities = {c.name for c in analysis.classes.values()
                          if entity_filter(c)}
    else:
        domain_entities = set()

    referenced: Set[str] = set()
    if domain_entities and consumer_filter is not None:
        for cls in analysis.classes.values():
            if consumer_filter(cls):
                for dep in cls.dependencies:
                    dep_segments = {s.lower()
                                    for s in dep.replace(".", " ").split()}
                    for ename in domain_entities:
                        if ename.lower() in dep_segments:
                            referenced.add(ename)
    T_zombie = len(referenced) / max(len(domain_entities), 1)

    # T_naming: naming convention check
    # Entity classes should be nouns (no action verb prefixes)
    # Consumer/service classes should contain action verbs
    _ACTION_PREFIXES = ("get", "set", "do", "handle", "process", "run", "execute")
    _SERVICE_VERBS = ("create", "update", "delete", "process", "handle", "run",
                      "execute", "manage", "build", "send", "validate", "compute")
    named_correctly = 0
    named_total = 0
    for cls in analysis.classes.values():
        if entity_filter is not None and entity_filter(cls):
            named_total += 1
            name_lower = cls.name.lower()
            if not any(name_lower.startswith(p) for p in _ACTION_PREFIXES):
                named_correctly += 1
        elif consumer_filter is not None and consumer_filter(cls):
            named_total += 1
            name_lower = cls.name.lower()
            if any(v in name_lower for v in _SERVICE_VERBS):
                named_correctly += 1
    T_naming = (named_correctly / named_total) if named_total > 0 else 1.0

    return ALPHA[0] * T_layer + ALPHA[1] * T_zombie + ALPHA[2] * T_naming


def compute_coupling(graph: nx.DiGraph, beta: float = BETA) -> float:
    """
    Graph coupling quality based on mean out-degree (fanout), size-independent.

    coupling = 1 / (1 + exp(β · (mean_out_degree - threshold)))
    threshold = 5.0  (modules with >5 direct dependencies are suspect)

    Replaces density-based formula which collapses to ≈1.0 for all large
    sparse graphs (density → 0 as N grows), providing no discrimination.
    Mean out-degree is size-independent and architecturally interpretable:
    each module's fanout counts equally regardless of total codebase size.
    """
    n = graph.number_of_nodes()
    if n <= 1:
        return 1.0
    mean_out_degree = graph.number_of_edges() / n
    threshold = 3.0  # >3 direct deps per module is suspect
    return 1.0 / (1.0 + math.exp(beta * (mean_out_degree - threshold)))


def compute_complexity(analysis: StaticAnalysis,
                       target_filter: ClassFilter,
                       threshold: int = 8,
                       steepness: float = 1.0) -> float:
    """
    Excess complexity (inverted) with smooth sigmoid penalty.

    Per-class penalty: σ(steepness · (n_methods - threshold)).
    complexity = 1 - mean(penalties).

    target_filter selects which classes to check (e.g. application services).
    """
    targets = [c for c in analysis.classes.values() if target_filter(c)]
    if not targets:
        return 1.0
    penalties = []
    for c in targets:
        penalties.append(
            1.0 / (1.0 + math.exp(-steepness * (c.n_methods - threshold)))
        )
    return 1.0 - (sum(penalties) / len(penalties))


def compute_risk(delta_complexity: float = 0.0,
                 delta_structure: float = 0.0) -> float:
    """
    Temporal risk bounded via tanh: risk = tanh(|ΔC| + |ΔS|).

    Returns inverted (1 - risk) so higher = better quality.
    """
    raw = math.tanh(abs(delta_complexity) + abs(delta_structure))
    return 1.0 - raw


def compute_all_metrics(analysis: StaticAnalysis,
                        graph: nx.DiGraph,
                        layer_order: Dict[str, int],
                        entity_filter: Optional[ClassFilter] = None,
                        consumer_filter: Optional[ClassFilter] = None,
                        target_filter: Optional[ClassFilter] = None,
                        delta_complexity: float = 0.0,
                        delta_structure: float = 0.0,
                        fat_threshold: int = 8,
                        fat_steepness: float = 1.0,
                        beta: float = BETA) -> SubMetrics:
    """Compute all universal sub-metrics for a repository snapshot."""
    # Default filters: include all classes
    _all = lambda c: True
    ef = entity_filter or _all
    cf = consumer_filter or (lambda c: not ef(c))
    tf = target_filter or _all

    return SubMetrics(
        richness=compute_richness(analysis, ef),
        compliance=compute_compliance(analysis, graph, layer_order,
                                      entity_filter=ef,
                                      consumer_filter=cf),
        coupling=compute_coupling(graph, beta),
        complexity=compute_complexity(analysis, tf, fat_threshold, fat_steepness),
        risk=compute_risk(delta_complexity, delta_structure),
    )
