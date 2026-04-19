"""Sprint 0 gate CLI entry point.

Usage:
    qse-gate <repo_path> --config qse-gate.toml [options]
    python -m qse.gate <repo_path> --config qse-gate.toml [options]

Δ mode options (mutually exclusive; pick at most one):
    --base-ref <git-ref>   Materialize the base graph from a git ref
                           (e.g. main, origin/main, abc123).
    --base-path <path>     Use a pre-materialized directory as the base.
    --auto-base            Auto-detect merge-base with the default branch.

If mode="delta" is set in config but no base is resolvable, the gate warns
and falls back to mode="any".

Sprint 0 is Python-only (uses qse.scanner). Java/Go via qse-core in 0.5.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, Optional, Tuple

import networkx as nx

from qse.gate.config import GateConfig, load_config
from qse.gate.report import to_json, to_pr_comment, write_telemetry
from qse.gate.rules import GateResult, run_gate


def _build_graph_python(
    repo_path: str,
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> Tuple[nx.DiGraph, Dict[str, str]]:
    """Scan a Python repo via qse.scanner and return (graph, file_hints)."""
    from qse.scanner import scan_repo

    analysis = scan_repo(repo_path, include=include, exclude=exclude)
    file_hints: Dict[str, str] = {}
    for file_path in analysis.files:
        rel = Path(file_path).relative_to(repo_path) if Path(file_path).is_absolute() else Path(file_path)
        module = str(rel.with_suffix("")).replace("/", ".")
        file_hints[module] = str(rel)
    return analysis.graph, file_hints


def _build_graph(
    repo_path: str,
    language: str,
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> Tuple[nx.DiGraph, Dict[str, str]]:
    if language == "python":
        return _build_graph_python(repo_path, include=include, exclude=exclude)
    raise NotImplementedError(
        f"Sprint 0 supports only language='python'. Got {language!r}. "
        "Java/Go via qse-core deferred to Sprint 0.5."
    )


def _run_git(args: list[str], cwd: str | Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _repo_root(path: str | Path) -> Optional[Path]:
    """Find the git repo root containing `path`, or None if not a repo."""
    r = _run_git(["rev-parse", "--show-toplevel"], path)
    if r.returncode != 0:
        return None
    return Path(r.stdout.strip())


def _detect_default_branch(repo: str | Path) -> Optional[str]:
    """Find the remote default branch (origin/HEAD target)."""
    r = _run_git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], repo)
    if r.returncode == 0:
        # e.g. "origin/main"
        return r.stdout.strip().split("/", 1)[-1]
    # Fallbacks
    for cand in ("main", "master"):
        r = _run_git(["rev-parse", "--verify", f"origin/{cand}"], repo)
        if r.returncode == 0:
            return cand
    return None


def _merge_base(repo: str | Path, ref: str) -> Optional[str]:
    r = _run_git(["merge-base", "HEAD", ref], repo)
    if r.returncode == 0:
        return r.stdout.strip()
    return None


def _materialize_ref(repo: str | Path, ref: str, dest: Path) -> None:
    """Extract the tree at `ref` into `dest` via `git archive | tar -x`."""
    dest.mkdir(parents=True, exist_ok=True)
    git = subprocess.Popen(
        ["git", "archive", "--format=tar", ref],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    tar = subprocess.Popen(
        ["tar", "-x", "-C", str(dest)],
        stdin=git.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert git.stdout is not None
    git.stdout.close()
    tar_stdout, tar_stderr = tar.communicate()
    _, git_stderr = git.communicate()

    if git.returncode != 0:
        raise RuntimeError(
            f"git archive {ref!r} failed: {git_stderr.decode(errors='replace').strip()}"
        )
    if tar.returncode != 0:
        raise RuntimeError(
            f"tar extract failed: {tar_stderr.decode(errors='replace').strip()}"
        )


def _resolve_base(
    head_path: str,
    base_ref: Optional[str],
    base_path: Optional[str],
    auto_base: bool,
) -> Optional[Tuple[Path, Optional[Path]]]:
    """Resolve the base tree to scan.

    Returns (base_scan_dir, temp_dir_to_cleanup) or None if no base is configured.
    `temp_dir_to_cleanup` is None when `base_path` was supplied by the user
    (they own it); it is set when we materialized a git ref and the caller
    must remove it after scanning.

    For git-ref materialization, we extract the whole repo at `ref` to a tmp
    dir and point the scanner at the same relative subpath the user scanned
    in HEAD (so comparing `qse/gate/` at HEAD vs HEAD~1 works when gate/
    didn't exist at HEAD~1 — we warn and fall back to no base).
    """
    if base_path:
        p = Path(base_path)
        if not p.is_dir():
            raise ValueError(f"--base-path not found or not a directory: {base_path}")
        return p, None

    repo_root = _repo_root(head_path)
    if (base_ref or auto_base) and repo_root is None:
        print(f"warning: {head_path} is not inside a git repo; base flags ignored",
              file=sys.stderr)
        return None

    ref = base_ref
    if auto_base and not ref:
        default = _detect_default_branch(repo_root)
        if not default:
            print("warning: --auto-base could not detect default branch (no origin?); falling back",
                  file=sys.stderr)
            return None
        mb = _merge_base(repo_root, f"origin/{default}")
        if not mb:
            mb = _merge_base(repo_root, default)
        if not mb:
            print(f"warning: --auto-base could not find merge-base with {default}; falling back",
                  file=sys.stderr)
            return None
        ref = mb

    if not ref:
        return None

    tmp = Path(tempfile.mkdtemp(prefix="qse-gate-base-"))
    try:
        _materialize_ref(repo_root, ref, tmp)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    # Preserve the relative subpath the user scanned at HEAD.
    try:
        rel = Path(head_path).resolve().relative_to(repo_root.resolve())
    except ValueError:
        rel = Path(".")
    base_scan = tmp / rel
    if not base_scan.is_dir():
        print(f"warning: subpath {rel} did not exist at ref {ref}; skipping base graph",
              file=sys.stderr)
        shutil.rmtree(tmp, ignore_errors=True)
        return None
    return base_scan, tmp


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="qse-gate",
        description="AI-Drift Firewall: axiom-backed architecture gate for CI/CD.",
    )
    p.add_argument("path", help="Repository path to scan (head).")
    p.add_argument("--config", required=True, help="Path to qse-gate.toml config.")

    base_group = p.add_mutually_exclusive_group()
    base_group.add_argument("--base-ref", default=None,
                            help="Git ref for base graph (e.g. main, origin/main, abc123).")
    base_group.add_argument("--base-path", default=None,
                            help="Path to pre-materialized base tree.")
    base_group.add_argument("--auto-base", action="store_true",
                            help="Auto-detect merge-base with the default branch.")

    p.add_argument("--output-json", default=None, help="Write JSON report to file.")
    p.add_argument("--pr-comment", default=None, help="Write PR-comment markdown to file.")
    p.add_argument("--override-token", default=None,
                   help="PR title or commit message to check for [skip-qse].")
    p.add_argument("--repo", default=None, help="Repo slug for telemetry (owner/name).")
    p.add_argument("--pr", type=int, default=None, help="PR number for telemetry.")
    p.add_argument("--commit", default=None, help="Head commit SHA for telemetry.")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if not Path(args.config).is_file():
        print(f"error: config file not found: {args.config}", file=sys.stderr)
        return 2
    if not Path(args.path).is_dir():
        print(f"error: repo path not found or not a directory: {args.path}", file=sys.stderr)
        return 2

    config = load_config(args.config)

    base_graph: Optional[nx.DiGraph] = None
    cleanup_dir: Optional[Path] = None
    try:
        resolved = _resolve_base(
            head_path=args.path,
            base_ref=args.base_ref,
            base_path=args.base_path,
            auto_base=args.auto_base,
        )
        if resolved is None and config.cycle_new.mode == "delta":
            print("warning: cycle_new.mode='delta' but no base resolved; falling back to mode='any'",
                  file=sys.stderr)
            config.cycle_new.mode = "any"
        if resolved is not None:
            base_dir, cleanup_dir = resolved
            base_graph, _ = _build_graph(
                str(base_dir), config.language,
                include=config.scan.include, exclude=config.scan.exclude,
            )

        head_graph, file_hints = _build_graph(
            args.path, config.language,
            include=config.scan.include, exclude=config.scan.exclude,
        )

        result: GateResult = run_gate(
            head_graph=head_graph,
            config=config,
            base_graph=base_graph,
            file_hints=file_hints,
            override_token=args.override_token,
        )
    finally:
        if cleanup_dir is not None:
            shutil.rmtree(cleanup_dir, ignore_errors=True)

    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(to_json(result))

    if args.pr_comment:
        Path(args.pr_comment).parent.mkdir(parents=True, exist_ok=True)
        Path(args.pr_comment).write_text(to_pr_comment(result, repo=args.repo, pr=args.pr))

    if config.telemetry.jsonl_path:
        write_telemetry(
            result,
            jsonl_path=config.telemetry.jsonl_path,
            repo=args.repo,
            pr=args.pr,
            commit=args.commit,
        )

    if result.passed:
        if result.override:
            print(f"QSE GATE OVERRIDE  {len(result.violations)} violations (skipped via [skip-qse])")
        else:
            delta_on = result.meta.get("delta_mode")
            mode_note = "delta" if delta_on else "any"
            print(f"QSE GATE PASS  rules={','.join(result.rules_evaluated)}  "
                  f"nodes={result.meta['head_nodes']}  edges={result.meta['head_edges']}  "
                  f"cycle_mode={mode_note}")
        return 0

    print(f"QSE GATE FAIL  violations={len(result.violations)}")
    for v in result.violations[:10]:
        print(f"  [{v.rule}] {v.source} → {v.target}  ({v.detail})")
    if len(result.violations) > 10:
        print(f"  …and {len(result.violations) - 10} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
