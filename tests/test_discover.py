"""Tests for auto-discovery of architectural boundaries."""

import json

import networkx as nx
import pytest

from qse.discover import (
    ProposedRule, DiscoveryReport,
    detect_clusters, discover_policies,
    _count_cross_edges, _infer_direction_confidence,
    _cluster_label, _glob_pattern,
)


def _two_cluster_graph():
    """Create a graph with two clear clusters and a one-way bridge."""
    G = nx.DiGraph()
    # Cluster A: payments
    G.add_edge("payments.service", "payments.model")
    G.add_edge("payments.api", "payments.service")
    G.add_edge("payments.api", "payments.model")
    # Cluster B: users
    G.add_edge("users.service", "users.model")
    G.add_edge("users.api", "users.service")
    G.add_edge("users.api", "users.model")
    # One-way bridge: payments → users (but never users → payments)
    G.add_edge("payments.service", "users.model")
    return G


def _isolated_clusters_graph():
    """Two clusters with zero edges between them."""
    G = nx.DiGraph()
    G.add_edge("alpha.a1", "alpha.a2")
    G.add_edge("alpha.a2", "alpha.a3")
    G.add_edge("beta.b1", "beta.b2")
    G.add_edge("beta.b2", "beta.b3")
    return G


class TestClusterLabel:
    def test_single_root(self):
        assert _cluster_label({"payments.api", "payments.service"}) == "payments"

    def test_empty(self):
        assert _cluster_label(set()) == "unknown"


class TestGlobPattern:
    def test_basic(self):
        assert _glob_pattern("payments") == "payments/*"


class TestCountCrossEdges:
    def test_counts_directed(self):
        G = _two_cluster_graph()
        payments = {"payments.service", "payments.model", "payments.api"}
        users = {"users.service", "users.model", "users.api"}
        assert _count_cross_edges(G, payments, users) == 1  # payments.service → users.model
        assert _count_cross_edges(G, users, payments) == 0


class TestInferDirectionConfidence:
    def test_isolated(self):
        conf, direction = _infer_direction_confidence(0, 0)
        assert direction == "isolated"
        assert conf >= 0.8

    def test_one_way_a_to_b(self):
        conf, direction = _infer_direction_confidence(5, 0)
        assert direction == "a_to_b"
        assert conf >= 0.7

    def test_one_way_b_to_a(self):
        conf, direction = _infer_direction_confidence(0, 3)
        assert direction == "b_to_a"
        assert conf >= 0.7

    def test_bidirectional(self):
        conf, direction = _infer_direction_confidence(5, 4)
        assert direction == "bidirectional"
        assert conf < 0.5


class TestDetectClusters:
    def test_two_clusters(self):
        G = _two_cluster_graph()
        clusters = detect_clusters(G)
        assert len(clusters) >= 2
        labels = {c["label"] for c in clusters}
        assert "payments" in labels or "users" in labels

    def test_empty_graph(self):
        G = nx.DiGraph()
        assert detect_clusters(G) == []

    def test_single_node(self):
        G = nx.DiGraph()
        G.add_node("alone")
        assert detect_clusters(G) == []

    def test_min_cluster_size(self):
        G = nx.DiGraph()
        G.add_edge("a.x", "a.y")
        # With min_cluster_size=3, a cluster of 2 is filtered out
        clusters = detect_clusters(G, min_cluster_size=3)
        assert len(clusters) == 0


class TestDiscoverPolicies:
    def test_isolated_clusters_propose_forbidden_both(self):
        G = _isolated_clusters_graph()
        report = discover_policies(G)
        assert len(report.proposed_rules) >= 2
        # Both directions should be forbidden
        directions = set()
        for r in report.proposed_rules:
            directions.add((r.from_pattern, r.to_pattern))
        # Should have rules in both directions
        assert len(directions) >= 2

    def test_directional_cluster_proposes_reverse_forbidden(self):
        G = _two_cluster_graph()
        report = discover_policies(G)
        # Should propose forbidding users → payments (since only payments → users exists)
        reverse_rules = [r for r in report.proposed_rules
                         if "users" in r.from_pattern and "payments" in r.to_pattern]
        assert len(reverse_rules) >= 1
        assert reverse_rules[0].confidence >= 0.7

    def test_empty_graph_no_rules(self):
        G = nx.DiGraph()
        report = discover_policies(G)
        assert len(report.proposed_rules) == 0
        assert len(report.clusters) == 0

    def test_report_to_dict(self):
        G = _isolated_clusters_graph()
        report = discover_policies(G)
        d = report.to_dict()
        assert "clusters" in d
        assert "proposed_rules" in d
        assert "constraints" in d
        assert "graph_summary" in d

    def test_report_to_json(self):
        G = _isolated_clusters_graph()
        report = discover_policies(G)
        j = report.to_json()
        data = json.loads(j)
        assert isinstance(data["proposed_rules"], list)

    def test_constraints_only_high_confidence(self):
        G = _isolated_clusters_graph()
        report = discover_policies(G)
        d = report.to_dict()
        for c in d["constraints"]:
            assert c["_confidence"] >= 0.7

    def test_min_confidence_filter(self):
        G = _two_cluster_graph()
        strict = discover_policies(G, min_confidence=0.9)
        lenient = discover_policies(G, min_confidence=0.3)
        assert len(lenient.proposed_rules) >= len(strict.proposed_rules)

    def test_graph_summary(self):
        G = _two_cluster_graph()
        report = discover_policies(G)
        s = report.graph_summary
        assert s["nodes"] == G.number_of_nodes()
        assert s["edges"] == G.number_of_edges()
        assert "clusters_found" in s
        assert "rules_proposed" in s


class TestProposedRule:
    def test_to_constraint(self):
        r = ProposedRule(
            type="forbidden",
            from_pattern="a/*",
            to_pattern="b/*",
            confidence=0.85,
            rationale="test",
            evidence={},
        )
        c = r.to_constraint()
        assert c["type"] == "forbidden"
        assert c["from"] == "a/*"
        assert c["to"] == "b/*"
        assert c["_confidence"] == 0.85
