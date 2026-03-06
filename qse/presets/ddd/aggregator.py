"""
QSE_total aggregation with proper bounds and weight constraints.

QSE_total = Σ w_i · m_i, clamped to [0, 1]
where w_i ≥ 0, Σ w_i = 1, and all m_i ∈ [0, 1].

λ is absorbed into the weight vector (no separate penalty term).
"""

import numpy as np
from typing import List, Optional

from qse.presets.ddd.metrics import SubMetrics

# Default equal weights (5 metrics)
DEFAULT_WEIGHTS = np.array([0.2, 0.2, 0.2, 0.2, 0.2])

METRIC_NAMES = ["S", "T_ddd", "G", "E", "Risk"]


def validate_weights(w: np.ndarray) -> bool:
    """Check weight constraints: w_i >= 0, sum(w) = 1."""
    return np.all(w >= -1e-9) and abs(np.sum(w) - 1.0) < 1e-6


def normalize_weights(w: np.ndarray) -> np.ndarray:
    """Project weights onto the probability simplex."""
    w = np.maximum(w, 0.0)
    s = np.sum(w)
    if s < 1e-12:
        return DEFAULT_WEIGHTS.copy()
    return w / s


def compute_qse_total(metrics: SubMetrics,
                      weights: Optional[np.ndarray] = None) -> float:
    """
    Compute QSE_total = Σ w_i · m_i, clamped to [0, 1].

    All sub-metrics are already in [0, 1] (Risk and E are inverted).
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
    m = np.array(metrics.as_vector())
    raw = float(np.dot(weights, m))
    return max(0.0, min(1.0, raw))


def compute_qse_batch(metrics_list: List[SubMetrics],
                      weights: Optional[np.ndarray] = None) -> np.ndarray:
    """Compute QSE_total for a batch of metric vectors."""
    if weights is None:
        weights = DEFAULT_WEIGHTS
    M = np.array([m.as_vector() for m in metrics_list])
    raw = M @ weights
    return np.clip(raw, 0.0, 1.0)
