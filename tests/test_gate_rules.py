"""Tests for Sprint 0 gate: 3 named rules + counterexample testbed."""

from __future__ import annotations

import json
from pathlib import Path
import textwrap

import networkx as nx
import pytest

from qse.gate.config import (
    BoundaryLeakRule,
    CycleNewRule,
    ForbiddenEdge,
    GateConfig,
    LayerViolationRule,
    ProtectedModule,
    load_config,
)
from qse.gate.report import to_json, to_pr_comment, write_telemetry
from qse.gate.rules import (
    check_boundary_leak,
    check_cycle_new,
    check_layer_violation,
    run_gate,
)


FIXTURES = Path(__file__).parent / "fixtures" / "gate"


# ---------- CYCLE_NEW ----------

def test_cycle_new_mode_any_flags_simple_cycle():
    g = nx.DiGraph()
    g.add_edges_from([("a", "b"), ("b", "a")])
    violations = check_cycle_new(g, base_graph=None, mode="any")
    assert len(violations) == 1
    assert violations[0].rule == "CYCLE_NEW"
    assert {violations[0].source, violations[0].target} == {"a", "b"}


def test_cycle_new_mode_any_passes_dag():
    g = nx.DiGraph()
    g.add_edges_from([("a", "b"), ("b", "c")])
    assert check_cycle_new(g, base_graph=None, mode="any") == []


def test_cycle_new_mode_delta_ignores_preexisting_cycle():
    # Same cycle in base and head → 0 NEW cycles.
    base = nx.DiGraph()
    base.add_edges_from([("a", "b"), ("b", "a")])
    head = base.copy()
    violations = check_cycle_new(head, base_graph=base, mode="delta")
    assert violations == []


def test_cycle_new_mode_delta_detects_added_cycle():
    base = nx.DiGraph()
    base.add_edges_from([("a", "b")])
    head = nx.DiGraph()
    head.add_edges_from([("a", "b"), ("b", "a")])
    violations = check_cycle_new(head, base_graph=base, mode="delta")
    assert len(violations) == 1


def test_cycle_new_flags_self_loop():
    g = nx.DiGraph()
    g.add_edge("a", "a")
    assert len(check_cycle_new(g, base_graph=None, mode="any")) == 1


# ---------- LAYER_VIOLATION ----------

def test_layer_violation_flags_forbidden_edge():
    g = nx.DiGraph()
    g.add_edges_from([
        ("src.domain.user", "src.infra.db"),  # forbidden
        ("src.application.service", "src.domain.user"),  # OK
    ])
    layers = {
        "domain":         ["src.domain.*", "src/domain/**"],
        "application":    ["src.application.*", "src/application/**"],
        "infrastructure": ["src.infra.*", "src/infra/**"],
    }
    forbidden = [ForbiddenEdge(from_layer="domain", to_layer="infrastructure")]
    violations = check_layer_violation(g, layers, forbidden)
    assert len(violations) == 1
    assert violations[0].source == "src.domain.user"
    assert violations[0].target == "src.infra.db"


def test_layer_violation_no_false_positive_when_both_same_layer():
    g = nx.DiGraph()
    g.add_edge("src.infra.db", "src.infra.cache")
    layers = {"infrastructure": ["src.infra.*"]}
    forbidden = [ForbiddenEdge(from_layer="domain", to_layer="infrastructure")]
    assert check_layer_violation(g, layers, forbidden) == []


# ---------- BOUNDARY_LEAK ----------

def test_boundary_leak_flags_unauthorized_caller():
    g = nx.DiGraph()
    g.add_edges_from([
        ("src.random.module", "src.payments.core.engine"),   # leak
        ("src.payments.api.endpoint", "src.payments.core.engine"),  # OK
    ])
    protected = [ProtectedModule(
        module="src.payments.core.*",
        allowed_callers=["src.payments.api.*"],
    )]
    violations = check_boundary_leak(g, protected)
    assert len(violations) == 1
    assert violations[0].source == "src.random.module"


def test_boundary_leak_allows_intra_protected_edges():
    g = nx.DiGraph()
    g.add_edge("src.payments.core.a", "src.payments.core.b")
    protected = [ProtectedModule(
        module="src.payments.core.*",
        allowed_callers=["src.payments.api.*"],
    )]
    assert check_boundary_leak(g, protected) == []


# ---------- run_gate integration ----------

def _config_fixture() -> GateConfig:
    return GateConfig(
        language="python",
        layers={
            "domain":         ["src.domain.*"],
            "infrastructure": ["src.infra.*"],
        },
        cycle_new=CycleNewRule(enabled=True, mode="any"),
        layer_violation=LayerViolationRule(
            enabled=True,
            forbidden=[ForbiddenEdge(from_layer="domain", to_layer="infrastructure")],
        ),
        boundary_leak=BoundaryLeakRule(enabled=False),
    )


def test_run_gate_pass_on_clean_graph():
    g = nx.DiGraph()
    g.add_edges_from([("src.application.svc", "src.domain.user")])
    result = run_gate(head_graph=g, config=_config_fixture())
    assert result.passed
    assert result.violations == []
    assert set(result.rules_evaluated) == {"CYCLE_NEW", "LAYER_VIOLATION"}


def test_run_gate_fail_on_layer_violation():
    g = nx.DiGraph()
    g.add_edge("src.domain.user", "src.infra.db")
    result = run_gate(head_graph=g, config=_config_fixture())
    assert not result.passed
    assert any(v.rule == "LAYER_VIOLATION" for v in result.violations)


def test_run_gate_override_token_passes_with_violations():
    g = nx.DiGraph()
    g.add_edge("src.domain.user", "src.infra.db")
    result = run_gate(
        head_graph=g, config=_config_fixture(),
        override_token="feat: big refactor [skip-qse]",
    )
    assert result.passed
    assert result.override
    assert len(result.violations) == 1


# ---------- TOML config ----------

def test_load_config_rejects_invalid_mode(tmp_path: Path):
    cfg_path = tmp_path / "qse-gate.toml"
    cfg_path.write_text('[rules.cycle_new]\nmode = "Delta"\n')
    with pytest.raises(ValueError, match="mode must be"):
        load_config(cfg_path)


def test_load_config_rejects_non_list_layer(tmp_path: Path):
    cfg_path = tmp_path / "qse-gate.toml"
    cfg_path.write_text('[layers]\ndomain = "src/domain/**"\n')
    with pytest.raises(ValueError, match="must be a list of glob strings"):
        load_config(cfg_path)


def test_load_config_roundtrip(tmp_path: Path):
    toml_src = textwrap.dedent("""
        [gate]
        language = "python"

        [layers]
        domain = ["src/domain/**"]
        infrastructure = ["src/infra/**"]

        [rules.cycle_new]
        enabled = true
        mode = "delta"

        [rules.layer_violation]
        forbidden = [
            { from = "domain", to = "infrastructure" },
        ]

        [rules.boundary_leak]
        protected = [
            { module = "src.core.*", allowed_callers = ["src.api.*"] },
        ]

        [telemetry]
        jsonl_path = "artifacts/gate.jsonl"
    """).strip()
    cfg_path = tmp_path / "qse-gate.toml"
    cfg_path.write_text(toml_src)

    cfg = load_config(cfg_path)

    assert cfg.language == "python"
    assert cfg.cycle_new.mode == "delta"
    assert cfg.layer_violation.forbidden[0].from_layer == "domain"
    assert cfg.boundary_leak.protected[0].module == "src.core.*"
    assert cfg.telemetry.jsonl_path == "artifacts/gate.jsonl"


# ---------- Report formatters ----------

def test_to_json_and_pr_comment_shapes():
    g = nx.DiGraph()
    g.add_edge("src.domain.user", "src.infra.db")
    result = run_gate(head_graph=g, config=_config_fixture())

    payload = json.loads(to_json(result))
    assert payload["gate"] == "FAIL"
    assert payload["violations"]

    md = to_pr_comment(result, repo="PiotrGry/qse-pkg", pr=42)
    assert "QSE Gate: FAIL" in md
    assert "LAYER_VIOLATION" in md
    assert "[skip-qse]" in md


def test_telemetry_jsonl_writes_rows(tmp_path: Path):
    g = nx.DiGraph()
    g.add_edge("src.domain.user", "src.infra.db")
    result = run_gate(head_graph=g, config=_config_fixture())
    out = tmp_path / "artifacts" / "gate.jsonl"
    write_telemetry(result, jsonl_path=str(out), repo="x/y", pr=1, commit="deadbeef")
    lines = [json.loads(l) for l in out.read_text().splitlines()]
    assert any(row["event"] == "rule_evaluated" for row in lines)
    assert any(row["event"] == "violation" for row in lines)


# ---------- Counterexample testbed ----------

@pytest.mark.parametrize("fixture_name", ["event_bus", "cqrs_saga", "plugin_system"])
def test_counterexample_any_mode_flags_cycle(fixture_name: str):
    """mode=any flags the known-good cycle (documents the pattern).

    This is EXPECTED behaviour in Sprint 0 single-scan mode — these fixtures
    exist to verify that Δ mode (below) correctly treats them as non-new.
    """
    from qse.scanner import scan_repo

    repo = FIXTURES / fixture_name
    analysis = scan_repo(str(repo))
    cycles = check_cycle_new(analysis.graph, base_graph=None, mode="any")
    assert len(cycles) >= 1, f"{fixture_name}: expected a cycle; scanner produced none"


@pytest.mark.parametrize("fixture_name", ["event_bus", "cqrs_saga", "plugin_system"])
def test_counterexample_delta_mode_passes_when_base_equals_head(fixture_name: str):
    """mode=delta with identical base and head → 0 new cycles (ring is not new)."""
    from qse.scanner import scan_repo

    repo = FIXTURES / fixture_name
    analysis = scan_repo(str(repo))
    head = analysis.graph
    base = analysis.graph.copy()
    cycles = check_cycle_new(head, base_graph=base, mode="delta")
    assert cycles == [], f"{fixture_name}: Δ mode incorrectly flagged pre-existing cycle"


# ---- A2.2 glob regression tests ----

def test_scanner_globstar_matches_direct_children():
    """qse/**/*.py must match qse/scanner.py (one level, not just nested)."""
    from qse.scanner import scan_repo
    import pathlib
    repo = str(pathlib.Path(".").resolve())
    analysis = scan_repo(".", include=["qse/**/*.py"], exclude=[])
    files_abs = {str(pathlib.Path(f).resolve()) for f in analysis.files}
    assert repo + "/qse/scanner.py" in files_abs
    assert repo + "/qse/__init__.py" in files_abs


def test_scanner_globstar_matches_nested():
    """qse/**/*.py must also match qse/gate/hook_runner.py (nested)."""
    from qse.scanner import scan_repo
    import pathlib
    repo = str(pathlib.Path(".").resolve())
    analysis = scan_repo(".", include=["qse/**/*.py"], exclude=[])
    files_abs = {str(pathlib.Path(f).resolve()) for f in analysis.files}
    assert repo + "/qse/gate/hook_runner.py" in files_abs


def test_scanner_exclude_globstar():
    """exclude ['**/__pycache__/**'] must not block real source files."""
    from qse.scanner import scan_repo
    import pathlib
    repo = str(pathlib.Path(".").resolve())
    analysis = scan_repo(
        ".", include=["qse/**/*.py"],
        exclude=["**/__pycache__/**", "**/target/**"],
    )
    files_abs = {str(pathlib.Path(f).resolve()) for f in analysis.files}
    assert repo + "/qse/scanner.py" in files_abs


def test_scanner_character_class_glob():
    """Character-class patterns like [abc]*.py must selectively match .py files."""
    from qse.scanner import scan_repo
    import pathlib, tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        (pathlib.Path(tmp) / "alpha.py").write_text("x=1")
        (pathlib.Path(tmp) / "beta.py").write_text("x=1")
        (pathlib.Path(tmp) / "zeta.py").write_text("x=1")
        # [ab]*.py matches alpha.py and beta.py but not zeta.py
        a = scan_repo(tmp, include=["[ab]*.py"], exclude=[])
        rels = {os.path.basename(f) for f in a.files}
        assert "alpha.py" in rels
        assert "beta.py" in rels
        assert "zeta.py" not in rels
        # [!ab]*.py should match only zeta.py
        b = scan_repo(tmp, include=["[!ab]*.py"], exclude=[])
        rels_b = {os.path.basename(f) for f in b.files}
        assert "zeta.py" in rels_b
        assert "alpha.py" not in rels_b


def test_scanner_exclude_actually_drops_file():
    """exclude must remove matching files, not merely not-break others."""
    from qse.scanner import scan_repo
    import pathlib, tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        (pathlib.Path(tmp) / "keep.py").write_text("x=1")
        cache = pathlib.Path(tmp) / "__pycache__"
        cache.mkdir()
        (cache / "drop.py").write_text("x=1")
        a = scan_repo(tmp, include=["**/*.py"], exclude=["**/__pycache__/**"])
        rels = {os.path.relpath(f, tmp).replace(os.sep, "/") for f in a.files}
        assert "keep.py" in rels
        assert "__pycache__/drop.py" not in rels


def test_proposed_module_name_matches_scanner_convention():
    """_proposed_module_name must return pkg.__init__ for __init__.py."""
    from pathlib import Path
    from qse.gate.hook_runner import _proposed_module_name
    from qse.scanner import _module_path
    repo = Path(".").resolve()
    init = repo / "qse" / "__init__.py"
    hook_name = _proposed_module_name(repo, init)
    scanner_name = _module_path(str(init), str(repo))
    assert hook_name == scanner_name, (
        f"hook says {hook_name!r}, scanner says {scanner_name!r}"
    )


def test_find_project_root_stays_inside_git_tree(tmp_path):
    """_find_project_root must not walk above the git toplevel."""
    from pathlib import Path
    from unittest.mock import patch
    from qse.gate.hook_runner import _find_project_root
    # Repo root at /fake/repo, no qse-gate.toml anywhere → returns git_top.
    with patch("qse.gate.hook_runner._git_repo_root", return_value=Path("/fake/repo")):
        with patch("pathlib.Path.is_file", return_value=False):
            result = _find_project_root(Path("/fake/repo/sub/dir"))
    # Must be git_top itself, not its parent.
    assert result == Path("/fake/repo")


def test_find_project_root_finds_config_at_git_root(tmp_path):
    """Config at the git root itself must be found (no off-by-one)."""
    from pathlib import Path
    from unittest.mock import patch
    from qse.gate.hook_runner import _find_project_root

    def fake_is_file(self):
        return str(self) == "/fake/repo/qse-gate.toml"

    with patch("qse.gate.hook_runner._git_repo_root", return_value=Path("/fake/repo")):
        with patch("pathlib.Path.is_file", new=fake_is_file):
            result = _find_project_root(Path("/fake/repo/sub"))
    assert result == Path("/fake/repo")
