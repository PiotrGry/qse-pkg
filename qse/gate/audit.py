"""Audit aggregator — turns raw gate violations into a priority-ranked report.

The gate (`qse.gate.rules.run_gate`) emits a list of structural violations.
That's great for CI (pass/fail), but the *Pilot Audit* product promises
"komponenty podwyższonego ryzyka + rekomendacje priorytetyzacji" — i.e. a
report an architect can hand to a CTO with a 1-page exec summary and a fix
roadmap. This module builds that report.

Design:
    run_gate (block-oriented) → AuditReport (analysis-oriented).

The audit is non-blocking: every analysis exits 0. Consumers choose how
aggressive to be about the findings.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import networkx as nx

from qse.gate.config import GateConfig
from qse.gate.rules import GateResult, RuleViolation, run_gate


# --- Scoring weights (tuneable, documented in report output) ---

SEVERITY_WEIGHT = {
    "CYCLE_NEW":        3.0,   # cycles block reasoning; hardest to unwind
    "LAYER_VIOLATION":  2.0,   # wrong direction but usually fixable via port
    "BOUNDARY_LEAK":    2.5,   # crosses a hard policy line
}

PRIORITY_THRESHOLDS = {
    "P1": 60.0,   # immediate (next sprint)
    "P2": 30.0,   # plan for the quarter
    # anything below P2 cutoff → P3 (backlog)
}


@dataclass
class ComponentRisk:
    module: str
    risk_score: float                          # 0–100
    in_scc: bool                               # participates in an SCC > 1
    rules_hit: List[str] = field(default_factory=list)
    reason: str = ""
    priority: str = "P3"

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "risk_score": round(self.risk_score, 1),
            "priority": self.priority,
            "in_scc": self.in_scc,
            "rules_hit": self.rules_hit,
            "reason": self.reason,
        }


@dataclass
class AuditReport:
    repo: str
    generated_at: str
    total_nodes: int
    total_edges: int
    total_violations: int
    violations_by_rule: Dict[str, int]
    health_score: float                         # 0–100
    health_band: str                            # green | yellow | orange | red
    top_risks: List[ComponentRisk]              # ranked descending
    recommendations: List[str]                  # priority-ordered
    raw_violations: List[RuleViolation]

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "generated_at": self.generated_at,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "total_violations": self.total_violations,
            "violations_by_rule": self.violations_by_rule,
            "health_score": round(self.health_score, 1),
            "health_band": self.health_band,
            "top_risks": [r.to_dict() for r in self.top_risks],
            "recommendations": self.recommendations,
            "raw_violations": [v.to_dict() for v in self.raw_violations],
        }


def _priority_for(score: float, in_scc: bool) -> str:
    """SCC membership auto-promotes to P1: cycles are expensive to unwind."""
    if in_scc or score >= PRIORITY_THRESHOLDS["P1"]:
        return "P1"
    if score >= PRIORITY_THRESHOLDS["P2"]:
        return "P2"
    return "P3"


def _component_risk(
    module: str,
    violations: List[RuleViolation],
    graph: nx.DiGraph,
    sccs: List[set],
    total_edges: int,
) -> ComponentRisk:
    """Compute a 0–100 risk score for one module."""
    weighted = 0.0
    rules_hit: List[str] = []
    for v in violations:
        if module in (v.source, v.target):
            weighted += SEVERITY_WEIGHT.get(v.rule, 1.0)
            if v.rule not in rules_hit:
                rules_hit.append(v.rule)

    in_scc = any(module in scc for scc in sccs)

    # Normalize: base = 20 points per weighted violation, capped via edge count.
    # A module in a 10-node repo with 3 violations scores higher than the same
    # in a 1000-node repo — the ratio is what matters.
    if total_edges > 0:
        pressure = min(1.0, weighted / max(1.0, total_edges * 0.1))
    else:
        pressure = 0.0
    score = pressure * 80.0 + (20.0 if in_scc else 0.0)
    score = min(100.0, score)

    if in_scc and rules_hit:
        reason = f"Participates in a cycle; also flagged by {', '.join(rules_hit)}."
    elif in_scc:
        reason = "Participates in a strongly-connected component (cycle)."
    elif rules_hit:
        reason = f"Flagged by {', '.join(rules_hit)}."
    else:
        reason = "No direct violations."

    return ComponentRisk(
        module=module,
        risk_score=score,
        in_scc=in_scc,
        rules_hit=rules_hit,
        reason=reason,
        priority=_priority_for(score, in_scc),
    )


def _health_score(total_violations: int, total_edges: int) -> tuple[float, str]:
    if total_edges == 0:
        return 100.0, "green"
    # Inverse normalization: >= 10% of edges violated → 0; 0 violations → 100.
    ratio = min(1.0, total_violations / (total_edges * 0.1))
    score = (1.0 - ratio) * 100.0
    if score >= 90:
        band = "green"
    elif score >= 70:
        band = "yellow"
    elif score >= 50:
        band = "orange"
    else:
        band = "red"
    return score, band


def _build_recommendations(top_risks: List[ComponentRisk]) -> List[str]:
    """Priority-ordered recommendations, derived from the top risks."""
    recs: List[str] = []
    p1 = [r for r in top_risks if r.priority == "P1"]
    p2 = [r for r in top_risks if r.priority == "P2"]
    p3 = [r for r in top_risks if r.priority == "P3"]

    if p1:
        scc_mods = [r.module for r in p1 if r.in_scc]
        if scc_mods:
            recs.append(
                f"**P1 — Break cycles:** extract shared interfaces to eliminate the SCC involving "
                f"{', '.join(sorted(set(scc_mods))[:3])}{'…' if len(scc_mods) > 3 else ''}."
            )
        other_p1 = [r for r in p1 if not r.in_scc]
        if other_p1:
            recs.append(
                f"**P1 — Hard policy fixes:** resolve violations in "
                f"{', '.join(r.module for r in other_p1[:3])}{'…' if len(other_p1) > 3 else ''} — "
                f"these cross axiomatic boundaries."
            )
    if p2:
        recs.append(
            f"**P2 — Plan for this quarter:** address {len(p2)} moderate-risk components via "
            f"targeted refactors (port/interface extraction, boundary hardening)."
        )
    if p3:
        recs.append(
            f"**P3 — Backlog:** {len(p3)} low-risk components under observation — track trend, "
            f"address if they grow."
        )
    if not recs:
        recs.append("No structural issues detected. Maintain current discipline; re-audit quarterly.")
    return recs


def audit_from_gate_result(
    repo: str,
    result: GateResult,
    head_graph: nx.DiGraph,
    top_n: int = 10,
) -> AuditReport:
    """Build an AuditReport from an existing GateResult + its head graph."""
    violations = result.violations
    sccs = [set(c) for c in nx.strongly_connected_components(head_graph) if len(c) > 1]
    for n in head_graph.nodes():
        if head_graph.has_edge(n, n):
            sccs.append({n})

    # Collect every module mentioned in any violation.
    mods: List[str] = []
    seen = set()
    for v in violations:
        for m in (v.source, v.target):
            if m not in seen:
                seen.add(m)
                mods.append(m)

    risks = [
        _component_risk(m, violations, head_graph, sccs, head_graph.number_of_edges())
        for m in mods
    ]
    risks.sort(key=lambda r: r.risk_score, reverse=True)
    top = risks[:top_n]

    health, band = _health_score(len(violations), head_graph.number_of_edges())
    rule_counts = dict(Counter(v.rule for v in violations))

    return AuditReport(
        repo=repo,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        total_nodes=head_graph.number_of_nodes(),
        total_edges=head_graph.number_of_edges(),
        total_violations=len(violations),
        violations_by_rule=rule_counts,
        health_score=health,
        health_band=band,
        top_risks=top,
        recommendations=_build_recommendations(top),
        raw_violations=violations,
    )


def audit_repo(repo_path: str, config: GateConfig, head_graph: nx.DiGraph,
               file_hints: Optional[Dict[str, str]] = None) -> AuditReport:
    """Convenience: run the gate on `head_graph` then build an AuditReport."""
    result = run_gate(head_graph=head_graph, config=config, file_hints=file_hints)
    return audit_from_gate_result(repo=repo_path, result=result, head_graph=head_graph)


# --- Markdown renderer ---

_BAND_BADGE = {
    "green":  "🟢 Healthy",
    "yellow": "🟡 Minor drift",
    "orange": "🟠 Significant drift",
    "red":    "🔴 Severe drift",
}


def to_markdown(report: AuditReport) -> str:
    """Render a Pilot-Audit-style report. The exec summary fits in one screen."""
    lines: list[str] = []
    lines.append(f"# AI-Drift Firewall — Architecture Audit")
    lines.append("")
    lines.append(f"**Repository:** `{report.repo}`  ")
    lines.append(f"**Generated:** {report.generated_at}  ")
    lines.append(f"**Scan:** {report.total_nodes} modules, {report.total_edges} dependencies")
    lines.append("")
    lines.append("## Executive summary")
    lines.append("")
    lines.append(f"- **Health score:** **{report.health_score:.1f}/100** "
                 f"({_BAND_BADGE.get(report.health_band, report.health_band)})")
    lines.append(f"- **Violations:** {report.total_violations} across "
                 f"{len(report.violations_by_rule)} rule(s)")
    if report.violations_by_rule:
        breakdown = ", ".join(f"{k}: {v}" for k, v in report.violations_by_rule.items())
        lines.append(f"- **Breakdown:** {breakdown}")
    p1_count = sum(1 for r in report.top_risks if r.priority == "P1")
    p2_count = sum(1 for r in report.top_risks if r.priority == "P2")
    p3_count = sum(1 for r in report.top_risks if r.priority == "P3")
    lines.append(f"- **Prioritized risks:** P1={p1_count}  P2={p2_count}  P3={p3_count}  (top 10 shown below)")
    lines.append("")

    lines.append("## Recommendations")
    lines.append("")
    for rec in report.recommendations:
        lines.append(f"- {rec}")
    lines.append("")

    if report.top_risks:
        lines.append("## Top at-risk components")
        lines.append("")
        lines.append("| Priority | Risk | Module | Rules | Reason |")
        lines.append("|---|---|---|---|---|")
        for r in report.top_risks:
            rules = ", ".join(r.rules_hit) or "—"
            lines.append(f"| **{r.priority}** | {r.risk_score:.0f} | `{r.module}` | {rules} | {r.reason} |")
        lines.append("")

    if report.raw_violations:
        lines.append("## Raw violations")
        lines.append("")
        lines.append("<details><summary>Expand full list</summary>")
        lines.append("")
        for v in report.raw_violations:
            lines.append(f"- **[{v.rule}]** `{v.source}` → `{v.target}`  ")
            lines.append(f"  - *Detail:* {v.detail}  ")
            lines.append(f"  - *Axiom:* {v.axiom}  ")
            lines.append(f"  - *Fix:* {v.fix_hint}")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "*Scoring:* risk = normalized weighted violations (CYCLE_NEW=3, LAYER_VIOLATION=2, "
        "BOUNDARY_LEAK=2.5) + 20 for SCC membership. Priority P1 at score ≥ 60 or any SCC "
        "membership; P2 at 30–59; P3 below. Health score = 100 − (violations / (0.1 × edges)) × 100, "
        "clipped to [0, 100]."
    )
    return "\n".join(lines)
