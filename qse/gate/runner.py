"""Sprint 0 gate CLI entry point.

Usage:
    python -m qse.gate <repo_path> --config qse-gate.toml [options]
    qse-gate <repo_path> --config qse-gate.toml [options]

Sprint 0 is Python-only (uses qse.scanner). Java/Go via qse-core deferred
to Sprint 0.5. Base-graph materialization for CYCLE_NEW delta mode also
deferred — Sprint 0 defaults mode=any (flags all cycles).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, Optional

import networkx as nx

from qse.gate.config import GateConfig, load_config
from qse.gate.report import to_json, to_pr_comment, write_telemetry
from qse.gate.rules import GateResult, run_gate


def _build_graph_python(repo_path: str) -> tuple[nx.DiGraph, Dict[str, str]]:
    """Scan a Python repo via qse.scanner and return (graph, file_hints)."""
    from qse.scanner import scan_repo

    analysis = scan_repo(repo_path)
    file_hints: Dict[str, str] = {}
    # If scanner exposes file paths per module, map them. Fallback: none.
    for file_path in analysis.files:
        # best-effort: derive module name from relative path
        rel = Path(file_path).relative_to(repo_path) if Path(file_path).is_absolute() else Path(file_path)
        module = str(rel.with_suffix("")).replace("/", ".")
        file_hints[module] = str(rel)
    return analysis.graph, file_hints


def _build_graph(repo_path: str, language: str) -> tuple[nx.DiGraph, Dict[str, str]]:
    if language == "python":
        return _build_graph_python(repo_path)
    raise NotImplementedError(
        f"Sprint 0 supports only language='python'. Got {language!r}. "
        "Java/Go via qse-core deferred to Sprint 0.5."
    )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="qse-gate",
        description="AI-Drift Firewall: axiom-backed architecture gate for CI/CD.",
    )
    p.add_argument("path", help="Repository path to scan (head).")
    p.add_argument("--config", required=True, help="Path to qse-gate.toml config.")
    p.add_argument("--base", default=None, help="Optional base repo path for Δ mode (CYCLE_NEW delta).")
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
    head_graph, file_hints = _build_graph(args.path, config.language)

    base_graph: Optional[nx.DiGraph] = None
    if args.base:
        if not Path(args.base).is_dir():
            print(f"error: base path not found or not a directory: {args.base}", file=sys.stderr)
            return 2
        base_graph, _ = _build_graph(args.base, config.language)
    elif config.cycle_new.mode == "delta":
        print("warning: cycle_new.mode='delta' but no --base provided; falling back to mode='any'",
              file=sys.stderr)
        config.cycle_new.mode = "any"

    result: GateResult = run_gate(
        head_graph=head_graph,
        config=config,
        base_graph=base_graph,
        file_hints=file_hints,
        override_token=args.override_token,
    )

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

    # Console summary (short)
    if result.passed:
        if result.override:
            print(f"QSE GATE OVERRIDE  {len(result.violations)} violations (skipped via [skip-qse])")
        else:
            print(f"QSE GATE PASS  rules={','.join(result.rules_evaluated)}  "
                  f"nodes={result.meta['head_nodes']}  edges={result.meta['head_edges']}")
        return 0

    print(f"QSE GATE FAIL  violations={len(result.violations)}")
    for v in result.violations[:10]:
        print(f"  [{v.rule}] {v.source} → {v.target}  ({v.detail})")
    if len(result.violations) > 10:
        print(f"  …and {len(result.violations) - 10} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
