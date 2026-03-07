"""Tests for universal (architecture-agnostic) metrics, aggregator, and detectors."""

import os
import math

import networkx as nx
import numpy as np
import pytest

from qse.scanner import ClassInfo, StaticAnalysis
from qse.metrics import (
    SubMetrics, compute_richness, compute_compliance,
    compute_coupling, compute_complexity, compute_risk,
    compute_all_metrics, BETA,
)
from qse.aggregator import (
    DEFAULT_WEIGHTS, METRIC_NAMES, validate_weights,
    normalize_weights, compute_qse_total, compute_qse_batch,
)
from qse.detectors import (
    detect_data_only, detect_god_class, detect_dead_class,
    detect_policy_violations, detect_all,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_class(name, layer="domain", n_methods=2, n_init_only=False,
                is_exception=False, is_abstract=False, file_path=None,
                dependencies=None, method_attrs=None):
    return ClassInfo(
        name=name,
        file_path=file_path or f"/repo/{layer}/{name.lower()}.py",
        layer=layer,
        n_methods=n_methods,
        n_init_only=n_init_only,
        is_exception=is_exception,
        is_abstract=is_abstract,
        dependencies=dependencies or [],
        method_attrs=method_attrs or [],
    )


def _make_analysis(classes, graph=None):
    g = graph or nx.DiGraph()
    return StaticAnalysis(
        graph=g,
        classes={c.name: c for c in classes},
        files=[c.file_path for c in classes],
    )


# ---------------------------------------------------------------------------
# Universal Metrics
# ---------------------------------------------------------------------------

class TestRichness:
    def test_all_rich(self):
        """All entities have methods → richness=1.0."""
        classes = [_make_class("Order", n_methods=3, n_init_only=False)]
        analysis = _make_analysis(classes)
        assert compute_richness(analysis, lambda c: c.layer == "domain") == 1.0

    def test_all_data_only(self):
        """All entities are data-only → richness=0.0."""
        classes = [_make_class("Order", n_methods=1, n_init_only=True)]
        analysis = _make_analysis(classes)
        assert compute_richness(analysis, lambda c: c.layer == "domain") == 0.0

    def test_mixed(self):
        classes = [
            _make_class("Order", n_methods=3, n_init_only=False),
            _make_class("Item", n_methods=1, n_init_only=True),
        ]
        analysis = _make_analysis(classes)
        assert compute_richness(analysis, lambda c: c.layer == "domain") == 0.5

    def test_no_matching_classes(self):
        """No classes match filter → richness=1.0 (vacuously true)."""
        classes = [_make_class("Svc", layer="application")]
        analysis = _make_analysis(classes)
        assert compute_richness(analysis, lambda c: c.layer == "domain") == 1.0

    def test_custom_filter(self):
        """Custom filter works on non-DDD architectures."""
        classes = [
            _make_class("User", layer="model", n_methods=3, n_init_only=False),
            _make_class("Config", layer="model", n_methods=1, n_init_only=True),
        ]
        analysis = _make_analysis(classes)
        assert compute_richness(analysis, lambda c: c.layer == "model") == 0.5


class TestCompliance:
    def test_no_violations(self):
        G = nx.DiGraph()
        G.add_node("app.svc", layer="application")
        G.add_node("domain.order", layer="domain")
        G.add_edge("app.svc", "domain.order")
        layer_order = {"domain": 0, "application": 1}

        classes = [
            _make_class("Order", layer="domain", dependencies=["domain.order"]),
            _make_class("Svc", layer="application", dependencies=["domain.order"]),
        ]
        analysis = _make_analysis(classes, G)
        score = compute_compliance(
            analysis, G, layer_order,
            entity_filter=lambda c: c.layer == "domain",
            consumer_filter=lambda c: c.layer == "application",
        )
        # T_layer=1.0,  T_zombie=1.0 (Order referenced by Svc), T_naming varies
        assert 0.0 <= score <= 1.0

    def test_violation_detected(self):
        G = nx.DiGraph()
        G.add_node("domain.order", layer="domain")
        G.add_node("infra.db", layer="infrastructure")
        G.add_edge("domain.order", "infra.db")  # inner→outer violation
        layer_order = {"domain": 0, "infrastructure": 2}

        classes = [_make_class("Order", layer="domain")]
        analysis = _make_analysis(classes, G)
        score = compute_compliance(analysis, G, layer_order)
        # T_layer < 1.0 due to violation
        assert score < 1.0

    def test_custom_layer_order(self):
        """Non-DDD layer ordering works."""
        G = nx.DiGraph()
        G.add_node("core.entity", layer="core")
        G.add_node("api.handler", layer="api")
        G.add_edge("core.entity", "api.handler")  # core→api = violation
        layer_order = {"core": 0, "api": 1}
        analysis = _make_analysis([], G)
        score = compute_compliance(analysis, G, layer_order)
        assert score < 1.0


class TestCoupling:
    def test_single_node(self):
        G = nx.DiGraph()
        G.add_node("a")
        assert compute_coupling(G) == 1.0

    def test_sparse_graph(self):
        G = nx.DiGraph()
        for i in range(10):
            G.add_node(f"m{i}")
        G.add_edge("m0", "m1")
        score = compute_coupling(G)
        assert score > 0.8

    def test_dense_graph(self):
        G = nx.DiGraph()
        nodes = [f"m{i}" for i in range(5)]
        for n in nodes:
            G.add_node(n)
        for a in nodes:
            for b in nodes:
                if a != b:
                    G.add_edge(a, b)
        score = compute_coupling(G)
        assert score < 0.3

    def test_bounds(self):
        G = nx.DiGraph()
        G.add_nodes_from(["a", "b", "c"])
        G.add_edge("a", "b")
        score = compute_coupling(G)
        assert 0.0 <= score <= 1.0


class TestComplexity:
    def test_no_targets(self):
        analysis = _make_analysis([_make_class("Order", layer="domain")])
        assert compute_complexity(analysis, lambda c: c.layer == "application") == 1.0

    def test_fat_classes_detected(self):
        classes = [_make_class("BigSvc", layer="application", n_methods=15)]
        analysis = _make_analysis(classes)
        score = compute_complexity(analysis, lambda c: c.layer == "application")
        assert score < 0.5

    def test_slim_classes_pass(self):
        classes = [_make_class("SmallSvc", layer="application", n_methods=3)]
        analysis = _make_analysis(classes)
        score = compute_complexity(analysis, lambda c: c.layer == "application")
        assert score > 0.5


class TestRisk:
    def test_zero_delta(self):
        assert compute_risk(0.0, 0.0) == 1.0

    def test_high_delta(self):
        score = compute_risk(5.0, 5.0)
        assert score < 0.1

    def test_bounds(self):
        for dc in [0.0, 0.5, 1.0, 5.0]:
            for ds in [0.0, 0.5, 1.0, 5.0]:
                score = compute_risk(dc, ds)
                assert 0.0 <= score <= 1.0


class TestSubMetrics:
    def test_as_vector(self):
        m = SubMetrics(richness=0.8, compliance=0.7, coupling=0.9,
                       complexity=0.85, risk=1.0)
        assert m.as_vector() == [0.8, 0.7, 0.9, 0.85, 1.0]


class TestComputeAllMetrics:
    def test_returns_sub_metrics(self):
        G = nx.DiGraph()
        G.add_node("domain.order", layer="domain")
        G.add_node("app.svc", layer="application")
        G.add_edge("app.svc", "domain.order")
        classes = [
            _make_class("Order", layer="domain", n_methods=3),
            _make_class("Svc", layer="application", n_methods=4),
        ]
        analysis = _make_analysis(classes, G)
        layer_order = {"domain": 0, "application": 1}
        m = compute_all_metrics(
            analysis, G, layer_order,
            entity_filter=lambda c: c.layer == "domain",
            consumer_filter=lambda c: c.layer == "application",
            target_filter=lambda c: c.layer == "application",
        )
        assert isinstance(m, SubMetrics)
        for v in m.as_vector():
            assert 0.0 <= v <= 1.0


# ---------------------------------------------------------------------------
# Universal Aggregator
# ---------------------------------------------------------------------------

class TestUniversalAggregator:
    def test_default_weights(self):
        assert len(DEFAULT_WEIGHTS) == 5
        assert abs(sum(DEFAULT_WEIGHTS) - 1.0) < 1e-6

    def test_metric_names(self):
        assert METRIC_NAMES == ["richness", "compliance", "coupling",
                                "complexity", "risk"]

    def test_validate_weights(self):
        assert validate_weights(np.array([0.2, 0.2, 0.2, 0.2, 0.2]))
        assert not validate_weights(np.array([0.5, 0.5, 0.5, 0.0, 0.0]))

    def test_normalize_weights(self):
        w = normalize_weights(np.array([-1.0, 0.0, 0.0, 0.0, 0.0]))
        assert np.all(w >= 0.0)
        assert abs(sum(w) - 1.0) < 1e-6

    def test_compute_qse_total(self):
        m = SubMetrics(richness=1.0, compliance=1.0, coupling=1.0,
                       complexity=1.0, risk=1.0)
        assert compute_qse_total(m) == 1.0

    def test_compute_qse_total_zero(self):
        m = SubMetrics(richness=0.0, compliance=0.0, coupling=0.0,
                       complexity=0.0, risk=0.0)
        assert compute_qse_total(m) == 0.0

    def test_compute_qse_total_custom_weights(self):
        m = SubMetrics(richness=1.0, compliance=0.0, coupling=0.0,
                       complexity=0.0, risk=0.0)
        w = np.array([1.0, 0.0, 0.0, 0.0, 0.0])
        assert compute_qse_total(m, w) == 1.0

    def test_compute_qse_batch(self):
        m1 = SubMetrics(richness=1.0, compliance=1.0, coupling=1.0,
                        complexity=1.0, risk=1.0)
        m2 = SubMetrics(richness=0.0, compliance=0.0, coupling=0.0,
                        complexity=0.0, risk=0.0)
        batch = compute_qse_batch([m1, m2])
        assert batch[0] == 1.0
        assert batch[1] == 0.0


# ---------------------------------------------------------------------------
# Universal Detectors
# ---------------------------------------------------------------------------

class TestDetectDataOnly:
    def test_detects_data_only(self, tmp_path):
        cls = _make_class("Order", layer="domain", n_init_only=True,
                          file_path=str(tmp_path / "domain" / "order.py"))
        analysis = _make_analysis([cls])
        result = detect_data_only(analysis, str(tmp_path),
                                   lambda c: c.layer == "domain")
        assert len(result) == 1

    def test_ignores_rich_class(self, tmp_path):
        cls = _make_class("Order", layer="domain", n_methods=3, n_init_only=False,
                          file_path=str(tmp_path / "domain" / "order.py"))
        analysis = _make_analysis([cls])
        result = detect_data_only(analysis, str(tmp_path),
                                   lambda c: c.layer == "domain")
        assert len(result) == 0

    def test_custom_filter(self, tmp_path):
        cls = _make_class("Entity", layer="model", n_init_only=True,
                          file_path=str(tmp_path / "model" / "entity.py"))
        analysis = _make_analysis([cls])
        result = detect_data_only(analysis, str(tmp_path),
                                   lambda c: c.layer == "model")
        assert len(result) == 1


class TestDetectGodClass:
    def test_detects_fat(self, tmp_path):
        cls = _make_class("BigSvc", layer="application", n_methods=15,
                          file_path=str(tmp_path / "app" / "big.py"))
        analysis = _make_analysis([cls])
        result = detect_god_class(analysis, str(tmp_path),
                                   lambda c: c.layer == "application")
        assert len(result) == 1

    def test_ignores_slim(self, tmp_path):
        cls = _make_class("SmallSvc", layer="application", n_methods=3,
                          file_path=str(tmp_path / "app" / "small.py"))
        analysis = _make_analysis([cls])
        result = detect_god_class(analysis, str(tmp_path),
                                   lambda c: c.layer == "application")
        assert len(result) == 0


class TestDetectPolicyViolations:
    def test_detects_violation(self, tmp_path):
        G = nx.DiGraph()
        f = str(tmp_path / "domain" / "order.py")
        G.add_node("domain.order", layer="domain", file=f)
        G.add_node("infra.db", layer="infrastructure")
        G.add_edge("domain.order", "infra.db")
        analysis = StaticAnalysis(graph=G, classes={}, files=[])
        result = detect_policy_violations(
            analysis, str(tmp_path),
            {"domain": 0, "infrastructure": 2},
        )
        assert len(result) == 1

    def test_no_violation(self, tmp_path):
        G = nx.DiGraph()
        G.add_node("infra.db", layer="infrastructure",
                   file=str(tmp_path / "infra" / "db.py"))
        G.add_node("domain.order", layer="domain")
        G.add_edge("infra.db", "domain.order")  # outer→inner = OK
        analysis = StaticAnalysis(graph=G, classes={}, files=[])
        result = detect_policy_violations(
            analysis, str(tmp_path),
            {"domain": 0, "infrastructure": 2},
        )
        assert len(result) == 0


class TestDetectAll:
    def test_returns_all_types(self, tmp_path):
        G = nx.DiGraph()
        classes = [_make_class("Order", layer="domain", n_methods=3,
                               file_path=str(tmp_path / "domain" / "order.py"))]
        analysis = _make_analysis(classes, G)
        result = detect_all(
            analysis, G, str(tmp_path),
            entity_filter=lambda c: c.layer == "domain",
            consumer_filter=lambda c: c.layer != "domain",
            target_filter=lambda c: c.layer == "application",
            layer_order={"domain": 0, "application": 1},
        )
        assert "data_only_class" in result
        assert "god_class" in result
        assert "dead_class" in result
        assert "policy_violation" in result


# ---------------------------------------------------------------------------
# Backward Compatibility
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    """Verify that DDD imports still work after refactoring."""

    def test_ddd_metrics_import(self):
        from qse.presets.ddd.metrics import SubMetrics as DDDSubMetrics
        from qse.presets.ddd.metrics import (
            compute_S, compute_T_ddd, compute_G, compute_E, compute_Risk,
            compute_all_metrics as ddd_compute_all,
        )
        # Functions should be callable
        assert callable(compute_S)
        assert callable(compute_T_ddd)

    def test_ddd_aggregator_import(self):
        from qse.presets.ddd.aggregator import (
            DEFAULT_WEIGHTS as ddd_weights,
            compute_qse_total as ddd_qse_total,
            validate_weights as ddd_validate,
        )
        assert len(ddd_weights) == 5
        assert callable(ddd_qse_total)
        assert callable(ddd_validate)

    def test_ddd_detectors_import(self):
        from qse.presets.ddd.detectors import (
            detect_anemic, detect_fat, detect_zombie,
            detect_layer_violations_set, detect_all as ddd_detect_all,
        )
        assert callable(detect_anemic)
        assert callable(detect_fat)
        assert callable(detect_zombie)

    def test_ddd_metrics_values_match_universal(self):
        """DDD wrappers produce same values as direct universal calls."""
        G = nx.DiGraph()
        G.add_node("domain.order", layer="domain")
        G.add_node("app.svc", layer="application")
        G.add_edge("app.svc", "domain.order")
        classes = [
            _make_class("Order", layer="domain", n_methods=3),
            _make_class("CreateService", layer="application", n_methods=4),
        ]
        analysis = _make_analysis(classes, G)

        from qse.presets.ddd.metrics import compute_S, compute_G
        from qse.metrics import compute_richness, compute_coupling

        s_ddd = compute_S(analysis)
        s_univ = compute_richness(analysis, lambda c: c.layer == "domain")
        assert s_ddd == s_univ

        g_ddd = compute_G(G)
        g_univ = compute_coupling(G)
        assert g_ddd == g_univ
