"""Tests for TRL4 gate wrapper (constraints + ratchet)."""

import json
from pathlib import Path
from types import SimpleNamespace

import networkx as nx

from qse.trl4_gate import (
    TRL4Rules,
    check_constraints_graph,
    compute_constraint_score,
    run_trl4_gate,
)


class DummyReport:
    def __init__(self, qse_total: float):
        self.qse_total = qse_total
        self.defects = {}

    def to_dict(self):
        return {"metrics": {}}


def _graph_with_edge(src: str, tgt: str) -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_edge(src, tgt)
    return g


def test_check_constraints_detects_violation():
    g = _graph_with_edge("api.routes", "core.user")
    rules = [{"name": "no_api_core", "from": "api/*", "to": "core/*", "type": "forbidden"}]
    violations = check_constraints_graph(g, rules)
    assert len(violations) == 1
    assert violations[0]["source"] == "api.routes"
    assert violations[0]["target"] == "core.user"


def test_constraint_score_bounds():
    g = _graph_with_edge("api.routes", "core.user")
    assert compute_constraint_score(g, []) == 1.0
    assert compute_constraint_score(g, [{"source": "api.routes", "target": "core.user", "rule": {}}]) == 0.0


def test_run_trl4_gate_fails_on_constraint_violation(monkeypatch, tmp_path):
    def fake_analyze_repo(_path, _cfg):
        return DummyReport(qse_total=0.90)

    def fake_scan_repo(_path, layer_map=None):
        return SimpleNamespace(graph=_graph_with_edge("api.routes", "core.user"))

    monkeypatch.setattr("qse.trl4_gate.analyze_repo", fake_analyze_repo)
    monkeypatch.setattr("qse.trl4_gate.scan_repo", fake_scan_repo)

    rules = TRL4Rules(
        threshold=0.80,
        min_constraint_score=0.95,
        constraints=[{"name": "no_api_core", "from": "api/*", "to": "core/*", "type": "forbidden"}],
        ratchet_enabled=False,
    )
    result = run_trl4_gate(str(tmp_path), rules=rules)
    assert not result.passed
    assert any("Constraint score=" in f for f in result.failures)


def test_run_trl4_gate_ratchet_blocks_regression(monkeypatch, tmp_path):
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(json.dumps({"qse_total": 0.90, "constraint_score": 1.0}))

    def fake_analyze_repo(_path, _cfg):
        return DummyReport(qse_total=0.85)

    def fake_scan_repo(_path, layer_map=None):
        g = nx.DiGraph()
        g.add_edge("application.service", "domain.order")
        return SimpleNamespace(graph=g)

    monkeypatch.setattr("qse.trl4_gate.analyze_repo", fake_analyze_repo)
    monkeypatch.setattr("qse.trl4_gate.scan_repo", fake_scan_repo)

    rules = TRL4Rules(
        threshold=0.0,
        min_constraint_score=0.0,
        constraints=[],
        ratchet_enabled=True,
        ratchet_baseline_file=str(baseline_file),
        ratchet_delta=0.0,
        ratchet_update_on_pass=True,
    )
    result = run_trl4_gate(str(tmp_path), rules=rules)
    assert not result.passed
    assert any("Ratchet violation" in f for f in result.failures)


def test_run_trl4_gate_creates_and_updates_baseline(monkeypatch, tmp_path):
    baseline_file = tmp_path / "baseline.json"
    qse_values = [0.82, 0.86]

    def fake_analyze_repo(_path, _cfg):
        return DummyReport(qse_total=qse_values.pop(0))

    def fake_scan_repo(_path, layer_map=None):
        g = nx.DiGraph()
        g.add_edge("application.service", "domain.order")
        return SimpleNamespace(graph=g)

    monkeypatch.setattr("qse.trl4_gate.analyze_repo", fake_analyze_repo)
    monkeypatch.setattr("qse.trl4_gate.scan_repo", fake_scan_repo)

    rules = TRL4Rules(
        threshold=0.80,
        min_constraint_score=0.0,
        constraints=[],
        ratchet_enabled=True,
        ratchet_baseline_file=str(baseline_file),
        ratchet_delta=0.0,
        ratchet_update_on_pass=True,
    )

    first = run_trl4_gate(str(tmp_path), rules=rules)
    assert first.passed
    assert baseline_file.exists()
    saved_1 = json.loads(baseline_file.read_text())
    assert abs(saved_1["qse_total"] - 0.82) < 1e-9

    second = run_trl4_gate(str(tmp_path), rules=rules)
    assert second.passed
    saved_2 = json.loads(baseline_file.read_text())
    assert abs(saved_2["qse_total"] - 0.86) < 1e-9

