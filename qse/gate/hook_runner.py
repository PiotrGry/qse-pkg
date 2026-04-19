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
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from qse.gate.config import load_config
from qse.gate.rules import RuleViolation, run_gate
from qse.gate.runner import _build_graph


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
    """Best-effort mapping: src/foo/bar.py → src.foo.bar (matches scanner)."""
    try:
        rel = file_path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else None


def _run_on_overlay(
    repo_root: Path, file_path: Path, proposed: str, language: str,
) -> Tuple[object, list[str]]:
    """Copy the repo to a temp dir, overwrite the one file with the proposed
    content, then build the graph + collect file hints. Returns (graph, hints)."""
    tmp = Path(tempfile.mkdtemp(prefix="qse-hook-"))
    try:
        # Copy shallowly — skip .git, node_modules, __pycache__, and the
        # qse-gate runtime artifacts.
        ignore = shutil.ignore_patterns(
            ".git", "node_modules", "__pycache__", "*.pyc",
            "artifacts", "_obsolete", ".pytest_cache",
        )
        shutil.copytree(repo_root, tmp / "repo", ignore=ignore, dirs_exist_ok=True)
        target = tmp / "repo" / file_path.resolve().relative_to(repo_root.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(proposed)
        graph, hints = _build_graph(str(tmp / "repo"), language)
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
    payload = _load_payload()
    tool_name = payload.get("tool_name", "")
    if tool_name not in {"Write", "Edit"}:
        return 0  # not our concern

    tool_input = payload.get("tool_input", {}) or {}
    cwd = Path(payload.get("cwd", ".")).resolve()
    file_path_raw = tool_input.get("file_path", "")
    if not file_path_raw:
        return 0
    file_path = Path(file_path_raw)
    if not file_path.is_absolute():
        file_path = (cwd / file_path).resolve()

    # Only gate files inside the project. Skip dotfiles and generated output.
    try:
        file_path.relative_to(cwd)
    except ValueError:
        return 0

    # Locate config. Convention: qse-gate.toml at the repo root.
    config_path = cwd / "qse-gate.toml"
    if not config_path.is_file():
        return 0  # no config = hook is opt-in and silent

    # Only gate files in the language the config is configured for. For MVP we
    # only handle Python; other languages will need scanner-side support first.
    config = load_config(str(config_path))
    if config.language != "python":
        return 0
    if file_path.suffix != ".py":
        return 0

    proposed = _materialize_proposed(cwd, file_path, tool_name, tool_input)
    if proposed is None:
        return 0

    try:
        graph, hints, tmp = _run_on_overlay(cwd, file_path, proposed, config.language)
    except Exception as e:
        print(f"qse-hook: overlay build failed: {e}", file=sys.stderr)
        return 0  # fail-open

    try:
        result = run_gate(head_graph=graph, config=config, file_hints=hints)
        if result.passed:
            return 0
        module = _proposed_module_name(cwd, file_path)
        # Keep violations that touch the file being edited. If none match, we
        # still block but with a generic message — better to be loud than
        # silently let a drift through.
        touching = [
            v for v in result.violations
            if module is None
            or module in (v.source, v.target)
            or module in (v.scc_members or [])
        ]
        if not touching:
            return 0  # violation exists but isn't caused by this edit
        print(_format_block_reason(touching, module), file=sys.stderr)
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
