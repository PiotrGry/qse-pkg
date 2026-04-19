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

    # Post-recalibration (Codex 2026-04-19): 1 cycle violation in a 3-edge toy
    # graph no longer screams "severe drift" — it shows up as green/yellow with
    # the SCC still ranked P1. That's the point: the priority flag still fires,
    # the health band reflects the small absolute impact.
    assert report.total_violations >= 1
    assert report.health_band in {"green", "yellow"}
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

def test_scc_members_surface_full_cycle_as_risks():
    """Fix #1 (Codex 2026-04-19): a 5-node cycle must rank all 5 nodes, not
    just the SCC-representative edge's 2 endpoints."""
    g = nx.DiGraph()
    g.add_edges_from([
        ("src.application.a", "src.application.b"),
        ("src.application.b", "src.application.c"),
        ("src.application.c", "src.application.d"),
        ("src.application.d", "src.application.e"),
        ("src.application.e", "src.application.a"),
    ])
    result = run_gate(head_graph=g, config=_cfg_all_enabled())
    # The rule must emit scc_members
    cycle_violations = [v for v in result.violations if v.rule == "CYCLE_NEW"]
    assert cycle_violations, "expected at least one CYCLE_NEW"
    assert len(cycle_violations[0].scc_members) == 5

    report = audit_from_gate_result(repo="scc5", result=result, head_graph=g, top_n=10)
    ranked = {r.module for r in report.top_risks}
    assert ranked == {
        "src.application.a", "src.application.b", "src.application.c",
        "src.application.d", "src.application.e",
    }
    # All should be P1 (SCC auto-promotes)
    assert all(r.priority == "P1" for r in report.top_risks)


def test_score_calibration_small_repo_not_severe():
    """Fix #2 (Codex 2026-04-19): 2 violations in a 10-edge graph must not
    report 0/100 'severe drift'. Under recalibrated thresholds the small-count
    cap keeps health >= 70 (yellow) for < 5 violations."""
    g = nx.DiGraph()
    g.add_edges_from([
        ("src.domain.user", "src.infra.db"),     # LAYER_VIOLATION
        ("src.domain.user2", "src.infra.cache"), # LAYER_VIOLATION
    ] + [(f"n{i}", f"n{i+1}") for i in range(8)])
    # total_edges = 10, total_violations = 2
    result = run_gate(head_graph=g, config=_cfg_all_enabled())
    report = audit_from_gate_result(repo="small", result=result, head_graph=g)
    assert report.total_violations == 2
    assert report.health_score >= 70.0
    assert report.health_band in {"yellow", "green"}


def test_score_calibration_many_violations_does_degrade():
    """Sanity check: the small-count cap only applies below 5 violations.
    At 10 violations in a 40-edge graph we should see the band drop."""
    g = nx.DiGraph()
    # 10 LAYER violations + some DAG edges
    for i in range(10):
        g.add_edge(f"src.domain.mod{i}", f"src.infra.mod{i}")
    for i in range(30):
        g.add_edge(f"pkg.a{i}", f"pkg.b{i}")
    result = run_gate(head_graph=g, config=_cfg_all_enabled())
    report = audit_from_gate_result(repo="big", result=result, head_graph=g)
    assert report.total_violations == 10
    assert report.health_band in {"yellow", "orange", "red"}


def test_delta_classification_flags_only_new_violations():
    """Fix #3 (Codex 2026-04-19): with a base graph, violations present in
    both base and head are marked 'existing'; violations only in head are 'new'."""
    base = nx.DiGraph()
    base.add_edges_from([
        ("src.domain.user", "src.infra.db"),    # LAYER_VIOLATION (already existing)
    ])
    head = base.copy()
    head.add_edges_from([
        ("src.domain.user2", "src.infra.cache"),  # NEW LAYER_VIOLATION
    ])

    cfg = _cfg_all_enabled()
    head_result = run_gate(head_graph=head, config=cfg)
    base_result = run_gate(head_graph=base, config=cfg)

    report = audit_from_gate_result(
        repo="delta-demo",
        result=head_result,
        head_graph=head,
        base_graph=base,
        base_result=base_result,
    )
    assert report.delta is not None
    assert report.delta.new == 1
    assert report.delta.existing == 1
    assert report.delta.resolved == 0

    # First-seen annotation on ranked components
    first_seen_by_mod = {r.module: r.first_seen for r in report.top_risks}
    assert first_seen_by_mod["src.domain.user2"] == "new"
    assert first_seen_by_mod["src.domain.user"] == "existing"


def test_delta_markdown_includes_delta_line_and_column():
    base = nx.DiGraph()
    base.add_edge("src.domain.user", "src.infra.db")
    head = base.copy()
    head.add_edge("src.domain.user2", "src.infra.cache")

    cfg = _cfg_all_enabled()
    report = audit_from_gate_result(
        repo="delta-md",
        result=run_gate(head_graph=head, config=cfg),
        head_graph=head,
        base_graph=base,
        base_result=run_gate(head_graph=base, config=cfg),
    )
    md = to_markdown(report)
    assert "Δ vs base" in md
    assert "🆕 new" in md
    assert "existing" in md


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


# ---- Slice 4.2: Codex challenge round 2 regression tests ----


def _cfg_cycle_only() -> GateConfig:
    return GateConfig(
        language="python",
        layers={},
        cycle_new=CycleNewRule(enabled=True, mode="any"),
        layer_violation=LayerViolationRule(enabled=False, forbidden=[]),
        boundary_leak=BoundaryLeakRule(enabled=False, protected=[]),
    )


def test_delta_cycle_key_stable_across_edge_insertion_order():
    import networkx as nx
    from qse.gate.audit import audit_from_gate_result
    cfg = _cfg_cycle_only()
    base = nx.DiGraph()
    for e in [('c','a'),('a','b'),('b','c')]:
        base.add_edge(*e)
    head = nx.DiGraph()
    for e in [('a','b'),('b','c'),('c','a')]:
        head.add_edge(*e)
    br = run_gate(head_graph=base, config=cfg)
    hr = run_gate(head_graph=head, config=cfg)
    rep = audit_from_gate_result(
        repo="x", result=hr, head_graph=head,
        base_graph=base, base_result=br,
    )
    assert rep.delta.existing == 1
    assert rep.delta.new == 0
    assert rep.delta.resolved == 0


def test_cycle_self_loop_not_double_counted_when_in_multi_scc():
    import networkx as nx
    cfg = _cfg_cycle_only()
    g = nx.DiGraph()
    g.add_edge("a", "b"); g.add_edge("b", "a"); g.add_edge("a", "a")
    result = run_gate(head_graph=g, config=cfg)
    # Before the fix: 2 CYCLE_NEW violations (one for {a,b}, one for {a}).
    assert len(result.violations) == 1


def test_base_graph_without_base_result_raises():
    import networkx as nx
    import pytest
    from qse.gate.audit import audit_from_gate_result
    cfg = _cfg_cycle_only()
    g = nx.DiGraph(); g.add_edge("a","b"); g.add_edge("b","a")
    r = run_gate(head_graph=g, config=cfg)
    with pytest.raises(ValueError):
        audit_from_gate_result(
            repo="x", result=r, head_graph=g,
            base_graph=g, base_result=None,
        )


def test_top_risks_ordering_is_deterministic_for_equal_scores():
    import networkx as nx
    from qse.gate.audit import audit_from_gate_result
    cfg = _cfg_cycle_only()
    g = nx.DiGraph()
    g.add_edges_from([('a','b'),('b','c'),('c','d'),('d','e'),('e','a')])
    orders = set()
    for _ in range(5):
        rep = audit_from_gate_result(
            repo="x", result=run_gate(head_graph=g, config=cfg),
            head_graph=g, top_n=10,
        )
        orders.add(tuple(r.module for r in rep.top_risks))
    assert len(orders) == 1


def test_health_density_escape_hatch_flags_half_broken_repo():
    import networkx as nx
    from qse.gate.config import GateConfig, CycleNewRule, LayerViolationRule, BoundaryLeakRule, ForbiddenEdge
    from qse.gate.audit import audit_from_gate_result
    cfg = GateConfig(
        language="python",
        layers={"d": ["src.d.*"], "i": ["src.i.*"]},
        cycle_new=CycleNewRule(enabled=False, mode="any"),
        layer_violation=LayerViolationRule(
            enabled=True,
            forbidden=[ForbiddenEdge(from_layer="d", to_layer="i")],
        ),
        boundary_leak=BoundaryLeakRule(enabled=False, protected=[]),
    )
    g = nx.DiGraph()
    for i in range(4):
        g.add_edge(f"src.d.m{i}", f"src.i.m{i}")
    rep = audit_from_gate_result(
        repo="x", result=run_gate(head_graph=g, config=cfg), head_graph=g,
    )
    # Half-broken repo must not be hidden by the small-count cap.
    assert rep.health_band == "red"
