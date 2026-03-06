"""QSE command-line interface."""

import argparse
import json
import sys

import numpy as np

from qse.presets.ddd.config import QSEConfig
from qse.presets.ddd.pipeline import analyze_repo
from qse.presets.ddd.report import format_json, format_table
from qse.trl4_gate import TRL4Rules, run_trl4_gate

DEFECT_TYPES = ["anemic_entity", "fat_service", "zombie_entity", "layer_violation"]


def _build_config(args) -> QSEConfig:
    config = QSEConfig.from_file(args.config) if args.config else QSEConfig()
    if args.no_trace:
        config.enable_trace = False
    if hasattr(args, "weights") and args.weights:
        vals = [float(x) for x in args.weights.split(",")]
        if len(vals) != 5:
            print("Error: --weights requires exactly 5 values", file=sys.stderr)
            sys.exit(1)
        config.weights = np.array(vals)
    return config


def main():
    parser = argparse.ArgumentParser(
        prog="qse",
        description="QSE — Quality Score Engine for DDD architecture validation",
    )
    sub = parser.add_subparsers(dest="command")

    # ── qse scan ──────────────────────────────────────────────────────────────
    scan = sub.add_parser("scan", help="Analyze a repository and print report")
    scan.add_argument("path", help="Path to the repository root")
    scan.add_argument("--format", choices=["table", "json"], default="table")
    scan.add_argument("--output-json", type=str, default=None, metavar="FILE")
    scan.add_argument("--no-trace", action="store_true")
    scan.add_argument("--weights", type=str, default=None)
    scan.add_argument("--config", type=str, default=None)

    # ── qse gate ──────────────────────────────────────────────────────────────
    gate = sub.add_parser("gate", help="Run QSE and exit non-zero if gate fails")
    gate.add_argument("path", help="Path to the repository root")
    gate.add_argument("--threshold", type=float, default=0.80, metavar="N",
                      help="Minimum QSE4 score (default: 0.80)")
    gate.add_argument("--fail-on-defects", type=str, default=None, metavar="LIST",
                      help=f"Comma-separated defect types that must be zero. "
                           f"Available: {', '.join(DEFECT_TYPES)}")
    gate.add_argument("--output-json", type=str, default=None, metavar="FILE")
    gate.add_argument("--no-trace", action="store_true")
    gate.add_argument("--config", type=str, default=None)

    # ── qse trl4 ──────────────────────────────────────────────────────────────
    trl4 = sub.add_parser("trl4", help="Run TRL4 gate (QSE + constraints + ratchet)")
    trl4.add_argument("path", help="Path to the repository root")
    trl4.add_argument("--config", type=str, default=None, help="JSON config path")
    trl4.add_argument("--output-json", type=str, default=None, metavar="FILE")
    trl4.add_argument("--threshold", type=float, default=None,
                      help="Override QSE threshold from config/default")
    trl4.add_argument("--min-constraint-score", type=float, default=None,
                      help="Override minimum constraints score from config/default")
    trl4.add_argument("--ratchet", action="store_true", help="Force enable ratchet")
    trl4.add_argument("--no-ratchet", action="store_true", help="Force disable ratchet")
    trl4.add_argument("--baseline-file", type=str, default=None,
                      help="Ratchet baseline JSON file path")
    trl4.add_argument("--no-trace", action="store_true")

    args = parser.parse_args()

    if args.command not in ("scan", "gate", "trl4"):
        parser.print_help()
        sys.exit(1)

    config = _build_config(args)
    if args.command == "trl4":
        rules = TRL4Rules.from_file(args.config) if args.config else TRL4Rules()
        if args.threshold is not None:
            rules.threshold = args.threshold
        if args.min_constraint_score is not None:
            rules.min_constraint_score = args.min_constraint_score
        if args.ratchet:
            rules.ratchet_enabled = True
        if args.no_ratchet:
            rules.ratchet_enabled = False
        if args.baseline_file:
            rules.ratchet_baseline_file = args.baseline_file

        result = run_trl4_gate(args.path, rules=rules, qse_config=config)
        payload = result.to_dict()

        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump(payload, f, indent=2)

        if result.passed:
            print(f"TRL4 GATE PASS  qse4={result.qse4:.4f}  constraint_score={result.constraint_score:.4f}")
            sys.exit(0)

        print("TRL4 GATE FAIL", file=sys.stderr)
        for failure in result.failures:
            print(f"  - {failure}", file=sys.stderr)
        sys.exit(1)

    report = analyze_repo(args.path, config)

    # ── scan ──────────────────────────────────────────────────────────────────
    if args.command == "scan":
        output = format_json(report) if args.format == "json" else format_table(report)
        print(output)
        if args.output_json:
            with open(args.output_json, "w") as f:
                f.write(format_json(report))
        sys.exit(0)

    # ── gate ──────────────────────────────────────────────────────────────────
    failures = []
    qse4 = report.qse_total

    if qse4 < args.threshold:
        failures.append(f"QSE4={qse4:.4f} below threshold {args.threshold:.2f}")

    if args.fail_on_defects:
        for dtype in args.fail_on_defects.split(","):
            dtype = dtype.strip()
            count = len(report.defects.get(dtype, set()))
            if count > 0:
                files = sorted(report.defects[dtype])
                failures.append(f"{dtype}: {count} instance(s) — {', '.join(files)}")

    result = {
        "gate":      "PASS" if not failures else "FAIL",
        "qse4":      round(qse4, 4),
        "threshold": args.threshold,
        "failures":  failures,
        "report":    report.to_dict(),
    }

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(result, f, indent=2)

    if failures:
        print("QSE GATE FAIL", file=sys.stderr)
        for f in failures:
            print(f"  ✗ {f}", file=sys.stderr)
        sys.exit(1)

    print(f"QSE GATE PASS  QSE4={qse4:.4f}")
    sys.exit(0)


if __name__ == "__main__":
    main()
