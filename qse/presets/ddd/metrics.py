"""
DDD sub-metrics: S (structure), T_ddd (conformance), G (coupling),
E (excess complexity), Risk(t) (temporal risk).

Thin wrapper over universal qse.metrics — applies DDD-specific ClassFilters.
All metrics normalized to [0, 1] where 1 = best quality.
"""

from dataclasses import dataclass
from typing import List

import networkx as nx

from qse.scanner import LAYER_ORDER, StaticAnalysis
from qse import metrics as _u

# --- Fixed hyperparameters (backward-compat re-exports) ---
TAU_SEM = 0.1
BETA = _u.BETA
ALPHA = _u.ALPHA
GAMMA = _u.GAMMA


# DDD ClassFilters
def _is_domain(c) -> bool:
    return c.layer == "domain"

def _is_not_domain(c) -> bool:
    return c.layer != "domain"

def _is_application(c) -> bool:
    return c.layer == "application"


@dataclass
class SubMetrics:
    """All QSE sub-metrics for a single repository snapshot (DDD names)."""
    S: float      # Structural quality [0,1]: 1 = good modularity
    T_ddd: float  # DDD conformance [0,1]: 1 = fully conformant
    G: float      # Graph quality [0,1]: 1 = low coupling
    E: float      # Excess complexity (inverted) [0,1]: 1 = no excess
    Risk: float   # Risk (inverted) [0,1]: 1 = no risk

    def as_vector(self) -> List[float]:
        return [self.S, self.T_ddd, self.G, self.E, self.Risk]


def compute_S(analysis: StaticAnalysis) -> float:
    """Structural quality: ratio of non-anemic domain entities."""
    return _u.compute_richness(analysis, _is_domain)


def compute_T_ddd(analysis: StaticAnalysis, G: nx.DiGraph) -> float:
    """DDD conformance score (layer + zombie + naming)."""
    return _u.compute_compliance(
        analysis, G, LAYER_ORDER,
        entity_filter=_is_domain,
        consumer_filter=_is_not_domain,
    )


def compute_G(G: nx.DiGraph) -> float:
    """Graph coupling quality (inverted)."""
    return _u.compute_coupling(G, BETA)


def compute_E(analysis: StaticAnalysis,
              fat_threshold: int = 8,
              fat_steepness: float = 1.0) -> float:
    """Excess complexity (inverted) for application services."""
    return _u.compute_complexity(analysis, _is_application,
                                 fat_threshold, fat_steepness)


def compute_Risk(delta_complexity: float = 0.0,
                 delta_structure: float = 0.0) -> float:
    """Temporal risk bounded via tanh (inverted)."""
    return _u.compute_risk(delta_complexity, delta_structure)


def compute_all_metrics(analysis: StaticAnalysis, G: nx.DiGraph,
                        delta_complexity: float = 0.0,
                        delta_structure: float = 0.0,
                        fat_threshold: int = 8,
                        fat_steepness: float = 1.0) -> SubMetrics:
    """Compute all DDD sub-metrics for a repository snapshot."""
    return SubMetrics(
        S=compute_S(analysis),
        T_ddd=compute_T_ddd(analysis, G),
        G=compute_G(G),
        E=compute_E(analysis, fat_threshold, fat_steepness),
        Risk=compute_Risk(delta_complexity, delta_structure),
    )
