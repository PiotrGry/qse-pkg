"""Unit tests for hybrid_graph.py — merge of static + dynamic edges."""

import pytest
import networkx as nx

from qse.hybrid_graph import build_hybrid_graph, graph_stats
from qse.scanner import StaticAnalysis
from qse.tracer import TraceResult


def _make_static(edges: list, nodes_with_files: list = None) -> StaticAnalysis:
    G = nx.DiGraph()
    for n in (nodes_with_files or []):
        G.add_node(n, file=f"/src/{n}.py", layer=None)
    for src, tgt in edges:
        G.add_edge(src, tgt)
    return StaticAnalysis(graph=G)


class TestBuildHybridGraph:
    def test_static_only_edges_tagged(self):
        """All static edges get source='static'."""
        static = _make_static([("a", "b"), ("b", "c")])
        trace = TraceResult()
        G = build_hybrid_graph(static, trace)
        for _, _, d in G.edges(data=True):
            assert d.get("source") == "static"

    def test_dynamic_only_edges_tagged(self):
        """Dynamic-only edges get source='dynamic'."""
        static = _make_static([])
        trace = TraceResult(dynamic_edges=[("x", "y")])
        G = build_hybrid_graph(static, trace)
        assert G.has_edge("x", "y")
        assert G.edges["x", "y"]["source"] == "dynamic"

    def test_shared_edge_tagged_both(self):
        """Edge present in static AND dynamic gets source='both'."""
        static = _make_static([("a", "b")])
        trace = TraceResult(dynamic_edges=[("a", "b")])
        G = build_hybrid_graph(static, trace)
        assert G.edges["a", "b"]["source"] == "both"

    def test_all_static_nodes_preserved(self):
        """All nodes from static graph appear in hybrid graph."""
        static = _make_static([("a", "b"), ("b", "c")], nodes_with_files=["a", "b", "c"])
        trace = TraceResult()
        G = build_hybrid_graph(static, trace)
        for node in ["a", "b", "c"]:
            assert node in G.nodes

    def test_dynamic_nodes_added(self):
        """New nodes introduced by dynamic edges are added."""
        static = _make_static([])
        trace = TraceResult(dynamic_edges=[("new_caller", "new_callee")])
        G = build_hybrid_graph(static, trace)
        assert "new_caller" in G.nodes
        assert "new_callee" in G.nodes

    def test_dynamic_node_layer_inferred(self):
        """Dynamic nodes in known DDD directories get layer inferred."""
        static = _make_static([])
        trace = TraceResult(dynamic_edges=[("domain.order", "application.service")])
        G = build_hybrid_graph(static, trace)
        assert G.nodes["domain.order"].get("layer") == "domain"
        assert G.nodes["application.service"].get("layer") == "application"

    def test_empty_static_empty_dynamic(self):
        """Both empty → empty graph."""
        G = build_hybrid_graph(_make_static([]), TraceResult())
        assert G.number_of_nodes() == 0
        assert G.number_of_edges() == 0

    def test_static_node_layer_not_overwritten(self):
        """Existing layer on static node is NOT overwritten by dynamic inference."""
        static = _make_static([], nodes_with_files=["domain.order"])
        static.graph.nodes["domain.order"]["layer"] = "domain"
        trace = TraceResult(dynamic_edges=[("domain.order", "infrastructure.repo")])
        G = build_hybrid_graph(static, trace)
        assert G.nodes["domain.order"].get("layer") == "domain"


class TestGraphStats:
    def test_counts_by_source(self):
        """graph_stats correctly counts static/dynamic/both edges."""
        static = _make_static([("a", "b"), ("b", "c")])
        trace = TraceResult(dynamic_edges=[("b", "c"), ("c", "d")])
        G = build_hybrid_graph(static, trace)
        stats = graph_stats(G)

        assert stats["nodes"] == 4
        assert stats["total_edges"] == 3
        assert stats["static_only_edges"] == 1   # a→b
        assert stats["dynamic_only_edges"] == 1  # c→d
        assert stats["both_edges"] == 1          # b→c

    def test_empty_graph_stats(self):
        G = nx.DiGraph()
        stats = graph_stats(G)
        assert stats["nodes"] == 0
        assert stats["total_edges"] == 0
        assert stats["static_only_edges"] == 0
        assert stats["dynamic_only_edges"] == 0
        assert stats["both_edges"] == 0
