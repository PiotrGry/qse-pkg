"""
DDD aggregator — thin re-export from universal qse.aggregator.

Backward compatibility: all existing imports from qse.presets.ddd.aggregator still work.

QSE_total = Σ w_i · m_i, clamped to [0, 1]
where w_i ≥ 0, Σ w_i = 1, and all m_i ∈ [0, 1].
"""

# Re-export everything from universal aggregator
from qse.aggregator import (  # noqa: F401
    DEFAULT_WEIGHTS,
    METRIC_NAMES,
    validate_weights,
    normalize_weights,
    compute_qse_total,
    compute_qse_batch,
)
