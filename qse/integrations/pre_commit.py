"""Pre-commit hook entry point.

Runs `gate_check(G_HEAD, G_HEAD+staged_overlay)` and exits 0/1.

Designed to be invoked by the standard `pre-commit` framework via the
`.pre-commit-hooks.yaml` declaration. Works with any AI coding tool —
the hook does not care who or what made the staged changes.
"""

from __future__ import annotations

import argparse
import ast
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import networkx as nx

from qse.gate.gate_check import gate_check


def _git(*args: str, cwd: str = ".") -> str:
    r = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def _staged_python_files(repo: str) -> list[str]:
    """Files staged for commit (Added/Copied/Modified), Python only."""
    out = _git("diff", "--cached", "--name-only", "--diff-filter=ACM", cwd=repo)
    return [f for f in out.splitlines() if f.endswith(".py")]


def _scan_python_dir(root: str) -> nx.DiGraph:
    """Build a dependency DiGraph from a directory of Python files."""
    rootp = Path(root)
    py_files = [
        p for p in rootp.rglob("*.py")
        if p.name != "__init__.py" and "__pycache__" not in str(p)
    ]
    nodes: dict[str, Path] = {}
    for p in py_files:
        rel = p.relative_to(rootp).with_suffix("")
        mod = ".".join(rel.parts)
        nodes[mod] = p

    G = nx.DiGraph()
    for mod, path in nodes.items():
        G.add_node(mod, file=str(path))

    for mod, path in nodes.items():
        try:
            src = path.read_text(errors="replace")
        except OSError:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        pkg = ".".join(mod.split(".")[:-1])
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.level == 0:
                    dep = node.module
                else:
                    base_parts = pkg.split(".") if pkg else []
                    keep = max(0, len(base_parts) - node.level + 1)
                    base = ".".join(base_parts[:keep])
                    dep = f"{base}.{node.module}".lstrip(".")
                if dep in nodes:
                    G.add_edge(mod, dep)
                for a in node.names:
                    full = f"{dep}.{a.name}"
                    if full in nodes:
                        G.add_edge(mod, full)
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.name in nodes:
                        G.add_edge(mod, a.name)
    return G


def _materialize_after_state(repo: str, staged: list[str]) -> str:
    """Create a temp dir mirroring HEAD state, then overlay staged changes.

    Returns path to the temp dir. Caller must shutil.rmtree() it when done.
    """
    tmp = tempfile.mkdtemp(prefix="qse-precommit-")
    try:
        # Export HEAD into tmp (without .git, preserving symlinks).
        result = subprocess.run(
            ["git", "archive", "HEAD", "--format=tar"],
            cwd=repo, capture_output=True, check=True,
        )
        import io
        import tarfile
        with tarfile.open(fileobj=io.BytesIO(result.stdout)) as tar:
            tar.extractall(tmp)

        # Overlay staged content for each staged Python file.
        for relpath in staged:
            target = Path(tmp) / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                content = subprocess.run(
                    ["git", "show", f":{relpath}"],
                    cwd=repo, capture_output=True, check=True,
                ).stdout
                target.write_bytes(content)
            except subprocess.CalledProcessError:
                # File deleted in stage — remove from tmp if present.
                if target.exists():
                    target.unlink()
        return tmp
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="qse-pre-commit",
        description="QSE architectural gate — pre-commit hook entry point.",
    )
    parser.add_argument("--language", default="python",
                        choices=["python", "java", "go"],
                        help="Threshold preset (default: python).")
    parser.add_argument("--repo", default=".", help="Repository root (default: cwd).")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress informational output.")
    parser.add_argument("filenames", nargs="*",
                        help="Files passed by pre-commit (informational; "
                             "actual scope determined via git index).")
    args = parser.parse_args(argv)

    repo = os.path.abspath(args.repo)

    # 1. Detect staged Python files via git index. If none, skip.
    try:
        staged = _staged_python_files(repo)
    except RuntimeError as e:
        print(f"qse pre-commit: {e}", file=sys.stderr)
        return 0  # fail-open on infrastructure errors

    if not staged:
        if not args.quiet:
            print("qse pre-commit: no staged Python files; skipping.")
        return 0

    # 2. Build G_before from HEAD.
    tmp_before: Optional[str] = None
    tmp_after: Optional[str] = None
    try:
        try:
            tmp_before = tempfile.mkdtemp(prefix="qse-precommit-before-")
            result = subprocess.run(
                ["git", "archive", "HEAD", "--format=tar"],
                cwd=repo, capture_output=True, check=True,
            )
            import io
            import tarfile
            with tarfile.open(fileobj=io.BytesIO(result.stdout)) as tar:
                tar.extractall(tmp_before)
        except subprocess.CalledProcessError:
            # No HEAD yet (initial commit) — empty graph.
            G_before = nx.DiGraph()
        else:
            G_before = _scan_python_dir(tmp_before)

        # 3. Build G_after = HEAD + staged overlay.
        tmp_after = _materialize_after_state(repo, staged)
        G_after = _scan_python_dir(tmp_after)

        # 4. Run gate_check.
        result = gate_check(G_before, G_after, language=args.language)
    except Exception as e:
        print(f"qse pre-commit: error during scan ({e}); skipping.", file=sys.stderr)
        return 0  # fail-open on scan errors
    finally:
        if tmp_before:
            shutil.rmtree(tmp_before, ignore_errors=True)
        if tmp_after:
            shutil.rmtree(tmp_after, ignore_errors=True)

    if result.passed:
        if not args.quiet:
            print(f"qse pre-commit: PASS ({len(staged)} Python file(s) staged).")
        return 0

    print("qse pre-commit: FAIL — architectural regression detected:", file=sys.stderr)
    for v in result.violations:
        print(f"  {v}", file=sys.stderr)
    print("\nFix the regression, re-stage, and retry. To bypass (not recommended):", file=sys.stderr)
    print("  git commit --no-verify", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
