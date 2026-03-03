"""QSE quality gate for LLM code generation loops."""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from qse.config import QSEConfig
from qse.pipeline import analyze_repo
from qse.report import QSEReport


@dataclass
class GateRules:
    """Pass/fail thresholds for the quality gate."""
    min_qse_total: Optional[float] = 0.7
    max_defects: Dict[str, int] = field(default_factory=lambda: {
        "anemic_entity": 0, "fat_service": 0,
        "zombie_entity": 0, "layer_violation": 0,
    })
    min_metrics: Dict[str, float] = field(default_factory=dict)
    max_retries: int = 3

    @classmethod
    def from_file(cls, path: str) -> "GateRules":
        with open(path) as f:
            data = json.load(f)
        rules = cls()
        if "min_qse_total" in data:
            rules.min_qse_total = data["min_qse_total"]
        if "max_defects" in data:
            rules.max_defects = data["max_defects"]
        if "min_metrics" in data:
            rules.min_metrics = data["min_metrics"]
        if "max_retries" in data:
            rules.max_retries = data["max_retries"]
        return rules


@dataclass
class GateResult:
    """Result of a quality gate check."""
    passed: bool
    qse_total: float
    failures: List[str]
    report: QSEReport
    feedback_prompt: str


def _build_feedback(failures: List[str], qse_total: float,
                    min_total: Optional[float]) -> str:
    if not failures:
        return ""
    lines = ["Your generated code failed QSE quality checks:"]
    for f in failures:
        lines.append(f"- {f}")
    if min_total is not None:
        lines.append(f"QSE score: {qse_total:.2f} (minimum: {min_total:.2f})")
    lines.append("Regenerate the failing files while keeping passing files unchanged.")
    return "\n".join(lines)


def quality_gate(repo_path: str, rules: GateRules = None,
                 config: QSEConfig = None) -> GateResult:
    """Run QSE analysis and check against gate rules."""
    if rules is None:
        rules = GateRules()
    report = analyze_repo(repo_path, config)
    failures = []

    # Check QSE total
    if rules.min_qse_total is not None and report.qse_total < rules.min_qse_total:
        failures.append(
            f"QSE total {report.qse_total:.2f} below minimum {rules.min_qse_total:.2f}"
        )

    # Check defect counts
    for defect_type, max_count in rules.max_defects.items():
        actual = len(report.defects.get(defect_type, set()))
        if actual > max_count:
            files = sorted(report.defects[defect_type])
            failures.append(
                f"{actual} {defect_type}(s) detected: {', '.join(files)}"
            )

    # Check sub-metric minimums
    metric_map = report.to_dict()["metrics"]
    for metric_name, min_val in rules.min_metrics.items():
        actual = metric_map.get(metric_name, 0.0)
        if actual < min_val:
            failures.append(
                f"Metric {metric_name}={actual:.2f} below minimum {min_val:.2f}"
            )

    passed = len(failures) == 0
    feedback = _build_feedback(failures, report.qse_total, rules.min_qse_total)

    return GateResult(
        passed=passed,
        qse_total=report.qse_total,
        failures=failures,
        report=report,
        feedback_prompt=feedback,
    )
