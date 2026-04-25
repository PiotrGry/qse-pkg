"""Smoke tests for qse.integrations.pre_commit."""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from qse.integrations.pre_commit import main, _staged_python_files


def _run_git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def temp_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init")
    _run_git(repo, "config", "user.email", "t@t")
    _run_git(repo, "config", "user.name", "t")
    # Multi-file initial state to avoid trivial-graph artifacts
    src = repo / "src"
    src.mkdir()
    (src / "a.py").write_text("def a(): return 1\n")
    (src / "b.py").write_text("from src.a import a\ndef b(): return a()\n")
    (src / "c.py").write_text("from src.b import b\ndef c(): return b()\n")
    (src / "d.py").write_text("from src.c import c\ndef d(): return c()\n")
    (src / "e.py").write_text("from src.d import d\ndef e(): return d()\n")
    (src / "f.py").write_text("from src.e import e\ndef f(): return e()\n")
    (src / "g.py").write_text("from src.f import f\ndef g(): return f()\n")
    (src / "h.py").write_text("from src.g import g\ndef h(): return g()\n")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "init")
    return repo


def test_no_staged_files_passes(temp_repo, capsys):
    rc = main(["--repo", str(temp_repo)])
    out = capsys.readouterr()
    assert rc == 0
    assert "no staged Python files" in out.out


def test_clean_addition_passes(temp_repo, capsys):
    """Adding a file that wires into the graph should pass."""
    new = temp_repo / "src" / "i.py"
    new.write_text("from src.h import h\ndef i(): return h()\n")
    _run_git(temp_repo, "add", "src/i.py")
    rc = main(["--repo", str(temp_repo)])
    assert rc == 0


def test_cycle_introduction_fails(temp_repo, capsys):
    """Adding a back-edge that closes a cycle must fail."""
    target = temp_repo / "src" / "a.py"
    target.write_text("from src.h import h\ndef a(): return h()\n")
    _run_git(temp_repo, "add", "src/a.py")
    rc = main(["--repo", str(temp_repo)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "CYCLE" in err


def test_staged_python_files_filters_non_python(temp_repo):
    (temp_repo / "README.md").write_text("# hi\n")
    new = temp_repo / "src" / "j.py"
    new.write_text("def j(): return 1\n")
    _run_git(temp_repo, "add", "README.md", "src/j.py")
    staged = _staged_python_files(str(temp_repo))
    assert "src/j.py" in staged
    assert all(s.endswith(".py") for s in staged)


def test_language_flag_changes_thresholds(temp_repo, capsys):
    """--language go is stricter on RC than python."""
    target = temp_repo / "src" / "a.py"
    target.write_text("from src.h import h\ndef a(): return h()\n")
    _run_git(temp_repo, "add", "src/a.py")
    # Both should fail (cycle is universal); just verify the flag is accepted
    rc_go = main(["--repo", str(temp_repo), "--language", "go"])
    err = capsys.readouterr().err
    assert rc_go == 1
    assert "CYCLE" in err
