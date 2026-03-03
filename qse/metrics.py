"""
QSE sub-metrics: S (structure), T_ddd (DDD conformance), G (graph coupling),
E (excess complexity), Risk(t) (temporal risk).

All metrics are normalized to [0, 1] where 1 = best quality.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

import networkx as nx

from qse.scanner import StaticAnalysis, ClassInfo, LAYER_ORDER


@dataclass
class SubMetrics:
    """All QSE sub-metrics for a single repository snapshot."""
    S: float      # Structural quality [0,1]: 1 = good modularity
    T_ddd: float  # DDD conformance [0,1]: 1 = fully conformant
    G: float      # Graph quality [0,1]: 1 = low coupling
    E: float      # Excess complexity (inverted) [0,1]: 1 = no excess
    Risk: float   # Risk (inverted) [0,1]: 1 = no risk

    def as_vector(self) -> List[float]:
        return [self.S, self.T_ddd, self.G, self.E, self.Risk]


# --- Fixed hyperparameters (stated explicitly per paper requirements) ---
TAU_SEM = 0.1     # Semantic similarity threshold for DDD naming
BETA = 3.0        # Sigmoid steepness for coupling normalization
ALPHA = (1/3, 1/3, 1/3)  # Weights for T_ddd sub-components
GAMMA = (0.5, 0.5)       # Weights for Risk sub-components


def compute_S(analysis: StaticAnalysis) -> float:
    """
    Structural quality: ratio of non-anemic entities.

    S = 1 - (n_anemic / n_total_entities)

    An entity is anemic if it has only __init__ and no domain methods.
    """
    entities = [c for c in analysis.classes.values() if c.layer == "domain"]
    if not entities:
        return 1.0
    n_anemic = sum(1 for e in entities if e.n_init_only)
    return 1.0 - (n_anemic / len(entities))


def compute_T_ddd(analysis: StaticAnalysis, G: nx.DiGraph) -> float:
    """
    DDD conformance score, combines:
    - T_layer: fraction of edges that respect layering
    - T_zombie: fraction of entities that are referenced
    - T_naming: fraction of entities with domain-appropriate naming (simplified)

    T_ddd = α₁·T_layer + α₂·T_zombie + α₃·T_naming
    """
    # T_layer: fraction of presentation-layer nodes that do NOT violate layering
    # (measured per-file, not per-edge, so violations aren't diluted by total edge count)
    presentation_nodes = {n for n, d in G.nodes(data=True) if d.get("layer") == "presentation"}
    violating_nodes = set()
    for src, tgt in G.edges():
        src_layer = G.nodes.get(src, {}).get("layer")
        tgt_layer = G.nodes.get(tgt, {}).get("layer")
        if src_layer == "presentation" and tgt_layer == "domain":
            violating_nodes.add(src)
    T_layer = 1.0 - (len(violating_nodes) / max(len(presentation_nodes), 1))

    # T_zombie: fraction of domain entities referenced by at least one service
    domain_entities = {c.name for c in analysis.classes.values() if c.layer == "domain"}
    referenced = set()
    for cls in analysis.classes.values():
        if cls.layer != "domain":
            for dep in cls.dependencies:
                # Check if any domain entity name appears in the import
                for ename in domain_entities:
                    if ename.lower() in dep.lower():
                        referenced.add(ename)
    T_zombie = len(referenced) / max(len(domain_entities), 1)

    # T_naming: DDD naming convention checker
    # Domain entities should be nouns (no action verb prefixes)
    # Services (application layer) should contain action verbs
    _ACTION_PREFIXES = ("get", "set", "do", "handle", "process", "run", "execute")
    _SERVICE_VERBS = ("create", "update", "delete", "process", "handle", "run",
                      "execute", "manage", "build", "send", "validate", "compute")
    all_classes = analysis.classes
    named_correctly = 0
    named_total = 0
    for cls in all_classes.values():
        if cls.layer == "domain":
            named_total += 1
            name_lower = cls.name.lower()
            if not any(name_lower.startswith(p) for p in _ACTION_PREFIXES):
                named_correctly += 1
        elif cls.layer == "application":
            named_total += 1
            name_lower = cls.name.lower()
            if any(v in name_lower for v in _SERVICE_VERBS):
                named_correctly += 1
    if named_total > 0:
        naming_score = named_correctly / named_total
        # TAU_SEM is the minimum acceptable naming score.
        # Below it, penalize proportionally. Above it, scale to [0,1].
        if naming_score >= 1.0:
            T_naming = 1.0
        else:
            T_naming = naming_score
    else:
        T_naming = 1.0

    return ALPHA[0] * T_layer + ALPHA[1] * T_zombie + ALPHA[2] * T_naming


def compute_G(G: nx.DiGraph) -> float:
    """
    Graph coupling quality (inverted coupling).

    G = 1 / (1 + exp(β · (density - 0.5)))

    Where density = edges / (nodes * (nodes-1)), normalized via sigmoid.
    High density → low quality. β controls steepness.
    """
    n = G.number_of_nodes()
    if n <= 1:
        return 1.0
    max_edges = n * (n - 1)
    density = G.number_of_edges() / max_edges
    # Sigmoid: maps density to quality; density=0 → ~1, density=1 → ~0
    return 1.0 / (1.0 + math.exp(BETA * (density - 0.5)))


def compute_E(analysis: StaticAnalysis,
              fat_threshold: int = 8,
              fat_steepness: float = 1.0) -> float:
    """
    Excess complexity (inverted) with smooth sigmoid penalty.

    Per-service penalty: σ(steepness · (n_methods - threshold)).
    E = 1 - mean(penalties).
    """
    services = [c for c in analysis.classes.values() if c.layer == "application"]
    if not services:
        return 1.0
    penalties = []
    for s in services:
        penalties.append(1.0 / (1.0 + math.exp(-fat_steepness * (s.n_methods - fat_threshold))))
    return 1.0 - (sum(penalties) / len(penalties))


def compute_Risk(delta_complexity: float = 0.0,
                 delta_structure: float = 0.0) -> float:
    """
    Temporal risk bounded via tanh: Risk(t) = tanh(|ΔC| + |ΔS|).

    Returns inverted risk (1 - risk) so that higher = better quality.
    Risk ∈ [0, 1), so inverted ∈ (0, 1].
    """
    raw = math.tanh(abs(delta_complexity) + abs(delta_structure))
    return 1.0 - raw


def compute_all_metrics(analysis: StaticAnalysis, G: nx.DiGraph,
                        delta_complexity: float = 0.0,
                        delta_structure: float = 0.0,
                        fat_threshold: int = 8,
                        fat_steepness: float = 1.0) -> SubMetrics:
    """Compute all sub-metrics for a repository snapshot."""
    return SubMetrics(
        S=compute_S(analysis),
        T_ddd=compute_T_ddd(analysis, G),
        G=compute_G(G),
        E=compute_E(analysis, fat_threshold, fat_steepness),
        Risk=compute_Risk(delta_complexity, delta_structure),
    )
