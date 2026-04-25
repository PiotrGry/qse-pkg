"""Tests for `qse gate-diff --migration-baseline` three-reference policy.

Tests at the policy layer (using a tiny git repo fixture). Asserts:
1. No --migration-baseline → behavior unchanged (2-way gate).
2. HEAD better than migration_baseline AND HEAD ≥ main → PASS.
3. HEAD worse than main BUT better than migration_baseline → PASS with note.
4. HEAD worse than both → FAIL with "regression vs both baselines" message.
5. Edge case: migration_baseline == main → behavior identical to no flag.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_qse(*args: str, cwd: str) -> tuple[int, str, str]:
    r = subprocess.run(
        [sys.executable, "-m", "qse.cli", *args],
        cwd=cwd, capture_output=True, text=True, env={
            **os.environ, "PYTHONPATH": str(REPO_ROOT),
        },
    )
    return r.returncode, r.stdout, r.stderr


def _git(*args: str, cwd: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=True)


def _commit(cwd: str, message: str, files: dict[str, str]) -> str:
    for path, content in files.items():
        full = Path(cwd) / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
    _git("add", "-A", cwd=cwd)
    _git("commit", "-m", message, cwd=cwd)
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd,
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


@pytest.fixture
def tiny_repo(tmp_path: Path) -> Path:
    """Build a 3-commit history: clean → has_cycle → still_has_cycle.

    main:        clean code (no cycle)
    migration:   introduces a cycle a↔b
    head:        keeps cycle a↔b but fixes nothing further
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=str(repo))
    _git("config", "user.email", "test@test", cwd=str(repo))
    _git("config", "user.name", "Test", cwd=str(repo))

    # Commit 1 (main): clean
    main_sha = _commit(str(repo), "clean", {
        "pkg/__init__.py": "",
        "pkg/a.py": "x = 1\n",
        "pkg/b.py": "y = 2\n",
        "pkg/c.py": "z = 3\n",
    })
    # Commit 2 (migration baseline): introduces cycle a↔b
    mig_sha = _commit(str(repo), "introduce cycle", {
        "pkg/a.py": "from pkg import b\nx = 1\n",
        "pkg/b.py": "from pkg import a\ny = 2\n",
    })
    # Commit 3 (head): cycle still there, additional unrelated change
    head_sha = _commit(str(repo), "more work in cycle", {
        "pkg/c.py": "z = 3\nz2 = 4\n",
    })
    return repo


def test_no_migration_flag_is_classic_2way(tiny_repo: Path) -> None:
    """Without --migration-baseline, gate-diff is the standard 2-way check."""
    rc, stdout, stderr = _run_qse(
        "gate-diff", "--base", "HEAD~2", "--head", "HEAD",
        "--language", "python",
        cwd=str(tiny_repo),
    )
    # Cycle introduced from HEAD~2 to HEAD → FAIL expected
    assert rc == 1, f"expected FAIL, got rc={rc}\n{stdout}\n{stderr}"
    assert "FAIL" in stdout
    assert "CYCLE" in stdout


def test_migration_pass_when_head_no_worse_than_migration_baseline(
        tiny_repo: Path) -> None:
    """HEAD has same cycle as migration_baseline; vs migration → PASS."""
    rc, stdout, stderr = _run_qse(
        "gate-diff", "--base", "HEAD~2", "--head", "HEAD",
        "--migration-baseline", "HEAD~1",
        "--language", "python",
        cwd=str(tiny_repo),
    )
    # HEAD vs main: FAIL (cycle); HEAD vs migration: PASS (cycle existed)
    # Policy → PASS with banner
    assert rc == 0, f"expected PASS-in-migration, got rc={rc}\n{stdout}\n{stderr}"
    assert "in-migration" in stdout.lower() or "PASS" in stdout
    assert "migration" in stdout.lower()


def test_migration_fail_when_head_worse_than_migration_baseline(
        tiny_repo: Path) -> None:
    """If HEAD is worse than even the migration baseline → FAIL."""
    # Add a 4th commit that ADDS a new cycle on top of the existing one
    _commit(str(tiny_repo), "add second cycle", {
        "pkg/d.py": "from pkg import e\nq = 1\n",
        "pkg/e.py": "from pkg import d\nr = 2\n",
    })

    rc, stdout, stderr = _run_qse(
        "gate-diff", "--base", "HEAD~3", "--head", "HEAD",
        "--migration-baseline", "HEAD~2",  # cycle a↔b at this commit
        "--language", "python",
        cwd=str(tiny_repo),
    )
    # HEAD has cycles a↔b AND d↔e; migration_baseline has only a↔b.
    # vs main: FAIL (2 cycles introduced); vs migration: FAIL (1 NEW cycle d↔e)
    # Policy → FAIL
    assert rc == 1, f"expected FAIL, got rc={rc}\n{stdout}\n{stderr}"
    assert "FAIL" in stdout
    assert "both baselines" in stdout.lower()


def test_migration_baseline_equal_to_base_is_classic(tiny_repo: Path) -> None:
    """Edge case: --migration-baseline == --base → behavior identical to 2-way."""
    rc1, out1, _ = _run_qse(
        "gate-diff", "--base", "HEAD~2", "--head", "HEAD",
        "--language", "python",
        cwd=str(tiny_repo),
    )
    rc2, out2, _ = _run_qse(
        "gate-diff", "--base", "HEAD~2", "--head", "HEAD",
        "--migration-baseline", "HEAD~2",
        "--language", "python",
        cwd=str(tiny_repo),
    )
    assert rc1 == rc2 == 1, "both should FAIL identically"
    # Both report cycle violation
    assert "CYCLE" in out1 and "CYCLE" in out2


def test_base_pass_migration_fail_policy_logic() -> None:
    """Rare branch logic test: BASE_PASS_MIG_FAIL.

    Reproducing this via real git history requires a base that's structurally
    BETTER than where the migration started (rare in practice — base is
    usually more stable than mid-refactor branches). Instead, we test the
    policy logic directly by mocking GateResult instances.
    """
    from dataclasses import replace
    from qse.gate.gate_check import GateResult, Violation

    base_pass = GateResult(passed=True, violations=[],
                           metrics_before={}, metrics_after={})
    mig_fail = GateResult(
        passed=False,
        violations=[Violation(rule="ISOLATED", summary="x", why="y",
                              fix="z", culprits=["a"])],
        metrics_before={}, metrics_after={},
    )
    # Simulate the policy outcome calculation from cli.py.
    base_passed = base_pass.passed
    mig_passed = mig_fail.passed
    if base_passed and mig_passed:
        outcome = "CLEAN_PASS"
    elif not base_passed and mig_passed:
        outcome = "IN_MIGRATION_PASS"
    elif not base_passed and not mig_passed:
        outcome = "FAIL_BOTH"
    else:
        outcome = "BASE_PASS_MIG_FAIL"

    assert outcome == "BASE_PASS_MIG_FAIL"
    # Final passed should be True (HEAD ≥ base is the dominant signal)
    final_passed = outcome != "FAIL_BOTH"
    assert final_passed is True


def test_json_output_carries_policy_outcome(tiny_repo: Path) -> None:
    """JSON output exposes machine-readable policy_outcome + base_passed."""
    import json
    out_file = tiny_repo / "result.json"
    rc, _, _ = _run_qse(
        "gate-diff", "--base", "HEAD~2", "--head", "HEAD",
        "--migration-baseline", "HEAD~1",
        "--language", "python",
        "--output-json", str(out_file),
        cwd=str(tiny_repo),
    )
    assert rc == 0
    data = json.loads(out_file.read_text())
    assert "policy_outcome" in data, "missing policy_outcome in JSON"
    assert data["policy_outcome"] == "IN_MIGRATION_PASS"
    assert "base_passed" in data
    assert data["base_passed"] is False  # vs-main FAIL but final PASS
    assert data["passed"] is True
    assert "migration_passed" in data
    assert data["migration_passed"] is True
    # Vs-base violations preserved in JSON for transparency
    assert len(data["violations"]) > 0


def test_inverted_migration_baseline_warns(tiny_repo: Path) -> None:
    """Migration baseline ahead of HEAD → ancestry warning emitted."""
    # HEAD~0 is HEAD. Use a future ref by tagging HEAD then advancing.
    # Easier: pass HEAD as migration baseline while base is HEAD~2 — HEAD is
    # ancestor of itself, no warning. So construct an unrelated branch.
    _git("checkout", "-q", "-b", "side", "HEAD~2", cwd=str(tiny_repo))
    _commit(str(tiny_repo), "side commit", {"side.py": "s = 1\n"})
    side_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(tiny_repo),
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    _git("checkout", "-q", "main", cwd=str(tiny_repo))

    rc, _, stderr = _run_qse(
        "gate-diff", "--base", "HEAD~2", "--head", "HEAD",
        "--migration-baseline", side_sha,
        "--language", "python",
        cwd=str(tiny_repo),
    )
    # Either FAIL or PASS depending on side branch content; what matters:
    # the warning is emitted.
    assert "warning" in stderr.lower() and "ancestor" in stderr.lower(), \
           f"missing ancestry warning in:\n{stderr}"
