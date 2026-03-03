"""
Weight calibration via L-BFGS-B with leave-one-out cross-validation.

Optimizes weights w to minimize MSE between QSE_total predictions
and ground truth quality scores, subject to w_i ≥ 0, Σw_i = 1.
"""

import numpy as np
from scipy.optimize import minimize
from typing import List, Tuple

from qse.metrics import SubMetrics
from qse.aggregator import normalize_weights, DEFAULT_WEIGHTS


def _objective(w_raw: np.ndarray, M: np.ndarray, y: np.ndarray) -> float:
    """
    MSE loss with simplex projection.

    w_raw is unconstrained; we project onto simplex before computing loss.
    """
    w = np.maximum(w_raw, 0.0)
    s = np.sum(w)
    if s < 1e-12:
        return 1e6
    w = w / s
    preds = np.clip(M @ w, 0.0, 1.0)
    return float(np.mean((preds - y) ** 2))


def calibrate_weights(metrics_list: List[SubMetrics],
                      ground_truth: np.ndarray,
                      n_restarts: int = 5) -> np.ndarray:
    """
    Calibrate weights using L-BFGS-B with multiple random restarts.

    Args:
        metrics_list: Sub-metrics for each data point
        ground_truth: Target quality scores in [0, 1]
        n_restarts: Number of random initializations

    Returns:
        Optimized weight vector (normalized to sum to 1)
    """
    M = np.array([m.as_vector() for m in metrics_list])
    y = np.asarray(ground_truth)
    n_metrics = M.shape[1]

    best_w = DEFAULT_WEIGHTS.copy()
    best_loss = _objective(best_w, M, y)

    rng = np.random.RandomState(42)
    for _ in range(n_restarts):
        w0 = rng.dirichlet(np.ones(n_metrics))
        result = minimize(
            _objective, w0, args=(M, y),
            method="L-BFGS-B",
            bounds=[(0.0, 1.0)] * n_metrics,
            options={"maxiter": 200},
        )
        if result.fun < best_loss:
            best_loss = result.fun
            best_w = result.x.copy()

    return normalize_weights(best_w)


def leave_one_out_cv(metrics_list: List[SubMetrics],
                     ground_truth: np.ndarray) -> Tuple[float, float, np.ndarray]:
    """
    Leave-one-out cross-validation for weight calibration.

    Returns:
        (mean_mse, std_mse, mean_weights)
    """
    M = np.array([m.as_vector() for m in metrics_list])
    y = np.asarray(ground_truth)
    n = len(y)

    errors = []
    all_weights = []

    for i in range(n):
        # Leave out sample i
        M_train = np.delete(M, i, axis=0)
        y_train = np.delete(y, i)
        M_test = M[i:i+1]
        y_test = y[i]

        # Build SubMetrics from rows
        train_metrics = [
            SubMetrics(*M_train[j]) for j in range(len(M_train))
        ]
        w = calibrate_weights(train_metrics, y_train, n_restarts=3)
        all_weights.append(w)

        pred = float(np.clip(M_test @ w, 0.0, 1.0))
        errors.append((pred - y_test) ** 2)

    errors = np.array(errors)
    weights_arr = np.array(all_weights)
    return float(np.mean(errors)), float(np.std(errors)), np.mean(weights_arr, axis=0)
