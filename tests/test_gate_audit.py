"""Tests for the audit aggregator (qse/gate/audit.py)."""

from __future__ import annotations

import json
from pathlib import Path
import textwrap

import networkx as nx
import pytest

from qse.gate.audit import (
    AuditReport,
    ComponentRisk,
    _priority_for,
    audit_from_gate_result,
    to_markdown,
)
from qse.gate.config import (
    BoundaryLeakRule,
    CycleNewRule,
    ForbiddenEdge,
    GateConfig,
    LayerViolationRule,
    ProtectedModule,
)
from qse.gate.rules import run_gate


def _cfg_all_enabled() -> GateConfig:
    return GateConfig(
        language="python",
        layers={
            "domain":         ["src.domain.*"],
            "application":    ["src.application.*"],
            "infrastructure": ["src.infra.*"],
        },
        cycle_new=CycleNewRule(enabled=True, mode="any"),
        layer_violation=LayerViolationRule(
            enabled=True,
            forbidden=[
                ForbiddenEdge(from_layer="domain", to_layer="infrastructure"),
                ForbiddenEdge(from_layer="domain", to_layer="application"),
            ],
        ),
        boundary_leak=BoundaryLeakRule(
            enabled=True,
            protected=[ProtectedModule(
                module="src.infra.payments_core*",
                allowed_callers=["src.payments_api.*"],
            )],
        ),
    )


# ---------- priority bucketing ----------

def test_priority_scc_auto_promotes_to_p1():
    assert _priority_for(score=5.0, in_scc=True) == "P1"


def test_priority_threshold_boundaries():
    assert _priority_for(score=60.0, in_scc=False) == "P1"
    assert _priority_for(score=59.9, in_scc=False) == "P2"
    assert _priority_for(score=30.0, in_scc=False) == "P2"
    assert _priority_for(score=29.9, in_scc=False) == "P3"


# ---------- audit on clean graph ----------

def test_audit_clean_graph_is_green_and_empty():
    g = nx.DiGraph()
    g.add_edges_from([
        ("src.application.svc", "src.domain.user"),
        ("src.infra.db", "src.domain.user"),
    ])
    result = run_gate(head_graph=g, config=_cfg_all_enabled())
    report = audit_from_gate_result(repo="demo", result=result, head_graph=g)

    assert report.total_violations == 0
    assert report.health_score == 100.0
    assert report.health_band == "green"
    assert report.top_risks == []
    assert report.recommendations  # at least one "keep going" message


# ---------- audit with cycle ----------

def test_audit_cycle_promotes_modules_to_p1():
    g = nx.DiGraph()
    # Three-node cycle, all in src.application (doesn't trip layering)
    g.add_edges_from([
        ("src.application.a", "src.application.b"),
        ("src.application.b", "src.application.c"),
        ("src.application.c", "src.application.a"),
    ])
    result = run_gate(head_graph=g, config=_cfg_all_enabled())
    report = audit_from_gate_result(repo="cycle-demo", result=result, head_graph=g)

    assert report.total_violations >= 1
    assert report.health_band in {"yellow", "orange", "red"}
    assert any(r.priority == "P1" for r in report.top_risks)
    assert any(r.in_scc for r in report.top_risks)


# ---------- audit with layer violation ----------

def test_audit_layer_violation_surfaces_in_risks():
    g = nx.DiGraph()
    g.add_edge("src.domain.user", "src.infra.db")
    result = run_gate(head_graph=g, config=_cfg_all_enabled())
    report = audit_from_gate_result(repo="layer-demo", result=result, head_graph=g)

    assert report.violations_by_rule.get("LAYER_VIOLATION", 0) >= 1
    modules = {r.module for r in report.top_risks}
    assert "src.domain.user" in modules or "src.infra.db" in modules


# ---------- audit with boundary leak ----------

def test_audit_boundary_leak_surfaces_caller_as_risk():
    g = nx.DiGraph()
    g.add_edge("src.analytics.tracker", "src.infra.payments_core.charge")
    result = run_gate(head_graph=g, config=_cfg_all_enabled())
    report = audit_from_gate_result(repo="leak-demo", result=result, head_graph=g)

    modules = {r.module for r in report.top_risks}
    assert "src.analytics.tracker" in modules


# ---------- markdown renderer ----------

def test_markdown_contains_expected_sections():
    g = nx.DiGraph()
    g.add_edges_from([
        ("src.application.a", "src.application.b"),
        ("src.application.b", "src.application.a"),
        ("src.domain.user", "src.infra.db"),
    ])
    result = run_gate(head_graph=g, config=_cfg_all_enabled())
    report = audit_from_gate_result(repo="md-demo", result=result, head_graph=g)

    md = to_markdown(report)
    assert "# AI-Drift Firewall" in md
    assert "## Executive summary" in md
    assert "## Recommendations" in md
    assert "## Top at-risk components" in md
    assert "## Raw violations" in md
    assert "CYCLE_NEW" in md or "LAYER_VIOLATION" in md


# ---------- JSON serialization ----------

def test_report_json_serializable():
    g = nx.DiGraph()
    g.add_edges_from([("a", "b"), ("b", "a")])
    result = run_gate(head_graph=g, config=_cfg_all_enabled())
    report = audit_from_gate_result(repo="json-demo", result=result, head_graph=g)
    data = report.to_dict()
    dumped = json.dumps(data)
    # Round-trip
    parsed = json.loads(dumped)
    assert parsed["repo"] == "json-demo"
    assert "health_score" in parsed
    assert isinstance(parsed["top_risks"], list)


# ---------- health score edge cases ----------

def test_health_score_empty_graph_is_green():
    g = nx.DiGraph()
    result = run_gate(head_graph=g, config=_cfg_all_enabled())
    report = audit_from_gate_result(repo="empty", result=result, head_graph=g)
    assert report.health_score == 100.0
    assert report.health_band == "green"


def test_health_score_monotone_with_violations():
    """More violations at fixed edge count → lower health score."""
    cfg = _cfg_all_enabled()

    def health(num_cycles: int) -> float:
        g = nx.DiGraph()
        g.add_edges_from([("hub", f"n{i}") for i in range(10)])
        # Add self-loops (each counts as a cycle)
        for i in range(num_cycles):
            g.add_edge(f"cyc{i}", f"cyc{i}")
        return audit_from_gate_result(
            repo="m", result=run_gate(head_graph=g, config=cfg), head_graph=g,
        ).health_score

    assert health(0) >= health(1) >= health(3) >= health(6)


# ---------- CLI runner smoke ----------

def test_audit_runner_cli_on_tmp_repo(tmp_path: Path):
    """End-to-end: run qse-audit programmatically on a tmp layered repo."""
    from qse.gate.audit_runner import main as audit_main

    # Flat-layout repo so scanner picks up intra-package edges cleanly.
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "a.py").write_text("from .b import x\nx = 1\n")
    (tmp_path / "b.py").write_text("from .a import x\n")
    cfg = tmp_path / "qse-gate.toml"
    cfg.write_text(textwrap.dedent("""
        [gate]
        language = "python"
        [rules.cycle_new]
        enabled = true
        mode = "any"
        [rules.layer_violation]
        enabled = false
        [rules.boundary_leak]
        enabled = false
    """).strip())

    out_md = tmp_path / "audit.md"
    out_json = tmp_path / "audit.json"
    rc = audit_main([
        str(tmp_path),
        "--config", str(cfg),
        "--output-md", str(out_md),
        "--output-json", str(out_json),
        "--repo-label", "tmp-demo",
    ])
    assert rc == 0
    md = out_md.read_text()
    assert "tmp-demo" in md
    assert "CYCLE_NEW" in md
    data = json.loads(out_json.read_text())
    assert data["repo"] == "tmp-demo"
    assert data["total_violations"] >= 1
