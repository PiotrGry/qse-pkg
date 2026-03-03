"""QSE command-line interface."""

import argparse
import sys

import numpy as np

from qse.config import QSEConfig
from qse.pipeline import analyze_repo
from qse.report import format_json, format_table


def main():
    parser = argparse.ArgumentParser(
        prog="qse",
        description="QSE — Quantitative Software Equilibrium analyzer",
    )
    sub = parser.add_subparsers(dest="command")

    scan = sub.add_parser("scan", help="Analyze a repository")
    scan.add_argument("path", help="Path to the repository root")
    scan.add_argument("--json", action="store_true", dest="json_output",
                      help="Output as JSON")
    scan.add_argument("--format", choices=["table", "json"], default="table",
                      help="Output format (default: table)")
    scan.add_argument("--no-trace", action="store_true",
                      help="Skip dynamic tracing (static analysis only)")
    scan.add_argument("--weights", type=str, default=None,
                      help="Comma-separated weights (5 values, e.g. 0.3,0.2,0.2,0.2,0.1)")
    scan.add_argument("--config", type=str, default=None,
                      help="Path to JSON config file")

    args = parser.parse_args()

    if args.command != "scan":
        parser.print_help()
        sys.exit(1)

    # Build config
    if args.config:
        config = QSEConfig.from_file(args.config)
    else:
        config = QSEConfig()

    if args.no_trace:
        config.enable_trace = False

    if args.weights:
        vals = [float(x) for x in args.weights.split(",")]
        if len(vals) != 5:
            print("Error: --weights requires exactly 5 comma-separated values", file=sys.stderr)
            sys.exit(1)
        config.weights = np.array(vals)

    report = analyze_repo(args.path, config)

    if args.json_output or args.format == "json":
        print(format_json(report))
    else:
        print(format_table(report))


if __name__ == "__main__":
    main()
