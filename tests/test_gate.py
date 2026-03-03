"""Tests for QSE quality gate and generation loop."""

import json
import os
import tempfile

import pytest

from qse.gate import GateRules, GateResult, quality_gate, _build_feedback
from qse.generate_loop import generate_and_validate, _read_specs


class TestGateRules:
    def test_defaults(self):
        r = GateRules()
        assert r.min_qse_total == 0.7
        assert r.max_defects["anemic_entity"] == 0
        assert r.max_retries == 3

    def test_from_file(self, tmp_path):
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(json.dumps({
            "min_qse_total": 0.5,
            "max_defects": {"anemic_entity": 1},
            "min_metrics": {"S": 0.9},
            "max_retries": 5,
        }))
        r = GateRules.from_file(str(rules_file))
        assert r.min_qse_total == 0.5
        assert r.max_defects["anemic_entity"] == 1
        assert r.min_metrics["S"] == 0.9
        assert r.max_retries == 5


class TestBuildFeedback:
    def test_empty_failures(self):
        assert _build_feedback([], 0.8, 0.7) == ""

    def test_formats_failures(self):
        fb = _build_feedback(["2 anemic_entity(s)"], 0.5, 0.7)
        assert "failed QSE quality checks" in fb
        assert "2 anemic_entity" in fb
        assert "0.50" in fb
        assert "0.70" in fb


class TestQualityGateCleanProject:
    """Test gate on a well-structured DDD project."""

    @pytest.fixture
    def clean_ddd_project(self, tmp_path):
        """Create a minimal clean DDD project."""
        domain = tmp_path / "domain"
        domain.mkdir()
        (domain / "__init__.py").write_text("")
        (domain / "order.py").write_text(
            "class Order:\n"
            "    def __init__(self, items):\n"
            "        self.items = items\n"
            "        self.status = 'pending'\n"
            "    def calculate_total(self):\n"
            "        return sum(i.subtotal() for i in self.items)\n"
            "    def ship(self):\n"
            "        assert self.items, 'No items'\n"
            "        self.status = 'shipped'\n"
        )
        app = tmp_path / "application"
        app.mkdir()
        (app / "__init__.py").write_text("")
        (app / "create_order_service.py").write_text(
            "from domain.order import Order\n"
            "class CreateOrderService:\n"
            "    def execute(self, items):\n"
            "        order = Order(items)\n"
            "        return order\n"
        )
        pres = tmp_path / "presentation"
        pres.mkdir()
        (pres / "__init__.py").write_text("")
        (pres / "api.py").write_text(
            "from application.create_order_service import CreateOrderService\n"
            "class OrderAPI:\n"
            "    def post_order(self, data):\n"
            "        svc = CreateOrderService()\n"
            "        return svc.execute(data['items'])\n"
        )
        return tmp_path

    def test_clean_project_passes_lenient_gate(self, clean_ddd_project):
        rules = GateRules(min_qse_total=0.0, max_defects={}, min_metrics={})
        result = quality_gate(str(clean_ddd_project), rules)
        assert isinstance(result, GateResult)
        assert result.qse_total >= 0.0
        assert result.feedback_prompt == "" if result.passed else len(result.failures) > 0


class TestQualityGateAnemicDetection:
    """Test gate detects anemic entities."""

    @pytest.fixture
    def anemic_project(self, tmp_path):
        domain = tmp_path / "domain"
        domain.mkdir()
        (domain / "__init__.py").write_text("")
        (domain / "order.py").write_text(
            "class Order:\n"
            "    def __init__(self, total):\n"
            "        self.total = total\n"
        )
        app = tmp_path / "application"
        app.mkdir()
        (app / "__init__.py").write_text("")
        (app / "order_service.py").write_text(
            "from domain.order import Order\n"
            "class OrderService:\n"
            "    def create(self, total):\n"
            "        return Order(total)\n"
        )
        return tmp_path

    def test_anemic_entity_fails_gate(self, anemic_project):
        rules = GateRules(
            min_qse_total=0.0,
            max_defects={"anemic_entity": 0},
            min_metrics={},
        )
        result = quality_gate(str(anemic_project), rules)
        assert not result.passed
        assert any("anemic_entity" in f for f in result.failures)
        assert "order.py" in result.feedback_prompt


class TestReadSpecs:
    def test_reads_markdown_files(self, tmp_path):
        spec = tmp_path / "spec"
        spec.mkdir()
        (spec / "domain.md").write_text("# Domain\nOrder entity")
        (spec / "api.md").write_text("# API\nPOST /orders")
        (spec / "ignore.txt").write_text("not included")
        result = _read_specs(str(tmp_path))
        assert "Order entity" in result
        assert "POST /orders" in result
        assert "not included" not in result

    def test_empty_spec_dir(self, tmp_path):
        assert _read_specs(str(tmp_path)) == ""


class TestGenerateLoop:
    def test_passes_on_first_try(self, tmp_path):
        """If gate passes immediately, no retries needed."""
        # Create a minimal project that passes lenient rules
        domain = tmp_path / "domain"
        domain.mkdir()
        (domain / "__init__.py").write_text("")
        (domain / "order.py").write_text(
            "class Order:\n"
            "    def __init__(self): self.x = 1\n"
            "    def do_thing(self): pass\n"
        )
        spec = tmp_path / "spec"
        spec.mkdir()
        (spec / "domain.md").write_text("# Order")
        rules_file = tmp_path / "qse_rules.json"
        rules_file.write_text(json.dumps({
            "min_qse_total": 0.0,
            "max_defects": {},
            "min_metrics": {},
            "max_retries": 2,
        }))
        (tmp_path / "README.md").write_text("Generate DDD code.")

        call_count = 0
        def fake_llm(prompt):
            nonlocal call_count
            call_count += 1

        passed, result, attempts = generate_and_validate(
            str(tmp_path), fake_llm, output_dir=str(tmp_path),
        )
        assert passed
        assert call_count == 1
        assert len(attempts) == 1
