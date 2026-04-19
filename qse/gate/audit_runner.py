"""CLI entry point for `qse-audit`.

Usage:
    qse-audit <path> --config qse-gate.toml [--output-md report.md] [--output-json report.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Optional

import shutil

from qse.gate.audit import audit_from_gate_result, to_markdown
from qse.gate.config import load_config
from qse.gate.rules import run_gate
from qse.gate.runner import _build_graph, _resolve_base


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="qse-audit",
        description="Architecture audit report — priority-ranked risks + recommendations. "
                    "Analysis-only; always exits 0 (not a blocker).",
    )
    p.add_argument("path", help="Repository path to audit.")
    p.add_argument("--config", required=True, help="Path to qse-gate.toml config.")
    p.add_argument("--output-md", default=None,
                   help="Write markdown report to this file (default: stdout).")
    p.add_argument("--output-json", default=None,
                   help="Write structured JSON report to this file.")
    p.add_argument("--top", type=int, default=10,
                   help="Number of top risks to include in the report (default: 10).")
    p.add_argument("--repo-label", default=None,
                   help="Override the repo label shown in the report (defaults to <path>).")
    base_group = p.add_mutually_exclusive_group()
    base_group.add_argument("--base-ref", default=None,
                            help="Git ref for base graph (Δ mode). Enables NEW/EXISTING/RESOLVED classification.")
    base_group.add_argument("--base-path", default=None,
                            help="Pre-materialized directory as the base (Δ mode).")
    base_group.add_argument("--auto-base", action="store_true",
                            help="Auto-detect merge-base with the default branch.")
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
    head_graph, file_hints = _build_graph(
        args.path, config.language,
        include=config.scan.include, exclude=config.scan.exclude,
    )
    head_result = run_gate(head_graph=head_graph, config=config, file_hints=file_hints)

    base_graph = None
    base_result = None
    cleanup_dir = None
    try:
        resolved = _resolve_base(
            head_path=args.path,
            base_ref=args.base_ref,
            base_path=args.base_path,
            auto_base=args.auto_base,
        )
        if resolved is not None:
            base_dir, cleanup_dir = resolved
            base_graph, base_hints = _build_graph(
                str(base_dir), config.language,
                include=config.scan.include, exclude=config.scan.exclude,
            )
            base_result = run_gate(
                head_graph=base_graph, config=config, file_hints=base_hints,
            )

        report = audit_from_gate_result(
            repo=args.repo_label or args.path,
            result=head_result,
            head_graph=head_graph,
            top_n=args.top,
            base_graph=base_graph,
            base_result=base_result,
        )
    finally:
        if cleanup_dir is not None:
            shutil.rmtree(cleanup_dir, ignore_errors=True)

    md = to_markdown(report)
    if args.output_md:
        Path(args.output_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_md).write_text(md)
    else:
        print(md)

    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(json.dumps(report.to_dict(), indent=2))

    # Short summary line to stderr so CI logs have something scannable.
    p1 = sum(1 for r in report.top_risks if r.priority == "P1")
    print(
        f"qse-audit: health={report.health_score:.0f}/100 ({report.health_band})  "
        f"violations={report.total_violations}  P1={p1}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
