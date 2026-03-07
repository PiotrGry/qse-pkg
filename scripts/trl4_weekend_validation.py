#!/usr/bin/env python3
"""Weekend TRL4 validation runner.

Runs integrated lab scenarios and emits machine-readable evidence:
- constraints detection and recovery,
- ratchet baseline + regression block,
- deterministic reproducibility check,
- optional benchmark snapshot.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Dict, List

from qse.presets.ddd.config import QSEConfig
from qse.trl4_gate import TRL4Rules, run_trl4_gate


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: Dict[str, object]


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _create_repo_clean(base: Path) -> None:
    _write_file(base / "domain" / "__init__.py", "")
    _write_file(
        base / "domain" / "order.py",
        "class Order:\n"
        "    def __init__(self, total):\n"
        "        self.total = total\n"
        "    def validate(self):\n"
        "        return self.total >= 0\n",
    )
    _write_file(base / "application" / "__init__.py", "")
    _write_file(
        base / "application" / "order_service.py",
        "from domain.order import Order\n"
        "class OrderService:\n"
        "    def create(self, total):\n"
        "        o = Order(total)\n"
        "        o.validate()\n"
        "        return o\n",
    )
    _write_file(base / "core" / "__init__.py", "")
    _write_file(base / "core" / "repo.py", "class Repo:\n    pass\n")
    _write_file(base / "api" / "__init__.py", "")
    _write_file(
        base / "api" / "routes.py",
        "from application.order_service import OrderService\n"
        "def create_order(total):\n"
        "    return OrderService().create(total)\n",
    )


def _create_repo_violation(base: Path) -> None:
    _create_repo_clean(base)
    _write_file(
        base / "api" / "routes.py",
        "from application.order_service import OrderService\n"
        "from core.repo import Repo\n"
        "def create_order(total):\n"
        "    _ = Repo()\n"
        "    return OrderService().create(total)\n",
    )


def _create_repo_repro(base: Path) -> None:
    _write_file(base / "domain" / "__init__.py", "")
    _write_file(
        base / "domain" / "invoice.py",
        "class Invoice:\n"
        "    def __init__(self, amount):\n"
        "        self.amount = amount\n"
        "    def is_valid(self):\n"
        "        return self.amount > 0\n",
    )
    _write_file(base / "application" / "__init__.py", "")
    _write_file(
        base / "application" / "invoice_service.py",
        "from domain.invoice import Invoice\n"
        "class InvoiceService:\n"
        "    def issue(self, amount):\n"
        "        i = Invoice(amount)\n"
        "        return i.is_valid()\n",
    )
    _write_file(base / "api" / "__init__.py", "")
    _write_file(
        base / "api" / "invoice_api.py",
        "from application.invoice_service import InvoiceService\n"
        "def issue(amount):\n"
        "    return InvoiceService().issue(amount)\n",
    )


def _load_rules(config_path: str, baseline_file: str) -> TRL4Rules:
    rules = TRL4Rules.from_file(config_path)
    rules.ratchet_baseline_file = baseline_file
    return rules


def _check_constraints_cycle(workdir: Path, config_path: str) -> CheckResult:
    clean = workdir / "constraints_clean"
    bad = workdir / "constraints_bad"
    clean.mkdir(parents=True, exist_ok=True)
    bad.mkdir(parents=True, exist_ok=True)
    _create_repo_clean(clean)
    _create_repo_violation(bad)

    baseline_file = str(workdir / "constraints_ratchet_baseline.json")
    rules = _load_rules(config_path, baseline_file=baseline_file)
    rules.ratchet_enabled = False
    rules.threshold = 0.0
    rules.min_constraint_score = 0.95
    cfg = QSEConfig.from_file(config_path)
    cfg.enable_trace = False

    r_clean = run_trl4_gate(str(clean), rules=rules, qse_config=cfg)
    r_bad = run_trl4_gate(str(bad), rules=rules, qse_config=cfg)

    passed = bool(r_clean.passed and not r_bad.passed and len(r_bad.constraint_violations) > 0)
    return CheckResult(
        name="constraints_detection",
        passed=passed,
        details={
            "clean": r_clean.to_dict(),
            "bad": r_bad.to_dict(),
        },
    )


def _check_ratchet(workdir: Path, config_path: str) -> CheckResult:
    clean = workdir / "ratchet_clean"
    bad = workdir / "ratchet_bad"
    clean.mkdir(parents=True, exist_ok=True)
    bad.mkdir(parents=True, exist_ok=True)
    _create_repo_clean(clean)
    _create_repo_violation(bad)

    baseline_file = str(workdir / "ratchet_baseline.json")
    rules = _load_rules(config_path, baseline_file=baseline_file)
    rules.ratchet_enabled = True
    rules.ratchet_delta = 0.0
    rules.threshold = 0.0
    rules.min_constraint_score = 0.0
    rules.ratchet_update_on_pass = True

    cfg = QSEConfig.from_file(config_path)
    cfg.enable_trace = False

    r_first = run_trl4_gate(str(clean), rules=rules, qse_config=cfg)
    r_regress = run_trl4_gate(str(bad), rules=rules, qse_config=cfg)

    passed = bool(
        r_first.passed
        and (Path(baseline_file).exists())
        and (not r_regress.passed)
        and any("Ratchet violation" in msg for msg in r_regress.failures)
    )
    return CheckResult(
        name="ratchet_regression_block",
        passed=passed,
        details={
            "first": r_first.to_dict(),
            "regress": r_regress.to_dict(),
            "baseline_file": baseline_file,
        },
    )


def _check_reproducibility(workdir: Path, config_path: str) -> CheckResult:
    repo = workdir / "repro_repo"
    repo.mkdir(parents=True, exist_ok=True)
    _create_repo_repro(repo)

    rules = _load_rules(config_path, baseline_file=str(workdir / "repro_baseline.json"))
    rules.ratchet_enabled = False
    rules.threshold = 0.0
    rules.min_constraint_score = 0.0
    cfg = QSEConfig.from_file(config_path)
    cfg.enable_trace = False

    r1 = run_trl4_gate(str(repo), rules=rules, qse_config=cfg).to_dict()
    r2 = run_trl4_gate(str(repo), rules=rules, qse_config=cfg).to_dict()

    stable = (
        r1["qse_total"] == r2["qse_total"]
        and r1["constraint_score"] == r2["constraint_score"]
        and r1["constraint_violations"] == r2["constraint_violations"]
    )
    return CheckResult(
        name="reproducibility_static_mode",
        passed=bool(stable),
        details={"run1": r1, "run2": r2},
    )


def _check_benchmark_snapshot(workdir: Path) -> CheckResult:
    from optimizations.constraints_benchmark.benchmark import (
        Case,
        resolve_baseline_checker,
        run_case,
    )

    case = Case(nodes=1000, edges=20000, rules=100)
    legacy_checker, legacy_name = resolve_baseline_checker("legacy")
    exp4_checker, exp4_name = resolve_baseline_checker("auto")

    legacy = run_case(case, repeats=4, seed=42, baseline_checker=legacy_checker)
    exp4 = run_case(case, repeats=4, seed=42, baseline_checker=exp4_checker)

    # For TRL4 evidence we require improved performance vs legacy baseline.
    passed = bool(legacy["speedup_x"] > 1.5)
    return CheckResult(
        name="benchmark_snapshot",
        passed=passed,
        details={
            "case": asdict(case),
            "legacy_baseline": legacy_name,
            "exp4_baseline": exp4_name,
            "legacy_result": legacy,
            "exp4_result": exp4,
        },
    )


def _to_markdown(summary: dict) -> str:
    lines: List[str] = []
    lines.append("# TRL4 Validation Report")
    lines.append("")
    lines.append(f"- generated_at: `{summary['generated_at']}`")
    lines.append(f"- overall_pass: `{summary['overall_pass']}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | Status |")
    lines.append("|---|---|")
    for c in summary["checks"]:
        lines.append(f"| {c['name']} | {'PASS' if c['passed'] else 'FAIL'} |")
    lines.append("")
    lines.append("## Acceptance")
    lines.append("")
    lines.append("TRL4 PASS requires all checks == PASS in lab environment.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run weekend TRL4 validation suite")
    parser.add_argument(
        "--config",
        default="scripts/trl4_weekend_config.json",
        help="TRL4 gate config JSON",
    )
    parser.add_argument(
        "--workdir",
        default=None,
        help="Optional existing workdir (if omitted, temp dir is used)",
    )
    parser.add_argument(
        "--output-json",
        default="artifacts/trl4/validation.json",
        help="Path for machine-readable report",
    )
    parser.add_argument(
        "--output-md",
        default="artifacts/trl4/validation.md",
        help="Path for markdown report",
    )
    args = parser.parse_args()

    if args.workdir:
        workdir = Path(args.workdir).resolve()
        workdir.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        workdir = Path(tempfile.mkdtemp(prefix="trl4_weekend_"))
        cleanup = True

    try:
        checks = [
            _check_constraints_cycle(workdir, args.config),
            _check_ratchet(workdir, args.config),
            _check_reproducibility(workdir, args.config),
            _check_benchmark_snapshot(workdir),
        ]
        overall_pass = all(c.passed for c in checks)

        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "config": str(Path(args.config).resolve()),
            "workdir": str(workdir),
            "overall_pass": overall_pass,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "details": c.details,
                }
                for c in checks
            ],
        }

        out_json = Path(args.output_json)
        out_md = Path(args.output_md)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(summary, indent=2))
        out_md.write_text(_to_markdown(summary))

        print(f"TRL4 validation {'PASS' if overall_pass else 'FAIL'}")
        print(f"JSON: {out_json}")
        print(f"MD:   {out_md}")
        raise SystemExit(0 if overall_pass else 1)
    finally:
        if cleanup:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
