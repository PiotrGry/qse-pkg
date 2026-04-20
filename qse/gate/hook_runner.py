"""Agent-time hook runner — consumes Claude Code's PreToolUse JSON on stdin,
materializes the *proposed* repo state (current tree + the pending Edit/Write),
runs the gate, and blocks the write if it introduces a violation touching the
file being edited.

Design notes:
    - Exit 0  → allow the write.
    - Exit 2  → block the write; stderr is shown to Claude so it can self-correct.
    - Any other exit  → Claude proceeds anyway (fail-open). We log to stderr so
      users can see what went wrong.

Latency budget: keep end-to-end under ~1 s for small repos (demo target). For
bigger trees we rebuild the whole graph in a temp overlay; caching is a
follow-up once the loop is proven.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from qse.gate.config import load_config
from qse.gate.rules import RuleViolation, run_gate
from qse.gate.runner import _build_graph


def _git_repo_root(start: Path) -> Optional[Path]:
    """Canonical git toplevel for `start`, or None if not a git repo."""
    try:
        r = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        if r.returncode == 0:
            return Path(r.stdout.strip()).resolve()
    except Exception:
        return None
    return None


def _find_project_root(start: Path) -> Optional[Path]:
    """Nearest ancestor of `start` that contains qse-gate.toml.

    Prefer the config anchor over git toplevel: a monorepo can have one
    git root with multiple independent gate-configured projects inside
    it (e.g. examples/sample-ai-drift-demo lives inside qse-pkg's git
    tree but is its own gated project).
    """
    cur = start.resolve() if start.exists() else start
    git_top = _git_repo_root(cur)
    # Stop at git_top (inclusive), not at its parent — previously used
    # git_top.parent which allowed walking one level above the repo root,
    # enabling a rogue /home/user/qse-gate.toml to hijack the gate for
    # any repo under /home/user/. (Codex round 4, 2026-04-20.)
    stop_at = git_top if git_top else Path(cur.anchor)
    while True:
        if (cur / "qse-gate.toml").is_file():
            return cur
        if cur == stop_at or cur.parent == cur:
            break
        cur = cur.parent
    return git_top


def _load_payload() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"qse-hook: invalid JSON on stdin: {e}", file=sys.stderr)
        sys.exit(0)  # fail-open


def _materialize_proposed(
    cwd: Path, file_path: Path, tool_name: str, tool_input: dict,
) -> Optional[str]:
    """Return the proposed file content, or None if we cannot reconstruct it."""
    if tool_name == "Write":
        return tool_input.get("content")
    if tool_name == "Edit":
        old = tool_input.get("old_string", "")
        new = tool_input.get("new_string", "")
        replace_all = bool(tool_input.get("replace_all", False))
        if file_path.is_file():
            current = file_path.read_text()
        else:
            current = ""
        if old == "" and not current:
            return new
        if replace_all:
            return current.replace(old, new)
        # Single replacement — Edit's contract requires old_string to be unique.
        return current.replace(old, new, 1)
    return None


def _proposed_module_name(repo_root: Path, file_path: Path) -> Optional[str]:
    """Best-effort mapping: src/foo/bar.py → src.foo.bar (matches scanner).

    __init__.py is kept as `pkg.__init__` — consistent with scanner's
    _module_path output so the hook touching-filter can match it.
    Previously we stripped __init__, which caused the hook to search for
    `pkg` while the graph had `pkg.__init__`. (Codex round 4, 2026-04-20.)
    """
    try:
        rel = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    parts = list(rel.with_suffix("").parts)
    return ".".join(parts) if parts else None


def _run_on_overlay(
    repo_root: Path,
    file_path: Path,
    proposed: str,
    language: str,
    include: list[str],
    exclude: list[str],
) -> Tuple[object, dict, Path]:
    """Copy the repo to a temp dir, overwrite the one file with the proposed
    content, then build the graph. Copy is symlink-preserving (not followed)
    so we cannot be tricked into pulling arbitrary external trees."""
    tmp = Path(tempfile.mkdtemp(prefix="qse-hook-"))
    try:
        ignore = shutil.ignore_patterns(
            ".git", "node_modules", "__pycache__", "*.pyc",
            "artifacts", "_obsolete", ".pytest_cache",
            "target", "build", "dist", "*.egg-info",
        )
        shutil.copytree(
            repo_root, tmp / "repo",
            ignore=ignore, dirs_exist_ok=True, symlinks=True,
        )
        target = tmp / "repo" / file_path.resolve().relative_to(repo_root.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(proposed)
        graph, hints = _build_graph(
            str(tmp / "repo"), language, include=include, exclude=exclude,
        )
        return graph, hints, tmp
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def _format_block_reason(
    violations: list[RuleViolation], module: Optional[str],
) -> str:
    lines = ["qse-gate: blocked — this change would introduce a structural violation.\n"]
    shown = 0
    for v in violations:
        touches = (
            module is None
            or module in (v.source, v.target)
            or module in (v.scc_members or [])
        )
        if not touches:
            continue
        lines.append(f"  [{v.rule}] {v.source} → {v.target}")
        lines.append(f"    axiom: {v.axiom}")
        lines.append(f"    fix:   {v.fix_hint}")
        shown += 1
        if shown >= 3:
            break
    if shown == 0:
        # Fall back: show the first violation even if it does not reference the
        # module directly — happens when the scanner's module name doesn't
        # match our best-effort mapping.
        v = violations[0]
        lines.append(f"  [{v.rule}] {v.source} → {v.target}")
        lines.append(f"    axiom: {v.axiom}")
        lines.append(f"    fix:   {v.fix_hint}")
    return "\n".join(lines)


def main() -> int:
    try:
        payload = _load_payload()
        tool_name = payload.get("tool_name", "")
        if tool_name not in {"Write", "Edit"}:
            return 0

        tool_input = payload.get("tool_input", {}) or {}
        payload_cwd = Path(payload.get("cwd", ".")).resolve()
        file_path_raw = tool_input.get("file_path", "")
        if not file_path_raw:
            return 0

        file_path = Path(file_path_raw)
        if not file_path.is_absolute():
            file_path = (payload_cwd / file_path).resolve()

        # Anchor on the nearest ancestor that owns a qse-gate.toml — not on
        # payload.cwd (attacker-controlled) and not blindly on git toplevel
        # (breaks monorepos / nested demo projects).
        repo_root = _find_project_root(payload_cwd) or payload_cwd

        # Skip files that escape the repo (symlinks pointing outside, paths
        # passed with '..', etc.).
        try:
            file_path.relative_to(repo_root)
        except ValueError:
            return 0

        config_path = repo_root / "qse-gate.toml"
        if not config_path.is_file():
            return 0  # opt-in, silent when no config

        try:
            config = load_config(str(config_path))
        except Exception as e:
            print(f"qse-hook: config load failed ({e}); skipping.", file=sys.stderr)
            return 0  # broken config shouldn't block the entire editor

        if config.language != "python":
            return 0
        if file_path.suffix != ".py":
            return 0

        try:
            proposed = _materialize_proposed(
                repo_root, file_path, tool_name, tool_input,
            )
        except (UnicodeDecodeError, PermissionError, OSError) as e:
            print(f"qse-hook: cannot read target ({e}); skipping.", file=sys.stderr)
            return 0
        if proposed is None:
            return 0

        tmp: Optional[Path] = None
        try:
            graph, hints, tmp = _run_on_overlay(
                repo_root, file_path, proposed, config.language,
                include=config.scan.include, exclude=config.scan.exclude,
            )
        except Exception as e:
            print(f"qse-hook: overlay build failed ({e}); skipping.", file=sys.stderr)
            return 0  # fail-open on infrastructure errors, not policy errors

        try:
            result = run_gate(head_graph=graph, config=config, file_hints=hints)
            if result.passed:
                return 0
            module = _proposed_module_name(repo_root, file_path)
            touching = [
                v for v in result.violations
                if module is None
                or module in (v.source, v.target)
                or module in (v.scc_members or [])
            ]
            if not touching:
                return 0
            print(_format_block_reason(touching, module), file=sys.stderr)
            return 2
        finally:
            if tmp is not None:
                shutil.rmtree(tmp, ignore_errors=True)
    except Exception as e:
        # Unknown top-level error — log loudly but fail-open so the hook
        # cannot turn into a deadlock that traps the user's editor.
        print(f"qse-hook: unexpected error ({e.__class__.__name__}: {e})",
              file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
