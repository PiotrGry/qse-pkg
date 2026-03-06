"""Unit tests for QSE metric boundedness and weight invariants."""

import math
import numpy as np
import pytest

from qse.presets.ddd.metrics import (
    compute_S, compute_G, compute_E, compute_Risk, SubMetrics,
)
from qse.presets.ddd.aggregator import (
    compute_qse_total, validate_weights, normalize_weights, DEFAULT_WEIGHTS,
)


class TestMetricBoundedness:
    """All sub-metrics must return values in [0, 1]."""

    def test_risk_bounded_zero_input(self):
        r = compute_Risk(0.0, 0.0)
        assert 0.0 <= r <= 1.0

    def test_risk_bounded_large_input(self):
        r = compute_Risk(100.0, 100.0)
        assert 0.0 <= r <= 1.0

    def test_risk_bounded_negative_input(self):
        r = compute_Risk(-5.0, -3.0)
        assert 0.0 <= r <= 1.0

    def test_risk_monotonic(self):
        """Higher deltas should produce lower quality (higher risk)."""
        r1 = compute_Risk(0.1, 0.1)
        r2 = compute_Risk(1.0, 1.0)
        assert r1 > r2  # Less change = higher quality

    def test_compute_G_empty_graph(self):
        """G with <=1 node should return 1.0."""
        import networkx as nx
        G = nx.DiGraph()
        G.add_node("a")
        assert compute_G(G) == 1.0

    def test_compute_G_bounded(self):
        import networkx as nx
        G = nx.complete_graph(20, create_using=nx.DiGraph)
        val = compute_G(G)
        assert 0.0 <= val <= 1.0


class TestSubMetrics:
    def test_as_vector_length(self):
        m = SubMetrics(0.5, 0.6, 0.7, 0.8, 0.9)
        assert len(m.as_vector()) == 5

    def test_as_vector_values(self):
        m = SubMetrics(0.1, 0.2, 0.3, 0.4, 0.5)
        assert m.as_vector() == [0.1, 0.2, 0.3, 0.4, 0.5]


class TestQSETotal:
    def test_bounded_with_default_weights(self):
        m = SubMetrics(0.5, 0.6, 0.7, 0.8, 0.9)
        qse = compute_qse_total(m)
        assert 0.0 <= qse <= 1.0

    def test_bounded_extreme_low(self):
        m = SubMetrics(0.0, 0.0, 0.0, 0.0, 0.0)
        assert compute_qse_total(m) == 0.0

    def test_bounded_extreme_high(self):
        m = SubMetrics(1.0, 1.0, 1.0, 1.0, 1.0)
        assert compute_qse_total(m) == 1.0

    def test_custom_weights(self):
        m = SubMetrics(1.0, 0.0, 0.0, 0.0, 0.0)
        w = np.array([1.0, 0.0, 0.0, 0.0, 0.0])
        assert compute_qse_total(m, w) == 1.0

    def test_qse_total_never_exceeds_one(self):
        """Even with adversarial weights, clamping ensures [0,1]."""
        m = SubMetrics(1.0, 1.0, 1.0, 1.0, 1.0)
        w = np.array([0.5, 0.5, 0.5, 0.5, 0.5])  # sum > 1
        qse = compute_qse_total(m, w)
        assert qse <= 1.0


class TestSigmoidFat:
    """Test that compute_E uses smooth sigmoid instead of binary cliff."""

    def _make_analysis(self, method_counts):
        """Create a minimal StaticAnalysis with application-layer services."""
        from qse.scanner import StaticAnalysis, ClassInfo
        import networkx as nx
        classes = {}
        for i, n in enumerate(method_counts):
            name = f"Service{i}"
            classes[name] = ClassInfo(
                name=name, file_path=f"/tmp/app/svc{i}.py",
                layer="application", n_methods=n,
            )
        return StaticAnalysis(graph=nx.DiGraph(), classes=classes, files=[])

    def test_sigmoid_smooth_gradient(self):
        """E should change smoothly, not jump from 1.0 to 0.0."""
        scores = []
        for n in range(1, 20):
            a = self._make_analysis([n])
            scores.append(compute_E(a))
        # Check no adjacent pair jumps by more than 0.3
        for i in range(len(scores) - 1):
            assert abs(scores[i] - scores[i + 1]) < 0.3, \
                f"Cliff detected between n={i+1} and n={i+2}: {scores[i]:.3f} -> {scores[i+1]:.3f}"

    def test_sigmoid_bounded(self):
        for n in [0, 1, 5, 8, 15, 50]:
            a = self._make_analysis([n])
            e = compute_E(a)
            assert 0.0 <= e <= 1.0, f"E out of bounds for n={n}: {e}"

    def test_sigmoid_steepness_param(self):
        a = self._make_analysis([12])
        e_gentle = compute_E(a, fat_steepness=0.5)
        e_steep = compute_E(a, fat_steepness=3.0)
        # Steeper should penalize more harshly above threshold
        assert e_steep < e_gentle


class TestNamingConvention:
    """Test that T_naming uses DDD naming conventions, not len(name) > 3."""

    def _make_analysis_with_names(self, domain_names, service_names):
        from qse.scanner import StaticAnalysis, ClassInfo
        import networkx as nx
        classes = {}
        for name in domain_names:
            classes[name] = ClassInfo(
                name=name, file_path=f"/tmp/domain/{name}.py",
                layer="domain", n_methods=3,
            )
        for name in service_names:
            classes[name] = ClassInfo(
                name=name, file_path=f"/tmp/application/{name}.py",
                layer="application", n_methods=3,
            )
        return StaticAnalysis(graph=nx.DiGraph(), classes=classes, files=[])

    def test_good_naming_scores_high(self):
        from qse.presets.ddd.metrics import compute_T_ddd
        import networkx as nx
        a = self._make_analysis_with_names(
            ["Order", "Invoice", "Customer"],
            ["CreateOrderService", "UpdateInvoiceHandler"],
        )
        G = nx.DiGraph()
        t = compute_T_ddd(a, G)
        assert t > 0.0  # Should have non-trivial T_naming component

    def test_bad_domain_naming_penalized(self):
        from qse.presets.ddd.metrics import compute_T_ddd
        import networkx as nx
        # Domain entities with verb prefixes — bad naming
        a_bad = self._make_analysis_with_names(
            ["GetOrder", "ProcessInvoice", "HandleCustomer"],
            ["CreateOrderService"],
        )
        a_good = self._make_analysis_with_names(
            ["Order", "Invoice", "Customer"],
            ["CreateOrderService"],
        )
        G = nx.DiGraph()
        t_bad = compute_T_ddd(a_bad, G)
        t_good = compute_T_ddd(a_good, G)
        assert t_good > t_bad


class TestWeights:
    def test_default_weights_valid(self):
        assert validate_weights(DEFAULT_WEIGHTS)

    def test_normalize_preserves_valid(self):
        w = np.array([0.3, 0.2, 0.2, 0.2, 0.1])
        n = normalize_weights(w)
        assert abs(np.sum(n) - 1.0) < 1e-9

    def test_normalize_clips_negative(self):
        w = np.array([-0.1, 0.5, 0.3, 0.2, 0.1])
        n = normalize_weights(w)
        assert np.all(n >= 0.0)
        assert abs(np.sum(n) - 1.0) < 1e-9

    def test_normalize_zero_vector(self):
        w = np.array([0.0, 0.0, 0.0, 0.0, 0.0])
        n = normalize_weights(w)
        assert abs(np.sum(n) - 1.0) < 1e-9
