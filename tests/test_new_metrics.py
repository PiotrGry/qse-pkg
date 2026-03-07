"""Tests for new graph metrics: hierarchical_modularity, boundary_crossing_ratio."""

import pytest
import networkx as nx

from qse.graph_metrics import (
    compute_hierarchical_modularity,
    compute_boundary_crossing_ratio,
)


def _pkg_graph(edges: list, files: list = None) -> nx.DiGraph:
    """Build graph with optional 'file' attributes on specified nodes."""
    G = nx.DiGraph()
    for src, tgt in edges:
        G.add_edge(src, tgt)
    for node in (files or []):
        if node in G.nodes:
            G.nodes[node]["file"] = f"/src/{node}.py"
        else:
            G.add_node(node, file=f"/src/{node}.py")
    return G


class TestHierarchicalModularity:
    def test_no_nodes_returns_one(self):
        assert compute_hierarchical_modularity(nx.DiGraph()) == 1.0

    def test_single_package_returns_neutral(self):
        """All nodes in same second-level package → can't measure → 0.5.
        Need 3-level names: myapp.core.X all group to 'myapp.core'."""
        G = _pkg_graph([("myapp.core.a", "myapp.core.b"),
                        ("myapp.core.b", "myapp.core.c")])
        assert compute_hierarchical_modularity(G) == 0.5

    def test_isolated_packages_high_score(self):
        """Two isolated first-level packages → high modularity."""
        G = nx.DiGraph()
        # services.* internal edges only
        G.add_edges_from([("services.a", "services.b"),
                          ("services.b", "services.c")])
        # domain.* internal edges only
        G.add_edges_from([("domain.x", "domain.y"),
                          ("domain.y", "domain.z")])
        m = compute_hierarchical_modularity(G)
        assert m > 0.5, f"isolated packages should score > 0.5, got {m}"

    def test_fully_cross_coupled_is_low(self):
        """Every edge crosses second-level package boundary → low modularity."""
        G = nx.DiGraph()
        for i in range(5):
            G.add_edge(f"app.services.m{i}", f"lib.utils.n{i}")
        m = compute_hierarchical_modularity(G)
        assert m < 0.5, f"fully cross-coupled should score < 0.5, got {m}"

    def test_mixed_structure(self):
        """Some internal, some cross edges → score in (0,1)."""
        G = nx.DiGraph()
        G.add_edges_from([("app.core.a", "app.core.b"),
                          ("app.core.b", "app.core.c")])   # internal
        G.add_edges_from([("app.core.a", "lib.base.x"),
                          ("lib.base.x", "lib.base.y")])   # cross + internal
        m = compute_hierarchical_modularity(G)
        assert 0.0 <= m <= 1.0

    def test_output_range(self):
        graphs = [
            _pkg_graph([("app.svc.a", "lib.base.b"), ("lib.base.b", "app.svc.c")]),
            _pkg_graph([("a.core.x", "a.core.y"), ("a.core.y", "b.utils.z")]),
        ]
        for G in graphs:
            m = compute_hierarchical_modularity(G)
            assert 0.0 <= m <= 1.0, f"out of range: {m}"


class TestBoundaryCrossingRatio:
    def test_no_nodes_returns_one(self):
        assert compute_boundary_crossing_ratio(nx.DiGraph()) == 1.0

    def test_no_cross_edges_returns_one(self):
        """All edges within same 2nd-level package → ratio=0 → score=1.0.
        Use 3-level names so nodes group into one package."""
        G = _pkg_graph([("myapp.core.a", "myapp.core.b"),
                        ("myapp.core.b", "myapp.core.c")],
                       files=["myapp.core.a", "myapp.core.b", "myapp.core.c"])
        score = compute_boundary_crossing_ratio(G)
        assert score == pytest.approx(1.0)

    def test_all_cross_edges_returns_zero(self):
        """Every edge crosses 2nd-level package boundary → ratio=1 → score=0.0."""
        G = _pkg_graph([("myapp.services.a", "mylib.base.b"),
                        ("myapp.services.c", "mylib.base.d")],
                       files=["myapp.services.a", "myapp.services.c"])
        score = compute_boundary_crossing_ratio(G)
        assert score == pytest.approx(0.0)

    def test_half_cross_edges(self):
        """Half internal, half cross → score=0.5."""
        G = _pkg_graph(
            [("myapp.core.a", "myapp.core.b"),   # internal
             ("myapp.core.a", "mylib.base.x")],  # cross
            files=["myapp.core.a", "myapp.core.b"]
        )
        score = compute_boundary_crossing_ratio(G)
        assert score == pytest.approx(0.5)

    def test_no_file_attr_uses_all_nodes(self):
        """No 'file' attrs → falls back to all nodes, still computes ratio."""
        G = nx.DiGraph()
        G.add_edge("myapp.core.a", "mylib.base.b")  # cross
        G.add_edge("myapp.core.a", "myapp.core.c")  # internal
        score = compute_boundary_crossing_ratio(G)
        assert 0.0 <= score <= 1.0

    def test_well_layered_beats_tangled(self):
        """Clean arch (few cross-package edges) scores higher than tangled."""
        # Clean: services import domain internally, minimal cross
        G_clean = nx.DiGraph()
        for i in range(4):
            G_clean.add_node(f"myapp.domain.m{i}", file=f"/src/m{i}.py")
            G_clean.add_edge(f"myapp.domain.m{i}", f"myapp.domain.m{(i+1)%4}")
        # One cross edge
        G_clean.add_node("myapp.services.s0", file="/src/s0.py")
        G_clean.add_edge("myapp.services.s0", "myapp.domain.m0")

        # Tangled: every module crosses into another package
        G_tangled = nx.DiGraph()
        for i in range(5):
            G_tangled.add_node(f"mod{i}.core.a", file=f"/src/mod{i}/a.py")
        for i in range(5):
            for j in range(5):
                if i != j:
                    G_tangled.add_edge(f"mod{i}.core.a", f"mod{j}.core.a")

        clean_score = compute_boundary_crossing_ratio(G_clean)
        tangled_score = compute_boundary_crossing_ratio(G_tangled)
        assert clean_score > tangled_score, \
            f"clean={clean_score:.3f} should beat tangled={tangled_score:.3f}"

    def test_output_range(self):
        graphs = [
            _pkg_graph([("a.x.m", "b.y.n"), ("b.y.n", "a.z.p")],
                       files=["a.x.m", "b.y.n"]),
            _pkg_graph([("c.core.a", "c.core.b"), ("c.core.b", "d.utils.c")],
                       files=["c.core.a", "c.core.b"]),
        ]
        for G in graphs:
            score = compute_boundary_crossing_ratio(G)
            assert 0.0 <= score <= 1.0
