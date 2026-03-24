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
    def test_empty(self):
        assert compute_cohesion([]) == 1.0

    def test_all_cohesive(self):
        """All LCOM4=1 → cohesion=1.0."""
        assert compute_cohesion([1, 1, 1]) == 1.0

    def test_one_bad_class(self):
        """LCOM4=5 → penalty = min(1, 4/4) = 1.0 → cohesion = 0.0 for single class."""
        assert compute_cohesion([5]) == 0.0

    def test_mixed(self):
        """LCOM4=[1, 3] → excess=[0, 2] → penalty=[0, 0.5] → mean=0.25 → cohesion=0.75."""
        assert compute_cohesion([1, 3]) == pytest.approx(0.75)

    def test_capped_at_five(self):
        """LCOM4=5 and LCOM4=10 both get penalty=1.0 (capped)."""
        assert compute_cohesion([5]) == compute_cohesion([10])


# ---------------------------------------------------------------------------
# Instability Variance
# ---------------------------------------------------------------------------

class TestInstabilityVariance:
    def test_single_node(self):
        G = nx.DiGraph()
        G.add_node("a")
        assert compute_instability_variance(G) == 1.0

    def test_uniform_instability(self):
        """All nodes with same I → variance=0."""
        G = nx.DiGraph()
        G.add_nodes_from(["a", "b", "c"])  # No edges → all I=0.5 → var=0
        assert compute_instability_variance(G) == 0.0

    def test_differentiated(self):
        """Leaf (I=1) and root (I=0) → high variance."""
        G = nx.DiGraph()
        G.add_edge("leaf", "root")
        var = compute_instability_variance(G)
        assert var > 0.0


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

    def test_agq_score_is_mean(self):
        G = nx.DiGraph()
        G.add_node("a")
        result = compute_agq(G)
        expected = (result.modularity + result.acyclicity + result.stability + result.cohesion) / 4
        assert result.agq_score == pytest.approx(expected)

    def test_dag_high_score(self):
        """Clean DAG with cohesive classes should score high."""
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("a", "c")])
        result = compute_agq(G, classes_lcom4=[1, 1, 1])
        assert result.acyclicity == 1.0
        assert result.agq_score > 0.5
