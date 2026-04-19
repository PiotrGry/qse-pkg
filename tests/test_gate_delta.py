"""Integration tests for Δ mode: builds a real git repo in tmp_path,
commits a layered base, then adds a cycle in a second commit, and verifies
CYCLE_NEW delta mode flags exactly the new cycle."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import textwrap

import pytest

from qse.gate.runner import main as run_cli


GATE_CFG_DELTA = textwrap.dedent("""
    [gate]
    language = "python"

    [rules.cycle_new]
    enabled = true
    mode = "delta"

    [rules.layer_violation]
    enabled = false

    [rules.boundary_leak]
    enabled = false
""").strip()


def _git(cwd: Path, *args: str) -> None:
    env = dict(os.environ)
    env.setdefault("GIT_AUTHOR_NAME", "test")
    env.setdefault("GIT_AUTHOR_EMAIL", "test@example.com")
    env.setdefault("GIT_COMMITTER_NAME", "test")
    env.setdefault("GIT_COMMITTER_EMAIL", "test@example.com")
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=env)


def _write_package(root: Path, relpath: str, body: str) -> None:
    p = root / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def _init_base_repo(root: Path) -> None:
    """Create a small layered DAG (no cycles) and commit it.

    Layout is flat (a.py / b.py / c.py at repo root) so the scanner module
    names match what relative imports emit — scanner sees {a, b, c}, relative
    imports emit {a, b, c}. If nested under `pkg/`, scanner emits `pkg.a`
    while `from .c` emits bare `c`, and the cycle is invisible.
    """
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _write_package(root, "__init__.py", "")
    _write_package(root, "a.py", "x = 1\n")
    _write_package(root, "b.py", "from .a import x\n")
    _write_package(root, "c.py", "from .b import x\n")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "base: no cycles")


def _add_cycle_commit(root: Path) -> None:
    """Mutate `a.py` to import from `c.py`, creating cycle a→c→b→a."""
    (root / "a.py").write_text("from .c import x\nx = 1\n")
    _git(root, "add", "a.py")
    _git(root, "commit", "-q", "-m", "feat: add cycle (head)")


def _write_cfg(tmp: Path) -> Path:
    p = tmp / "qse-gate.toml"
    p.write_text(GATE_CFG_DELTA)
    return p


# ---------- --base-path ----------

def test_delta_via_base_path_same_tree_passes(tmp_path: Path):
    """If base == head (same tree), delta mode finds no new cycles."""
    head = tmp_path / "head"
    _init_base_repo(head)
    _add_cycle_commit(head)  # has the cycle in both

    base = tmp_path / "base"
    base.mkdir()
    # Copy current tree to base (same content)
    for p in head.rglob("*.py"):
        rel = p.relative_to(head)
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(p.read_text())

    cfg = _write_cfg(tmp_path)
    rc = run_cli([str(head), "--config", str(cfg), "--base-path", str(base)])
    assert rc == 0


def test_delta_via_base_path_flags_new_cycle(tmp_path: Path):
    """Head introduces a cycle not in base. Delta flags it."""
    head = tmp_path / "head"
    _init_base_repo(head)
    _add_cycle_commit(head)

    # Base = pre-cycle version extracted via worktree
    base = tmp_path / "base"
    _git(head, "worktree", "add", "--quiet", str(base), "HEAD~1")
    try:
        cfg = _write_cfg(tmp_path)
        out_json = tmp_path / "report.json"
        rc = run_cli([str(head), "--config", str(cfg),
                      "--base-path", str(base),
                      "--output-json", str(out_json)])
        assert rc == 1
        report = json.loads(out_json.read_text())
        assert report["gate"] == "FAIL"
        rules = {v["rule"] for v in report["violations"]}
        assert "CYCLE_NEW" in rules
    finally:
        _git(head, "worktree", "remove", "--force", str(base))


# ---------- --base-ref ----------

def test_delta_via_base_ref_passes_when_no_new_cycle(tmp_path: Path):
    """Base-ref points at HEAD itself. Nothing is new, delta passes."""
    head = tmp_path / "repo"
    _init_base_repo(head)
    _add_cycle_commit(head)

    cfg = _write_cfg(tmp_path)
    rc = run_cli([str(head), "--config", str(cfg), "--base-ref", "HEAD"])
    assert rc == 0


def test_delta_via_base_ref_flags_new_cycle(tmp_path: Path):
    """Base-ref = HEAD~1 (pre-cycle). Head has the cycle. Delta flags it."""
    head = tmp_path / "repo"
    _init_base_repo(head)
    _add_cycle_commit(head)

    cfg = _write_cfg(tmp_path)
    out_json = tmp_path / "report.json"
    pr_md = tmp_path / "pr.md"
    rc = run_cli([str(head), "--config", str(cfg),
                  "--base-ref", "HEAD~1",
                  "--output-json", str(out_json),
                  "--pr-comment", str(pr_md)])
    assert rc == 1
    report = json.loads(out_json.read_text())
    assert report["gate"] == "FAIL"
    assert any(v["rule"] == "CYCLE_NEW" for v in report["violations"])
    # PR markdown should mention the rule
    assert "CYCLE_NEW" in pr_md.read_text()


# ---------- delta + override ----------

def test_delta_override_token_passes_with_new_cycle(tmp_path: Path):
    """[skip-qse] in override token flips FAIL to PASS with violations logged."""
    head = tmp_path / "repo"
    _init_base_repo(head)
    _add_cycle_commit(head)

    cfg = _write_cfg(tmp_path)
    rc = run_cli([str(head), "--config", str(cfg),
                  "--base-ref", "HEAD~1",
                  "--override-token", "merge: urgent [skip-qse]"])
    assert rc == 0


# ---------- fallback behaviour ----------

def test_delta_without_base_falls_back_to_any(tmp_path: Path, capsys):
    """mode=delta but no base flag: warn on stderr, fall back to mode='any'."""
    head = tmp_path / "repo"
    _init_base_repo(head)
    _add_cycle_commit(head)

    cfg = _write_cfg(tmp_path)
    # any-mode still flags cycles → FAIL
    rc = run_cli([str(head), "--config", str(cfg)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "falling back to mode='any'" in err


def test_delta_invalid_base_path_is_error(tmp_path: Path, capsys):
    """--base-path pointing nowhere should be a clean user-facing error."""
    head = tmp_path / "repo"
    _init_base_repo(head)
    cfg = _write_cfg(tmp_path)
    with pytest.raises(ValueError, match="--base-path not found"):
        run_cli([str(head), "--config", str(cfg),
                 "--base-path", str(tmp_path / "does-not-exist")])


def test_missing_config_returns_exit_2(tmp_path: Path):
    rc = run_cli([str(tmp_path), "--config", str(tmp_path / "nope.toml")])
    assert rc == 2


def test_missing_repo_returns_exit_2(tmp_path: Path):
    cfg = _write_cfg(tmp_path)
    rc = run_cli([str(tmp_path / "nope"), "--config", str(cfg)])
    assert rc == 2
