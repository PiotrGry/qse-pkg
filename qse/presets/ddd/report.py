"""QSE report output formatters."""

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Set

import numpy as np

from qse.presets.ddd.metrics import SubMetrics


@dataclass
class QSEReport:
    """Complete result of a QSE analysis run."""
    metrics: SubMetrics
    qse_total: float
    defects: Dict[str, Set[str]]
    graph_stats: Dict[str, int]
    weights: np.ndarray
    enable_trace: bool = True
    test_quality: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "qse_total": round(self.qse_total, 4),
            "metrics": {
                "S": round(self.metrics.S, 4),
                "T_ddd": round(self.metrics.T_ddd, 4),
                "G": round(self.metrics.G, 4),
                "E": round(self.metrics.E, 4),
                "Risk": round(self.metrics.Risk, 4),
            },
            "defects": {k: sorted(v) for k, v in self.defects.items()},
            "graph": self.graph_stats,
            "weights": self.weights.tolist(),
            "trace_enabled": self.enable_trace,
        }


def format_json(report: QSEReport) -> str:
    """Machine-readable JSON output."""
    return json.dumps(report.to_dict(), indent=2)


def format_table(report: QSEReport) -> str:
    """Human-readable table output."""
    from tabulate import tabulate

    lines = []
    lines.append(f"QSE Total: {report.qse_total:.4f}")
    lines.append("")

    # Metrics table
    metric_rows = [
        ["S (Structure)", f"{report.metrics.S:.4f}"],
        ["T_ddd (DDD Conformance)", f"{report.metrics.T_ddd:.4f}"],
        ["G (Graph Coupling)", f"{report.metrics.G:.4f}"],
        ["E (Excess Complexity)", f"{report.metrics.E:.4f}"],
        ["Risk (Temporal)", f"{report.metrics.Risk:.4f}"],
    ]
    lines.append(tabulate(metric_rows, headers=["Metric", "Score"], tablefmt="simple"))
    lines.append("")

    # Graph stats
    if report.graph_stats:
        lines.append("Graph:")
        for k, v in report.graph_stats.items():
            lines.append(f"  {k}: {v}")
        lines.append("")

    # Defects
    total_defects = sum(len(v) for v in report.defects.values())
    lines.append(f"Defects found: {total_defects}")
    for dtype, files in sorted(report.defects.items()):
        if files:
            lines.append(f"  {dtype} ({len(files)}):")
            for f in sorted(files):
                lines.append(f"    - {f}")

    return "\n".join(lines)
