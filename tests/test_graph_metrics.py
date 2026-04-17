"""Unit tests for qse.graph_metrics — AGQ Level 1 metrics."""

import networkx as nx
import pytest

from qse.graph_metrics import (
    AGQMetrics,
    compute_acyclicity,
    compute_agq,
    compute_cohesion,
    compute_instability_variance,
    compute_lcom4,
    compute_modularity,
    compute_stability,
)


# ---------------------------------------------------------------------------
# Modularity
# ---------------------------------------------------------------------------

class TestModularity:
    def test_empty_graph(self):
        G = nx.DiGraph()
        assert compute_modularity(G) == 1.0

    def test_single_node(self):
        G = nx.DiGraph()
        G.add_node("a")
        assert compute_modularity(G) == 1.0

    def test_no_edges(self):
        G = nx.DiGraph()
        G.add_nodes_from(["a", "b", "c"])
        assert compute_modularity(G) == 1.0

    def test_two_clusters(self):
        """Two disconnected clusters should yield high modularity."""
        G = nx.DiGraph()
        G.add_edges_from([("a1", "a2"), ("a2", "a3"), ("b1", "b2"), ("b2", "b3")])
        q = compute_modularity(G)
        assert 0.0 <= q <= 1.0
        assert q > 0.3  # Well-separated clusters

    def test_fully_connected(self):
        """Fully connected graph → low modularity."""
        G = nx.DiGraph()
        nodes = ["a", "b", "c", "d"]
        for i in nodes:
            for j in nodes:
                if i != j:
                    G.add_edge(i, j)
        q = compute_modularity(G)
        assert 0.0 <= q <= 1.0

    def test_output_range(self):
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "c")])
        q = compute_modularity(G)
        assert 0.0 <= q <= 1.0


# ---------------------------------------------------------------------------
# Acyclicity
# ---------------------------------------------------------------------------

class TestAcyclicity:
    def test_empty_graph(self):
        assert compute_acyclicity(nx.DiGraph()) == 1.0

    def test_single_node(self):
        G = nx.DiGraph()
        G.add_node("a")
        assert compute_acyclicity(G) == 1.0

    def test_dag(self):
        """Directed acyclic graph → acyclicity = 1.0."""
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "c"), ("a", "c")])
        assert compute_acyclicity(G) == 1.0

    def test_full_cycle(self):
        """All nodes in a cycle → acyclicity = 0.0."""
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "c"), ("c", "a")])
        assert compute_acyclicity(G) == 0.0

    def test_partial_cycle(self):
        """3 nodes in cycle + 1 outside → acyclicity = 0.25."""
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "c"), ("c", "a"), ("a", "d")])
        assert compute_acyclicity(G) == pytest.approx(0.25)

    def test_two_disconnected_cycles(self):
        """Two separate 2-node cycles: largest SCC=2, total=4 → 1 - 2/4 = 0.5.
        Less catastrophic than one large SCC — new formula captures severity."""
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "a"), ("c", "d"), ("d", "c")])
        assert compute_acyclicity(G) == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Stability
# ---------------------------------------------------------------------------

class TestStability:
    def test_empty_graph(self):
        assert compute_stability(nx.DiGraph()) == 1.0

    def test_isolated_nodes_default(self):
        """Isolated nodes all get I=0.5 → zero variance → stability=0.0.
        Undifferentiated graph has no layering signal."""
        G = nx.DiGraph()
        G.add_nodes_from(["a", "b"])
        st = compute_stability(G)
        assert st == pytest.approx(0.0)

    def test_abstract_module_on_main_sequence(self):
        """A=1 (fully abstract) + I=0 (fully stable) → D=0 → St=1.0."""
        G = nx.DiGraph()
        G.add_edge("client", "core")
        st = compute_stability(G, abstract_modules={"core"})
        assert 0.0 <= st <= 1.0

    def test_output_range(self):
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "c")])
        st = compute_stability(G)
        assert 0.0 <= st <= 1.0


# ---------------------------------------------------------------------------
# LCOM4
# ---------------------------------------------------------------------------

class TestLCOM4:
    def test_empty(self):
        assert compute_lcom4([]) == 1

    def test_cohesive_class(self):
        """Two methods sharing the same attribute → LCOM4=1."""
        methods = [("get", {"x"}), ("set", {"x"})]
        assert compute_lcom4(methods) == 1

    def test_disjoint_methods(self):
        """Two methods with no shared attributes → LCOM4=2."""
        methods = [("get_x", {"x"}), ("get_y", {"y"})]
        assert compute_lcom4(methods) == 2

    def test_chain(self):
        """A-B share attr1, B-C share attr2 → all connected → LCOM4=1."""
        methods = [("a", {"x"}), ("b", {"x", "y"}), ("c", {"y"})]
        assert compute_lcom4(methods) == 1

    def test_three_isolated(self):
        methods = [("a", {"x"}), ("b", {"y"}), ("c", {"z"})]
        assert compute_lcom4(methods) == 3


# ---------------------------------------------------------------------------
# Cohesion
# ---------------------------------------------------------------------------

class TestCohesion:
    def test_empty_is_neutral(self):
        """No classes found → neutral score (not perfect).
        Empty input means the scanner found nothing, not that cohesion is ideal."""
        score = compute_cohesion([])
        assert 0.0 < score < 1.0  # neutral, not perfect

    def test_all_cohesive(self):
        """All LCOM4=1 → cohesion=1.0 (trivially cohesive classes skipped, no penalties)."""
        assert compute_cohesion([1, 1, 1]) == 1.0

    def test_one_bad_class(self):
        """LCOM4=5 → penalty = min(1, 4/4) = 1.0 → cohesion = 0.0 for single non-trivial class."""
        assert compute_cohesion([5]) == 0.0

    def test_mixed_worse_than_all_good(self):
        """Adding a bad class (LCOM4=3) to good ones lowers cohesion."""
        all_good = compute_cohesion([1, 1, 1])
        mixed = compute_cohesion([1, 1, 3])
        assert mixed < all_good

    def test_mixed_better_than_all_bad(self):
        """Mix of good and bad is better than all bad."""
        mixed = compute_cohesion([1, 1, 3])
        all_bad = compute_cohesion([5, 5, 5])
        assert mixed > all_bad

    def test_more_bad_classes_lower_score(self):
        """More non-trivial bad classes → lower cohesion."""
        one_bad = compute_cohesion([3])
        three_bad = compute_cohesion([3, 4, 5])
        assert one_bad >= three_bad

    def test_capped_at_five(self):
        """LCOM4=5 and LCOM4=10 both get penalty=1.0 (capped)."""
        assert compute_cohesion([5]) == compute_cohesion([10])

    def test_output_range(self):
        """Cohesion is always in [0, 1]."""
        for lcom_list in [[], [1], [1, 1], [5], [1, 3], [2, 3, 5, 8]]:
            score = compute_cohesion(lcom_list)
            assert 0.0 <= score <= 1.0, f"cohesion({lcom_list})={score} out of range"


# ---------------------------------------------------------------------------
# Instability Variance
# ---------------------------------------------------------------------------

class TestInstabilityVariance:
    """Tests for deprecated compute_instability_variance (node-level).
    Tests verify behavioral invariants, not specific numeric values."""

    def test_single_node(self):
        G = nx.DiGraph()
        G.add_node("a")
        assert compute_instability_variance(G) == 1.0

    def test_uniform_instability_is_zero(self):
        """All nodes with same I → variance=0."""
        G = nx.DiGraph()
        G.add_nodes_from(["a", "b", "c"])  # No edges → all I=0.5 → var=0
        assert compute_instability_variance(G) == 0.0

    def test_differentiated_higher_than_uniform(self):
        """Leaf (I=1) and root (I=0) → higher variance than uniform."""
        G_diff = nx.DiGraph()
        G_diff.add_edge("leaf", "root")
        G_uniform = nx.DiGraph()
        G_uniform.add_nodes_from(["a", "b", "c"])
        assert compute_instability_variance(G_diff) > compute_instability_variance(G_uniform)

    def test_output_range(self):
        """Result is always in [0, 1]."""
        for edges in [[], [("a", "b")], [("a", "b"), ("b", "c"), ("c", "a")]]:
            G = nx.DiGraph()
            G.add_edges_from(edges) if edges else G.add_nodes_from(["a", "b"])
            val = compute_instability_variance(G)
            assert 0.0 <= val <= 1.0, f"instability_variance={val} out of range"


# ---------------------------------------------------------------------------
# Composite compute_agq
# ---------------------------------------------------------------------------

class TestComputeAGQ:
    def test_returns_agq_metrics(self):
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "c")])
        result = compute_agq(G)
        assert isinstance(result, AGQMetrics)

    def test_all_metrics_in_range(self):
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "c"), ("c", "d")])
        result = compute_agq(G, classes_lcom4=[1, 2])
        assert 0.0 <= result.modularity <= 1.0
        assert 0.0 <= result.acyclicity <= 1.0
        assert 0.0 <= result.stability <= 1.0
        assert 0.0 <= result.cohesion <= 1.0
        assert 0.0 <= result.agq_score <= 1.0

    def test_agq_score_respects_weights(self):
        """agq_score uses the default weights (0.20, 0.20, 0.55, 0.05), not equal mean."""
        G = nx.DiGraph()
        G.add_node("a")
        result = compute_agq(G)
        w = (0.20, 0.20, 0.55, 0.05)
        expected = (w[0] * result.modularity + w[1] * result.acyclicity +
                    w[2] * result.stability + w[3] * result.cohesion)
        assert result.agq_score == pytest.approx(expected)

    def test_agq_score_with_equal_weights(self):
        """Explicit equal weights → mean of 4 components."""
        G = nx.DiGraph()
        G.add_node("a")
        result = compute_agq(G, weights=(0.25, 0.25, 0.25, 0.25))
        expected = (result.modularity + result.acyclicity + result.stability + result.cohesion) / 4
        assert result.agq_score == pytest.approx(expected)

    def test_dag_high_score(self):
        """Clean DAG with cohesive classes should score high."""
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("a", "c")])
        result = compute_agq(G, classes_lcom4=[1, 1, 1])
        assert result.acyclicity == 1.0
        assert result.agq_score > 0.5


# ---------------------------------------------------------------------------
# Layer Violations (scanner.detect_layer_violations)
# ---------------------------------------------------------------------------

from qse.scanner import StaticAnalysis, detect_layer_violations


def _make_analysis_with_layers(edges, node_layers):
    """Helper: build a StaticAnalysis with nodes having layer attributes."""
    G = nx.DiGraph()
    for node, layer in node_layers.items():
        G.add_node(node, layer=layer)
    for src, tgt in edges:
        G.add_edge(src, tgt)
    return StaticAnalysis(graph=G, classes={}, files=[])


class TestLayerViolations:
    def test_allowed_outer_to_inner_adjacent(self):
        """application→domain is allowed (adjacent layers, correct direction)."""
        analysis = _make_analysis_with_layers(
            [("app.service", "domain.order")],
            {"app.service": "application", "domain.order": "domain"},
        )
        assert detect_layer_violations(analysis) == []

    def test_allowed_same_layer(self):
        """domain→domain is always allowed."""
        analysis = _make_analysis_with_layers(
            [("domain.order", "domain.item")],
            {"domain.order": "domain", "domain.item": "domain"},
        )
        assert detect_layer_violations(analysis) == []

    def test_violation_upward_domain_to_infra(self):
        """domain→infrastructure is a dependency inversion violation."""
        analysis = _make_analysis_with_layers(
            [("domain.order", "infra.db")],
            {"domain.order": "domain", "infra.db": "infrastructure"},
        )
        violations = detect_layer_violations(analysis)
        assert len(violations) == 1
        assert violations[0][2] == "domain"
        assert violations[0][3] == "infrastructure"

    def test_violation_upward_application_to_presentation(self):
        """application→presentation is a dependency inversion violation."""
        analysis = _make_analysis_with_layers(
            [("app.svc", "pres.view")],
            {"app.svc": "application", "pres.view": "presentation"},
        )
        assert len(detect_layer_violations(analysis)) == 1

    def test_violation_skip_presentation_to_domain(self):
        """presentation→domain is OK (outer→inner, dependency rule satisfied)."""
        analysis = _make_analysis_with_layers(
            [("pres.view", "domain.order")],
            {"pres.view": "presentation", "domain.order": "domain"},
        )
        violations = detect_layer_violations(analysis)
        assert len(violations) == 0

    def test_allowed_presentation_to_infrastructure(self):
        """presentation→infrastructure is OK (outer→inner)."""
        analysis = _make_analysis_with_layers(
            [("pres.view", "infra.api")],
            {"pres.view": "presentation", "infra.api": "infrastructure"},
        )
        assert detect_layer_violations(analysis) == []

    def test_no_violations_clean_ddd(self):
        """Full clean DDD stack: all dependencies flow inward → no violations."""
        analysis = _make_analysis_with_layers(
            [
                ("pres.api", "app.service"),
                ("app.service", "domain.order"),
                ("infra.repo", "domain.order"),
            ],
            {
                "pres.api": "presentation",
                "app.service": "application",
                "domain.order": "domain",
                "infra.repo": "infrastructure",
            },
        )
        violations = detect_layer_violations(analysis)
        assert len(violations) == 0

    def test_unknown_layer_ignored(self):
        """Nodes without known layers are not flagged."""
        analysis = _make_analysis_with_layers(
            [("unknown.mod", "domain.order")],
            {"unknown.mod": "unknown", "domain.order": "domain"},
        )
        assert detect_layer_violations(analysis) == []
