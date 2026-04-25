"""Tests for qse hotspot — hybrid behavioral × structural metric."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import networkx as nx
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


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


def test_path_to_module() -> None:
    from qse.hotspot import _path_to_module
    assert _path_to_module("pkg/sub/mod.py") == "pkg.sub.mod"
    assert _path_to_module("pkg/__init__.py") == "pkg"
    assert _path_to_module("top.py") == "top"


def test_compute_hotspot_score_synthetic() -> None:
    """Score = freq_norm × centrality_norm. Verify max-score = max-freq AND
    max-centrality."""
    from qse.hotspot import compute_hotspot_score

    G = nx.DiGraph()
    # core depended-on by 5 things → high in-degree → high centrality on reverse
    for i in range(5):
        G.add_node(f"caller_{i}", file=f"caller_{i}.py")
        G.add_edge(f"caller_{i}", "core")
    G.add_node("core", file="core.py")
    G.add_node("orphan", file="orphan.py")  # isolated, low centrality

    freq = {
        "core.py": 100,         # high churn + high centrality → top
        "orphan.py": 100,       # high churn but low centrality → low score
        "caller_0.py": 10,      # low churn even though some centrality
    }
    entries = compute_hotspot_score(G, freq)
    assert entries[0].module == "core", \
        f"core should rank first, got {entries[0].module}"
    # orphan has same freq but near-zero centrality
    orphan_score = next(e.score for e in entries if e.module == "orphan")
    core_score = next(e.score for e in entries if e.module == "core")
    assert core_score > orphan_score


def test_compute_change_frequency_filters_skip_paths(tmp_path: Path) -> None:
    """SKIP_PARTS paths should be excluded from frequency counts."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=str(repo))
    _git("config", "user.email", "test@test", cwd=str(repo))
    _git("config", "user.name", "Test", cwd=str(repo))
    _commit(str(repo), "init", {
        "src/real.py": "x = 1\n",
        "artifacts/dump.py": "y = 2\n",
        "_vendor/lib.py": "z = 3\n",
    })

    from qse.hotspot import compute_change_frequency
    freq = compute_change_frequency(str(repo), since="20 years ago")
    assert "src/real.py" in freq
    assert "artifacts/dump.py" not in freq
    assert "_vendor/lib.py" not in freq


def test_find_hotspots_e2e_self() -> None:
    """End-to-end on qse-pkg itself — should not crash, returns ≤N."""
    from qse.hotspot import find_hotspots
    entries = find_hotspots(str(REPO_ROOT), since="3 months ago", top=5)
    assert len(entries) <= 5
    # Score is always in [0, 1]
    for e in entries:
        assert 0.0 <= e.score <= 1.0
        assert e.frequency >= 1
        assert 0.0 <= e.centrality <= 1.0


def test_hotspot_cli_smoke() -> None:
    """`qse hotspot --top 3 --json` runs and emits valid JSON."""
    import json
    r = subprocess.run(
        [sys.executable, "-m", "qse.cli", "hotspot", str(REPO_ROOT),
         "--top", "3", "--json", "--since", "3 months ago"],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert isinstance(data, list)
    assert len(data) <= 3
    if data:
        for entry in data:
            assert "module" in entry and "score" in entry
            assert "frequency" in entry and "centrality" in entry
