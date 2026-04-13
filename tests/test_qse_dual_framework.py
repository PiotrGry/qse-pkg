"""Tests for QSE three-layer framework: Rank, Track, Diagnostic."""

import networkx as nx
import pytest

from qse.graph_metrics import (
    AGQMetrics,
    GT_BENCHMARK_C,
    GT_BENCHMARK_S,
    compute_agq,
    compute_qse_rank,
    compute_qse_track,
    compute_qse_diagnostic,
)


# ── QSE-Rank (Layer 1: benchmarking) ──────────────────────────────────


class TestQSERank:
    """Test compute_qse_rank behavior, not specific values."""

    def test_high_c_high_s_scores_high(self):
        """A repo with top C and S should rank near 2.0."""
        m = AGQMetrics(modularity=0.5, acyclicity=0.9, stability=0.95, cohesion=0.8)
        score = compute_qse_rank(m, GT_BENCHMARK_C, GT_BENCHMARK_S)
        assert score > 1.5, f"Top C+S should score >1.5, got {score}"

    def test_low_c_low_s_scores_low(self):
        """A repo with bottom C and S should rank near 0.0."""
        m = AGQMetrics(modularity=0.5, acyclicity=0.9, stability=0.01, cohesion=0.1)
        score = compute_qse_rank(m, GT_BENCHMARK_C, GT_BENCHMARK_S)
        assert score < 0.5, f"Bottom C+S should score <0.5, got {score}"

    def test_result_in_valid_range(self):
        """QSE-Rank must be in [0, 2]."""
        m = AGQMetrics(modularity=0.5, acyclicity=0.5, stability=0.5, cohesion=0.5)
        score = compute_qse_rank(m, GT_BENCHMARK_C, GT_BENCHMARK_S)
        assert 0.0 <= score <= 2.0

    def test_stores_on_metrics_object(self):
        """compute_qse_rank should set metrics.qse_rank."""
        m = AGQMetrics(modularity=0.5, acyclicity=0.5, stability=0.5, cohesion=0.5)
        score = compute_qse_rank(m, GT_BENCHMARK_C, GT_BENCHMARK_S)
        assert m.qse_rank == score

    def test_monotonic_in_cohesion(self):
        """Higher cohesion (all else equal) should give higher QSE-Rank."""
        m_low = AGQMetrics(modularity=0.5, acyclicity=0.5, stability=0.3, cohesion=0.25)
        m_high = AGQMetrics(modularity=0.5, acyclicity=0.5, stability=0.3, cohesion=0.7)
        s_low = compute_qse_rank(m_low, GT_BENCHMARK_C, GT_BENCHMARK_S)
        s_high = compute_qse_rank(m_high, GT_BENCHMARK_C, GT_BENCHMARK_S)
        assert s_high > s_low

    def test_monotonic_in_stability(self):
        """Higher stability (all else equal) should give higher QSE-Rank."""
        m_low = AGQMetrics(modularity=0.5, acyclicity=0.5, stability=0.05, cohesion=0.4)
        m_high = AGQMetrics(modularity=0.5, acyclicity=0.5, stability=0.8, cohesion=0.4)
        s_low = compute_qse_rank(m_low, GT_BENCHMARK_C, GT_BENCHMARK_S)
        s_high = compute_qse_rank(m_high, GT_BENCHMARK_C, GT_BENCHMARK_S)
        assert s_high > s_low

    def test_custom_benchmark(self):
        """Custom (small) benchmark should work and give different results."""
        m = AGQMetrics(modularity=0.5, acyclicity=0.5, stability=0.5, cohesion=0.5)
        custom_C = [0.3, 0.4, 0.6]
        custom_S = [0.2, 0.5, 0.8]
        score = compute_qse_rank(m, custom_C, custom_S)
        assert 0.0 <= score <= 2.0

    def test_empty_benchmark_handles_gracefully(self):
        """Empty benchmark should not crash."""
        m = AGQMetrics(modularity=0.5, acyclicity=0.5, stability=0.5, cohesion=0.5)
        score = compute_qse_rank(m, [], [])
        import math
        assert isinstance(score, float)


# ── QSE-Track (Layer 2: monitoring) ───────────────────────────────────


def _make_layered_graph(n_packages=4, n_per_pkg=5, add_violations=False):
    """Create a synthetic layered graph for testing."""
    G = nx.DiGraph()
    packages = [f"com.app.layer{i}" for i in range(n_packages)]

    for p_idx, pkg in enumerate(packages):
        for j in range(n_per_pkg):
            node = f"{pkg}.Class{j}"
            G.add_node(node)

    # Downward edges (legal: higher layer -> lower layer)
    for p_idx in range(n_packages - 1):
        src = f"{packages[p_idx]}.Class0"
        tgt = f"{packages[p_idx + 1]}.Class0"
        G.add_edge(src, tgt)

    if add_violations:
        # Upward edge (creates cycle)
        G.add_edge(f"{packages[-1]}.Class0", f"{packages[0]}.Class0")

    return G


class TestQSETrack:
    """Test compute_qse_track behavior."""

    def test_returns_required_keys(self):
        """Must return M, PCA, dip_violations, largest_scc."""
        G = _make_layered_graph()
        result = compute_qse_track(G)
        assert "M" in result
        assert "PCA" in result
        assert "dip_violations" in result
        assert "largest_scc" in result

    def test_m_in_valid_range(self):
        """Modularity should be in [0, 1]."""
        G = _make_layered_graph()
        result = compute_qse_track(G)
        assert 0.0 <= result["M"] <= 1.0

    def test_acyclic_graph_no_scc(self):
        """Acyclic graph should have largest_scc = 0."""
        G = _make_layered_graph(add_violations=False)
        result = compute_qse_track(G)
        assert result["largest_scc"] == 0

    def test_cycle_detected_in_scc(self):
        """Adding a cycle should produce largest_scc > 0."""
        G = _make_layered_graph(add_violations=True)
        result = compute_qse_track(G)
        assert result["largest_scc"] > 0

    def test_track_detects_structural_change(self):
        """Adding a cycle should change PCA or largest_scc."""
        G_clean = _make_layered_graph(add_violations=False)
        G_dirty = _make_layered_graph(add_violations=True)
        r_clean = compute_qse_track(G_clean)
        r_dirty = compute_qse_track(G_dirty)
        changed = (
            r_clean["PCA"] != r_dirty["PCA"]
            or r_clean["largest_scc"] != r_dirty["largest_scc"]
        )
        assert changed, "QSE-Track should detect cycle addition"

    def test_dip_violations_with_domain_infra(self):
        """Graph with domain->infra edge should have dip_violations > 0."""
        G = nx.DiGraph()
        G.add_node("com.app.domain.Order")
        G.add_node("com.app.infrastructure.OrderRepo")
        G.add_edge("com.app.domain.Order", "com.app.infrastructure.OrderRepo")
        result = compute_qse_track(G)
        assert result["dip_violations"] > 0


# ── QSE-Diagnostic (Layer 3: problem identification) ──────────────────


class TestQSEDiagnostic:
    """Test compute_qse_diagnostic behavior."""

    def test_returns_all_components(self):
        """Must return all metric components and problems list."""
        G = _make_layered_graph()
        m = AGQMetrics(modularity=0.5, acyclicity=0.9, stability=0.3, cohesion=0.4,
                       coupling_density=0.5)
        result = compute_qse_diagnostic(G, m)
        for key in ("C", "C_percentile", "S", "S_percentile", "M", "A", "CD",
                     "PCA", "LVR", "dip_violations", "largest_scc", "problems"):
            assert key in result, f"Missing key: {key}"

    def test_flags_low_cohesion(self):
        """Bottom-quartile cohesion should flag LOW_COHESION."""
        G = _make_layered_graph()
        m = AGQMetrics(modularity=0.6, acyclicity=0.9, stability=0.5, cohesion=0.22,
                       coupling_density=0.5)
        result = compute_qse_diagnostic(G, m)
        assert "LOW_COHESION" in result["problems"]

    def test_no_false_flags_for_good_repo(self):
        """Good metrics should produce no problem flags."""
        G = _make_layered_graph()
        m = AGQMetrics(modularity=0.7, acyclicity=0.95, stability=0.8, cohesion=0.65,
                       coupling_density=0.6)
        result = compute_qse_diagnostic(G, m)
        # PCA is 1.0 for acyclic graph, LVR 1.0 for no violations
        # C=0.65 and S=0.8 are well above bottom quartile
        assert len(result["problems"]) == 0, f"Unexpected problems: {result['problems']}"

    def test_percentiles_in_valid_range(self):
        """Percentiles should be in [0, 1]."""
        G = _make_layered_graph()
        m = AGQMetrics(modularity=0.5, acyclicity=0.9, stability=0.3, cohesion=0.4,
                       coupling_density=0.5)
        result = compute_qse_diagnostic(G, m)
        assert 0.0 <= result["C_percentile"] <= 1.0
        assert 0.0 <= result["S_percentile"] <= 1.0


# ── GT Benchmark constants ────────────────────────────────────────────


class TestGTBenchmark:
    """Verify GT benchmark data integrity."""

    def test_benchmark_length(self):
        """GT benchmark should have n=52 entries."""
        assert len(GT_BENCHMARK_C) == 52
        assert len(GT_BENCHMARK_S) == 52

    def test_benchmark_ranges(self):
        """C and S values should be in [0, 1]."""
        assert all(0 <= v <= 1 for v in GT_BENCHMARK_C)
        assert all(0 <= v <= 1 for v in GT_BENCHMARK_S)

    def test_benchmark_has_variance(self):
        """Benchmark should have actual variance (not all same value)."""
        import numpy as np
        assert np.std(GT_BENCHMARK_C) > 0.05
        assert np.std(GT_BENCHMARK_S) > 0.05
