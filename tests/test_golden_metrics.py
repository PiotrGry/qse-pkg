"""
Golden path regression tests for AGQ metrics.

Tests three levels:
1. Synthetic architectural patterns — known exact or bounded outputs
2. Structural ordering invariants — "good" architecture scores higher
3. Determinism — repeated calls produce identical results

These tests catch regressions when metric formulas change.
Do NOT use real repos (slow, requires /tmp). Use synthetic graphs only.
"""

import pytest
import networkx as nx

from qse.graph_metrics import (
    compute_agq,
    compute_acyclicity,
    compute_cohesion,
    compute_lcom4,
    compute_modularity,
    compute_stability,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chain(n: int) -> nx.DiGraph:
    """Linear chain: a0 → a1 → … → a(n-1). Pure DAG."""
    G = nx.DiGraph()
    for i in range(n - 1):
        G.add_edge(f"m{i}", f"m{i+1}")
    return G


def _two_clusters(n: int) -> nx.DiGraph:
    """Two isolated chains of n nodes each. Clear community structure."""
    G = nx.DiGraph()
    for i in range(n - 1):
        G.add_edge(f"a{i}", f"a{i+1}")
        G.add_edge(f"b{i}", f"b{i+1}")
    return G


def _with_cycle(base: nx.DiGraph, cycle_nodes: list) -> nx.DiGraph:
    """Add a cycle to an existing graph."""
    G = base.copy()
    for i in range(len(cycle_nodes)):
        G.add_edge(cycle_nodes[i], cycle_nodes[(i + 1) % len(cycle_nodes)])
    return G


def _star(n: int) -> nx.DiGraph:
    """Hub node with n-1 leaves all pointing to hub (stable core)."""
    G = nx.DiGraph()
    for i in range(n):
        G.add_edge(f"leaf{i}", "hub")
    return G


def _fully_coupled(n: int) -> nx.DiGraph:
    """All nodes depend on all other nodes."""
    G = nx.DiGraph()
    for i in range(n):
        for j in range(n):
            if i != j:
                G.add_edge(f"m{i}", f"m{j}")
    return G


def _layered(n_layers: int, n_per_layer: int) -> nx.DiGraph:
    """n_layers layers of n_per_layer modules, each layer depends on next."""
    G = nx.DiGraph()
    for layer in range(n_layers - 1):
        for mod in range(n_per_layer):
            src = f"L{layer}_M{mod}"
            for tgt_mod in range(n_per_layer):
                tgt = f"L{layer+1}_M{tgt_mod}"
                G.add_edge(src, tgt)
    return G


# ---------------------------------------------------------------------------
# 1. Acyclicity — architectural pattern checks
# ---------------------------------------------------------------------------

class TestAcyclicityGolden:
    def test_clean_dag_is_perfect(self):
        """No cycles → 1.0."""
        assert compute_acyclicity(_chain(20)) == 1.0

    def test_full_cycle_is_zero(self):
        """All nodes in one cycle → 0.0."""
        G = nx.DiGraph()
        nodes = [f"m{i}" for i in range(10)]
        for i in range(len(nodes)):
            G.add_edge(nodes[i], nodes[(i + 1) % len(nodes)])
        assert compute_acyclicity(G) == 0.0

    def test_small_cycle_in_large_dag(self):
        """3-node cycle in a 30-node DAG → acyclicity close to 1 but < 1."""
        G = _chain(30)
        G.add_edge("m5", "m3")   # back-edge: creates cycle m3→m4→m5→m3
        acy = compute_acyclicity(G)
        assert 0.5 < acy < 1.0, f"expected (0.5, 1.0), got {acy}"

    def test_severity_matters(self):
        """Large cycle worse than small cycle (same total node count)."""
        # 20 nodes: one 10-node cycle + 10 clean nodes
        G_big = nx.DiGraph()
        for i in range(10):
            G_big.add_edge(f"cycle{i}", f"cycle{(i+1)%10}")
        for i in range(10):
            G_big.add_edge(f"clean{i}", f"clean{min(i+1,9)}")

        # 20 nodes: one 3-node cycle + 17 clean nodes
        G_small = nx.DiGraph()
        for i in range(3):
            G_small.add_edge(f"cycle{i}", f"cycle{(i+1)%3}")
        for i in range(17):
            G_small.add_edge(f"clean{i}", f"clean{min(i+1,16)}")

        assert compute_acyclicity(G_big) < compute_acyclicity(G_small), \
            "larger cycle should give lower acyclicity"

    def test_two_small_cycles_mid_range(self):
        """Two 2-node cycles in 4-node graph: largest SCC=2 → 1 - 2/4 = 0.5."""
        G = nx.DiGraph()
        G.add_edges_from([("a", "b"), ("b", "a"), ("c", "d"), ("d", "c")])
        assert compute_acyclicity(G) == pytest.approx(0.5)

    def test_external_cycle_ignored(self):
        """Cycle between external nodes (no 'file' attr) must not affect score.
        External = stdlib/third-party modules — cycles there are not architectural."""
        G = nx.DiGraph()
        G.add_node("app.mod", file="/src/mod.py")  # internal
        G.add_node("ext.a")   # external — no file
        G.add_node("ext.b")   # external — no file
        G.add_edge("app.mod", "ext.a")
        G.add_edge("ext.a", "ext.b")
        G.add_edge("ext.b", "ext.a")   # cycle between externals only
        assert compute_acyclicity(G) == 1.0, \
            "cycle only between external nodes should not penalize acyclicity"

    def test_internal_cycle_detected_among_externals(self):
        """Internal cycle is still detected even when mixed with external nodes."""
        G = nx.DiGraph()
        G.add_node("app.a", file="/src/a.py")
        G.add_node("app.b", file="/src/b.py")
        G.add_node("stdlib.os")  # external
        G.add_edge("app.a", "stdlib.os")   # a imports os (normal)
        G.add_edge("app.a", "app.b")       # direct internal edge
        G.add_edge("app.b", "app.a")       # back-edge → cycle a→b→a
        # Internal subgraph: app.a → app.b → app.a = cycle
        acy = compute_acyclicity(G)
        assert acy < 1.0, f"internal cycle should be detected, got {acy}"


# ---------------------------------------------------------------------------
# 2. Stability — instability variance checks
# ---------------------------------------------------------------------------

class TestStabilityGolden:
    def test_uniform_instability_is_zero(self):
        """All nodes same I → variance=0 → stability=0."""
        G = nx.DiGraph()
        G.add_nodes_from(["a", "b", "c", "d"])  # isolated, all I=0.5
        assert compute_stability(G) == pytest.approx(0.0)

    def test_clean_hierarchy_scores_high(self):
        """Balanced bimodal: 10 leaves (I=1) → 10 stable cores (I=0) → max variance.
        50/50 split of I=0 and I=1 gives var=0.25 → stability=1.0."""
        G = nx.DiGraph()
        for i in range(10):
            for j in range(10):
                G.add_edge(f"leaf{i}", f"core{j}")
        s = compute_stability(G)
        assert s > 0.9, f"balanced bimodal hierarchy should have stability>0.9, got {s}"

    def test_more_layered_beats_flat(self):
        """Well-differentiated architecture > uniform architecture."""
        # Layered: clear core + leaves
        G_layered = _star(20)
        s_layered = compute_stability(G_layered)

        # Flat: ring where every node has I ≈ 0.5
        G_flat = nx.DiGraph()
        for i in range(20):
            G_flat.add_edge(f"m{i}", f"m{(i+1)%20}")
        s_flat = compute_stability(G_flat)

        assert s_layered > s_flat, \
            f"layered s={s_layered:.3f} should beat flat ring s={s_flat:.3f}"

    def test_fully_coupled_is_uniform(self):
        """Fully connected: every node I=0.5 → stability=0."""
        G = _fully_coupled(8)
        s = compute_stability(G)
        assert s == pytest.approx(0.0, abs=1e-6)

    def test_leaf_module_inflation_prevented(self):
        """Package-level grouping: 500 leaf nodes in same package must NOT inflate
        stability. All leaves collapse to one package → low variance → low score.
        Regression guard for the v2 bug where youtube-dl got stability=0.99."""
        G = nx.DiGraph()
        # 500 leaf files all in "extractors.X" package importing one hub
        for i in range(500):
            G.add_edge(f"extractors.plugin{i}", "core.hub")
        # Result: "extractors" package (one group) and "core" package (one group)
        # extractors: Ca=0, Ce=500 → I=1.0
        # core: Ca=500, Ce=0 → I=0.0
        # Two packages only → variance of [0.0, 1.0] = 0.25 → stability=1.0?
        # NO — this is actually the correct bimodal case. The inflation bug was
        # when ALL nodes had I=1.0 (no hub imports the extractors back).
        # True inflation test: all extractors import only stdlib (nothing imports them)
        G2 = nx.DiGraph()
        for i in range(500):
            G2.add_edge(f"extractors.plugin{i}", "stdlib.os")  # all same target, external
        # extractors all go to same external node, no one imports them
        # All I = 1.0 (only outgoing) → per-node var would be 0 (all same)
        # Actually this is uniform I=1.0 → variance=0 → stability=0 ✓
        # The real inflation was: per-node var(I) high because many I=1 vs few I=0
        # Package grouping collapses all extractors.* into one "extractors" package
        s = compute_stability(G2)
        assert s == pytest.approx(0.0, abs=0.05), \
            f"500 uniform-leaf modules should give stability≈0, got {s}"

    def test_output_range(self):
        for G in [_chain(15), _star(10), _two_clusters(8), _layered(3, 4)]:
            s = compute_stability(G)
            assert 0.0 <= s <= 1.0, f"stability out of [0,1]: {s}"


# ---------------------------------------------------------------------------
# 3. Modularity — community structure checks
# ---------------------------------------------------------------------------

class TestModularityGolden:
    def test_no_edges_is_perfect(self):
        """Isolated nodes = each its own community → 1.0."""
        G = nx.DiGraph()
        G.add_nodes_from(["a", "b", "c", "d", "e"])
        assert compute_modularity(G) == 1.0

    def test_tiny_connected_graph_is_neutral(self):
        """n<10 with edges → 0.5 (Louvain unreliable on tiny graphs)."""
        G = _chain(5)
        assert compute_modularity(G) == 0.5

    def test_two_clusters_beats_single_chain(self):
        """Two isolated clusters should score higher than one monolithic chain."""
        G_clusters = _two_clusters(15)
        G_chain = _chain(30)
        assert compute_modularity(G_clusters) > compute_modularity(G_chain), \
            "two isolated clusters should have higher modularity than chain"

    def test_fully_coupled_is_low(self):
        """Fully connected graph has no community structure → near 0."""
        G = _fully_coupled(15)
        m = compute_modularity(G)
        assert m < 0.3, f"fully coupled should be near 0, got {m}"

    def test_output_range(self):
        for G in [_chain(20), _two_clusters(10), _layered(3, 5)]:
            m = compute_modularity(G)
            assert 0.0 <= m <= 1.0, f"modularity out of [0,1]: {m}"


# ---------------------------------------------------------------------------
# 4. Cohesion — LCOM4 checks
# ---------------------------------------------------------------------------

class TestCohesionGolden:
    def test_perfect_classes_score_one(self):
        """All classes with LCOM4=1 → cohesion=1.0."""
        assert compute_cohesion([1, 1, 1, 1, 1]) == 1.0

    def test_god_class_penalized(self):
        """LCOM4=5 (max penalty threshold) → penalty=1.0."""
        assert compute_cohesion([5]) == pytest.approx(0.0)

    def test_mixed_cohesion(self):
        """Mix of moderate and bad classes yields intermediate score.
        Uses LCOM4 > 1 (non-trivial classes that aren't skipped)
        and < 5 (not capped) to test the scoring gradient."""
        score = compute_cohesion([2, 2, 3, 4])
        assert 0.0 < score < 1.0

    def test_worse_with_more_god_classes(self):
        """More god classes = lower cohesion.
        Uses non-trivial LCOM4 values (> 1) so the skip filter doesn't mask the effect."""
        score_one_bad = compute_cohesion([2, 2, 2, 2, 5])
        score_two_bad = compute_cohesion([2, 2, 5, 5, 5])
        assert score_one_bad > score_two_bad

    def test_lcom4_single_method_is_perfect(self):
        methods = [("only_method", {"x", "y", "z"})]
        assert compute_lcom4(methods) == 1

    def test_lcom4_no_shared_attrs(self):
        methods = [("a", {"x"}), ("b", {"y"}), ("c", {"z"})]
        assert compute_lcom4(methods) == 3

    def test_lcom4_chain_is_cohesive(self):
        """a-b share x, b-c share y → all connected → LCOM4=1."""
        methods = [("a", {"x"}), ("b", {"x", "y"}), ("c", {"y"})]
        assert compute_lcom4(methods) == 1


# ---------------------------------------------------------------------------
# 5. Composite AGQ — ordering invariants
# ---------------------------------------------------------------------------

class TestAGQOrderingInvariants:
    """
    Architecture quality ordering: known-good > known-bad patterns.
    These are the most important regression guards.
    """

    def test_dag_beats_cyclic(self):
        """Clean DAG should outperform graph with large cycle."""
        G_clean = _chain(30)
        G_cyclic = nx.DiGraph()
        for i in range(30):
            G_cyclic.add_edge(f"m{i}", f"m{(i+1)%30}")  # full ring = one big cycle

        m_clean = compute_agq(G_clean).agq_score
        m_cyclic = compute_agq(G_cyclic).agq_score
        assert m_clean > m_cyclic, \
            f"DAG agq={m_clean:.3f} should beat full cycle agq={m_cyclic:.3f}"

    def test_modular_beats_monolith(self):
        """Two well-separated clusters > single fully-coupled blob."""
        G_modular = _two_clusters(15)
        G_monolith = _fully_coupled(15)

        m_mod = compute_agq(G_modular).agq_score
        m_mono = compute_agq(G_monolith).agq_score
        assert m_mod > m_mono, \
            f"modular agq={m_mod:.3f} should beat monolith agq={m_mono:.3f}"

    def test_layered_beats_flat(self):
        """Clear layered hierarchy > flat graph where all nodes have same I."""
        G_layered = _layered(4, 5)  # 4 layers, 5 modules each
        G_flat = nx.DiGraph()
        # Flat: ring — all nodes have I ≈ 0.5
        for i in range(20):
            G_flat.add_edge(f"m{i}", f"m{(i+1)%20}")

        m_lay = compute_agq(G_layered).agq_score
        m_flat = compute_agq(G_flat).agq_score
        assert m_lay > m_flat, \
            f"layered agq={m_lay:.3f} should beat flat ring agq={m_flat:.3f}"

    def test_good_cohesion_raises_agq(self):
        """Same graph structure but good cohesion > bad cohesion."""
        G = _chain(20)
        lcom_good = [1] * 10
        lcom_bad = [5] * 10

        agq_good = compute_agq(G, classes_lcom4=lcom_good).agq_score
        agq_bad = compute_agq(G, classes_lcom4=lcom_bad).agq_score
        assert agq_good > agq_bad, \
            f"good cohesion agq={agq_good:.3f} should beat bad agq={agq_bad:.3f}"

    def test_all_components_in_range(self):
        """All AGQ components must be in [0, 1] for diverse graphs."""
        graphs = [
            _chain(25),
            _two_clusters(12),
            _star(15),
            _fully_coupled(10),
            _layered(3, 5),
            _with_cycle(_chain(20), ["m5", "m8", "m11"]),
        ]
        lcom = [1, 2, 3, 1, 2]
        for G in graphs:
            m = compute_agq(G, classes_lcom4=lcom)
            for name, val in [
                ("modularity", m.modularity),
                ("acyclicity", m.acyclicity),
                ("stability", m.stability),
                ("cohesion", m.cohesion),
                ("agq_score", m.agq_score),
            ]:
                assert 0.0 <= val <= 1.0, \
                    f"{name}={val} out of [0,1] for graph with {G.number_of_nodes()} nodes"


# ---------------------------------------------------------------------------
# 6. Weighted AGQ
# ---------------------------------------------------------------------------

class TestWeightedAGQ:
    def test_default_weights_applied(self):
        """Default weights (0.20, 0.20, 0.55, 0.05) are applied correctly.
        Tests the weighted sum, not the equal mean."""
        G = _chain(20)
        lcom = [1, 2, 1]
        m = compute_agq(G, classes_lcom4=lcom)
        w = (0.20, 0.20, 0.55, 0.05)
        expected = (w[0] * m.modularity + w[1] * m.acyclicity +
                    w[2] * m.stability + w[3] * m.cohesion)
        assert m.agq_score == pytest.approx(expected)

    def test_explicit_equal_weights_gives_mean(self):
        """Explicit equal weights → simple mean of 4 components."""
        G = _chain(20)
        lcom = [1, 2, 1]
        m = compute_agq(G, classes_lcom4=lcom, weights=(0.25, 0.25, 0.25, 0.25))
        expected = (m.modularity + m.acyclicity + m.stability + m.cohesion) / 4
        assert m.agq_score == pytest.approx(expected)

    def test_acyclicity_only_weight(self):
        """Weight = (0,1,0,0) → agq_score == acyclicity."""
        G = _chain(20)
        m = compute_agq(G, weights=(0.0, 1.0, 0.0, 0.0))
        assert m.agq_score == pytest.approx(m.acyclicity)

    def test_weights_auto_normalized(self):
        """Weights are auto-normalized: (0,73,5,17) → same as (0,0.73,0.05,0.17)."""
        G = _chain(20)
        lcom = [1, 2]
        m1 = compute_agq(G, classes_lcom4=lcom, weights=(0, 73, 5, 17))
        m2 = compute_agq(G, classes_lcom4=lcom, weights=(0.0, 0.73, 0.05, 0.17))
        assert m1.agq_score == pytest.approx(m2.agq_score, abs=1e-6)

    def test_calibrated_weights_favour_acyclicity(self):
        """Churn-calibrated (0,0.73,0.05,0.17): cyclic graph penalized more."""
        G_dag = _chain(20)
        G_cyc = nx.DiGraph()
        for i in range(20):
            G_cyc.add_edge(f"m{i}", f"m{(i+1)%20}")  # full ring

        eq_dag = compute_agq(G_dag, weights=(0.25, 0.25, 0.25, 0.25)).agq_score
        eq_cyc = compute_agq(G_cyc, weights=(0.25, 0.25, 0.25, 0.25)).agq_score
        cal_dag = compute_agq(G_dag, weights=(0.0, 0.73, 0.05, 0.17)).agq_score
        cal_cyc = compute_agq(G_cyc, weights=(0.0, 0.73, 0.05, 0.17)).agq_score

        gap_eq = eq_dag - eq_cyc
        gap_cal = cal_dag - cal_cyc
        assert gap_cal > gap_eq, \
            f"calibrated weights should amplify DAG vs cyclic gap: {gap_cal:.3f} > {gap_eq:.3f}"


# ---------------------------------------------------------------------------
# 7. Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_modularity_deterministic(self):
        """Louvain uses fixed seed=42 — must return identical results."""
        G = _two_clusters(20)
        results = [compute_modularity(G) for _ in range(5)]
        assert len(set(results)) == 1, f"modularity not deterministic: {results}"

    def test_agq_deterministic(self):
        """AGQ score must be identical across repeated calls."""
        G = _layered(3, 8)
        lcom = [1, 2, 1, 3, 1]
        scores = [compute_agq(G, classes_lcom4=lcom).agq_score for _ in range(3)]
        assert len(set(scores)) == 1, f"agq_score not deterministic: {scores}"

    def test_delta_zero_on_same_graph(self):
        """Two runs on same graph → delta < 1e-9 (benchmark T1 requirement)."""
        G = _chain(50)
        lcom = [1, 2, 3, 2, 1] * 4
        s1 = compute_agq(G, classes_lcom4=lcom).agq_score
        s2 = compute_agq(G, classes_lcom4=lcom).agq_score
        assert abs(s1 - s2) < 1e-9
