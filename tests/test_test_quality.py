"""Unit tests for test_quality.py — QSE_test metrics."""

import textwrap
from pathlib import Path

import pytest

from qse.test_quality import compute_test_quality


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content))
    return p


class TestComputeTestQuality:
    def test_no_tests_returns_zeros(self, tmp_path):
        """Repo with no test files → all zeros."""
        _write(tmp_path, "src/module.py", "class Order: pass\n")
        result = compute_test_quality(str(tmp_path))
        assert result["qse_test"] == 0.0
        assert result["n_test_files"] == 0
        assert result["n_test_functions"] == 0

    def test_single_test_with_assertion(self, tmp_path):
        """One test file, one function, one assertion."""
        _write(tmp_path, "test_order.py", """\
            def test_order_creation():
                assert True
        """)
        result = compute_test_quality(str(tmp_path))
        assert result["n_test_files"] == 1
        assert result["n_test_functions"] == 1
        assert result["assertion_density"] > 0.0

    def test_assertion_density_capped_at_one(self, tmp_path):
        """3+ assertions per test → density = 1.0."""
        _write(tmp_path, "test_x.py", """\
            def test_many_assertions():
                assert 1 == 1
                assert 2 == 2
                assert 3 == 3
                assert 4 == 4
        """)
        result = compute_test_quality(str(tmp_path))
        assert result["assertion_density"] == 1.0

    def test_naming_quality_descriptive(self, tmp_path):
        """test_should_* names count as descriptive."""
        _write(tmp_path, "test_order.py", """\
            def test_should_create_order():
                assert True
            def test_when_empty_returns_zero():
                assert True
            def test_basic():
                assert True
        """)
        result = compute_test_quality(str(tmp_path))
        # 2 out of 3 are descriptive → 0.666...
        assert result["naming_quality"] == pytest.approx(2 / 3, abs=0.01)

    def test_isolation_score_with_mock(self, tmp_path):
        """Tests using 'mock' or 'mocker' count as isolated."""
        _write(tmp_path, "test_service.py", """\
            def test_with_mock(mocker):
                assert True
            def test_without_mock():
                assert True
        """)
        result = compute_test_quality(str(tmp_path))
        assert result["isolation_score"] == pytest.approx(0.5)

    def test_coverage_potential_with_domain(self, tmp_path):
        """Domain class referenced in test → coverage_potential > 0."""
        _write(tmp_path, "domain/order.py", "class Order: pass\n")
        _write(tmp_path, "test_order.py", """\
            from domain.order import Order
            def test_order():
                o = Order()
                assert o is not None
        """)
        result = compute_test_quality(str(tmp_path))
        assert result["coverage_potential"] > 0.0

    def test_no_domain_classes_coverage_is_one(self, tmp_path):
        """No domain classes → coverage_potential = 1.0 (nothing uncovered)."""
        _write(tmp_path, "test_util.py", """\
            def test_add():
                assert 1 + 1 == 2
        """)
        result = compute_test_quality(str(tmp_path))
        assert result["coverage_potential"] == 1.0

    def test_qse_test_is_mean_of_five(self, tmp_path):
        """qse_test = mean of 5 sub-metrics."""
        _write(tmp_path, "test_x.py", """\
            def test_should_work():
                assert True
        """)
        r = compute_test_quality(str(tmp_path))
        expected = (r["assertion_density"] + r["test_to_code_ratio"] +
                    r["naming_quality"] + r["isolation_score"] +
                    r["coverage_potential"]) / 5.0
        assert r["qse_test"] == pytest.approx(expected, abs=1e-4)

    def test_all_values_in_range(self, tmp_path):
        """All metrics ∈ [0, 1]."""
        _write(tmp_path, "src/core.py", "class Core:\n    def run(self): pass\n")
        _write(tmp_path, "test_core.py", """\
            def test_should_run(mocker):
                assert True
                assert True
        """)
        r = compute_test_quality(str(tmp_path))
        for key in ["assertion_density", "test_to_code_ratio", "naming_quality",
                    "isolation_score", "coverage_potential", "qse_test"]:
            assert 0.0 <= r[key] <= 1.0, f"{key}={r[key]} out of [0,1]"
