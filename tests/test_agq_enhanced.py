"""Tests for AGQ enhanced metrics."""
import pytest
from qse.agq_enhanced import (
    compute_agq_z, compute_agq_percentile, compute_fingerprint,
    compute_cycle_severity, compute_churn_risk, compute_agq_size_adjusted,
    compute_agq_enhanced,
)


class TestAGQz:
    def test_average_project_has_zero_z(self):
        # Python mean = 0.7494
        z = compute_agq_z(0.7494, "Python")
        assert abs(z) < 0.1

    def test_excellent_project_positive_z(self):
        z = compute_agq_z(0.90, "Python")
        assert z > 1.0

    def test_poor_project_negative_z(self):
        z = compute_agq_z(0.55, "Java")
        assert z < -0.5

    def test_go_average_higher_than_java(self):
        # Same absolute AGQ=0.75 → better z for Java than Go
        z_java = compute_agq_z(0.75, "Java")
        z_go   = compute_agq_z(0.75, "Go")
        assert z_java > z_go, "0.75 is above Java mean but below Go mean"

    def test_unknown_language_returns_none(self):
        assert compute_agq_z(0.80, "Rust") is None

    def test_percentile_range(self):
        p = compute_agq_percentile(0.75, "Python")
        assert 0 <= p <= 100

    def test_high_agq_high_percentile(self):
        p = compute_agq_percentile(0.85, "Python")
        assert p > 90


class TestFingerprint:
    def test_clean_go_style(self):
        fp = compute_fingerprint(0.5, 1.0, 0.95, 1.0)
        assert fp == "CLEAN"

    def test_layered(self):
        fp = compute_fingerprint(0.6, 1.0, 0.80, 0.70)
        assert fp == "LAYERED"

    def test_tangled_java_oop(self):
        fp = compute_fingerprint(0.6, 0.85, 0.40, 0.20)
        assert fp == "TANGLED"

    def test_cyclic(self):
        fp = compute_fingerprint(0.6, 0.85, 0.40, 0.60)
        assert fp == "CYCLIC"

    def test_low_cohesion(self):
        fp = compute_fingerprint(0.6, 1.0, 0.50, 0.30)
        assert fp == "LOW_COHESION"

    def test_flat(self):
        fp = compute_fingerprint(0.5, 1.0, 0.20, 0.60)
        assert fp == "FLAT"

    def test_moderate(self):
        fp = compute_fingerprint(0.5, 1.0, 0.55, 0.55)
        assert fp == "MODERATE"


class TestCycleSeverity:
    def test_no_cycles(self):
        cs = compute_cycle_severity(1.0)
        assert cs["severity_level"] == "NONE"
        assert cs["severity_ratio"] == 0.0

    def test_minor_cycles(self):
        cs = compute_cycle_severity(0.995)
        assert cs["severity_level"] == "LOW"
        assert cs["severity_pct"] == pytest.approx(0.5, abs=0.1)

    def test_critical_cycles(self):
        cs = compute_cycle_severity(0.70)
        assert cs["severity_level"] == "CRITICAL"
        assert cs["severity_pct"] == pytest.approx(30.0, abs=0.1)

    def test_levels_ordered(self):
        levels = ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        acys = [1.0, 0.995, 0.97, 0.90, 0.70]
        for acy, expected in zip(acys, levels):
            assert compute_cycle_severity(acy)["severity_level"] == expected


class TestChurnRisk:
    def test_clean_arch_low_risk(self):
        cr = compute_churn_risk(1.0, 1.0, 0.8)
        assert cr["churn_risk_level"] == "LOW"
        assert cr["churn_risk_score"] < 0.1

    def test_tangled_high_risk(self):
        cr = compute_churn_risk(0.7, 0.2, 0.3)
        assert cr["churn_risk_score"] > 0.4

    def test_risk_in_range(self):
        for acy, stab, mod in [(1.0,1.0,1.0),(0.5,0.3,0.4),(0.0,0.0,0.0)]:
            cr = compute_churn_risk(acy, stab, mod)
            assert 0.0 <= cr["churn_risk_score"] <= 1.0


class TestSizeAdjusted:
    def test_500_node_project_unchanged(self):
        adj = compute_agq_size_adjusted(0.75, 500)
        assert adj == pytest.approx(0.75, abs=0.01)

    def test_small_project_higher(self):
        adj = compute_agq_size_adjusted(0.75, 50)
        assert adj > 0.75

    def test_large_project_lower(self):
        adj = compute_agq_size_adjusted(0.75, 5000)
        assert adj < 0.75

    def test_capped_at_one(self):
        adj = compute_agq_size_adjusted(0.90, 10)
        assert adj <= 1.0

    def test_tiny_project_unchanged(self):
        adj = compute_agq_size_adjusted(0.80, 5)
        assert adj == 0.80


class TestComputeAGQEnhanced:
    def test_returns_all_fields(self):
        result = compute_agq_enhanced(0.75, 0.60, 1.0, 0.80, 0.70, 500, "Python")
        assert result.agq_z is not None
        assert result.agq_percentile is not None
        assert result.fingerprint in ["CLEAN","LAYERED","MODERATE","FLAT",
                                       "LOW_COHESION","CYCLIC","TANGLED"]
        assert "severity_level" in result.cycle_severity
        assert "churn_risk_score" in result.churn_risk

    def test_to_dict_serializable(self):
        import json
        result = compute_agq_enhanced(0.65, 0.55, 0.90, 0.50, 0.35, 869, "Java")
        d = result.to_dict()
        json.dumps(d)  # must not raise

    def test_summary_non_empty(self):
        result = compute_agq_enhanced(0.82, 0.50, 1.0, 0.96, 1.0, 167, "Go")
        s = result.summary()
        assert len(s) > 20
