"""
Unit tests for _churn_proxy() in agq_oss_thesis_benchmark.py.

Uses tmp git repos created in-process - no network, no /tmp/agq_bench80.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_repo(tmp_path: Path, commits: list) -> Path:
    """Create a minimal git repo with given commits.

    commits: list of (message, {filename: content}) dicts
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@t.com"],
                   capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "T"], capture_output=True)

    for msg, files in commits:
        for fname, content in files.items():
            fpath = repo / fname
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content)
            subprocess.run(["git", "-C", str(repo), "add", fname], capture_output=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", msg],
                       capture_output=True)
    return repo


# Import the function under test
from scripts.agq_oss_thesis_benchmark import _churn_proxy


class TestChurnProxy:
    def test_empty_repo_returns_none_fields(self, tmp_path):
        """Repo with no Python commits → all None."""
        repo = _make_repo(tmp_path, [
            ("init", {"README.md": "hello"}),
        ])
        result = _churn_proxy(repo, since="10 years ago")
        assert result["hotspot_ratio"] is None
        assert result["churn_gini"] is None
        assert result["n_files"] == 0

    def test_single_file_single_commit(self, tmp_path):
        """One .py file touched once → hotspot_ratio=0, gini=0."""
        repo = _make_repo(tmp_path, [
            ("add module", {"module.py": "x = 1"}),
        ])
        result = _churn_proxy(repo, since="10 years ago")
        assert result["n_files"] == 1
        assert result["hotspot_ratio"] == 0.0   # no file exceeds 2x mean
        assert result["churn_gini"] == pytest.approx(0.0)

    def test_hotspot_detected(self, tmp_path):
        """One file touched many times, others once → hotspot detected."""
        commits = [("init", {"hot.py": "x=1", "cold1.py": "a=1", "cold2.py": "b=1"})]
        for i in range(9):
            commits.append((f"fix {i}", {"hot.py": f"x={i}"}))
        repo = _make_repo(tmp_path, commits)
        result = _churn_proxy(repo, since="10 years ago")
        # hot.py: 10 commits, cold1/cold2: 1 each → mean=4, hotspot threshold=8
        assert result["hotspot_ratio"] > 0.0, "hot.py should be a hotspot"
        assert result["n_files"] == 3

    def test_test_files_excluded(self, tmp_path):
        """Files in tests/ directory are excluded from churn count."""
        repo = _make_repo(tmp_path, [
            ("add", {"src/module.py": "x=1", "tests/test_module.py": "def test_x(): pass"}),
            ("fix", {"tests/test_module.py": "def test_x(): assert True"}),
        ])
        result = _churn_proxy(repo, since="10 years ago")
        assert result["n_files"] == 1   # only src/module.py, test file excluded

    def test_gini_uniform_is_zero(self, tmp_path):
        """All files touched same number of times → Gini=0."""
        commits = [("init", {"a.py": "1", "b.py": "2", "c.py": "3"})]
        for i in range(3):
            commits.append((f"c{i}", {"a.py": str(i), "b.py": str(i), "c.py": str(i)}))
        repo = _make_repo(tmp_path, commits)
        result = _churn_proxy(repo, since="10 years ago")
        assert result["churn_gini"] == pytest.approx(0.0, abs=0.01)

    def test_gini_unequal_is_positive(self, tmp_path):
        """Unequal churn distribution → Gini > 0."""
        commits = [("init", {"a.py": "1", "b.py": "2"})]
        for i in range(8):
            commits.append((f"fix a {i}", {"a.py": str(i)}))
        repo = _make_repo(tmp_path, commits)
        result = _churn_proxy(repo, since="10 years ago")
        assert result["churn_gini"] > 0.0

    def test_since_window_respected(self, tmp_path):
        """Commits outside the time window are ignored."""
        repo = _make_repo(tmp_path, [
            ("old commit", {"module.py": "x=1"}),
        ])
        # Future date - no existing commits can match
        result = _churn_proxy(repo, since="2099-01-01")
        assert result["n_files"] == 0
        assert result["hotspot_ratio"] is None
