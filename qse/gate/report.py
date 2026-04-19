"""Output formatters for the gate: JSON + PR-comment markdown + JSONL telemetry."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional

from qse.gate.rules import GateResult


def to_json(result: GateResult, indent: int = 2) -> str:
    return json.dumps(result.to_dict(), indent=indent)


def to_pr_comment(result: GateResult, repo: Optional[str] = None, pr: Optional[int] = None) -> str:
    """Render a GitHub PR comment markdown summary."""
    lines: list[str] = []
    header = "✅ QSE Gate: PASS" if result.passed else "❌ QSE Gate: FAIL"
    if result.override:
        header = "⚠️ QSE Gate: OVERRIDE (violations logged)"
    lines.append(f"### {header}")
    lines.append("")
    if repo or pr:
        lines.append(f"_Repo: {repo or '—'}  PR: #{pr or '—'}_")
        lines.append("")

    lines.append(
        f"**Rules evaluated:** {', '.join(result.rules_evaluated) or '(none)'}  "
        f"· **Nodes:** {result.meta.get('head_nodes', 0)}  "
        f"· **Edges:** {result.meta.get('head_edges', 0)}"
    )
    lines.append("")

    if not result.violations:
        lines.append("No architectural drift detected. 🟢")
        return "\n".join(lines)

    # Group by rule
    by_rule: dict[str, list] = {}
    for v in result.violations:
        by_rule.setdefault(v.rule, []).append(v)

    for rule, vs in by_rule.items():
        lines.append(f"#### {rule} ({len(vs)} violation{'s' if len(vs) != 1 else ''})")
        lines.append("")
        for v in vs[:10]:
            lines.append(f"- `{v.source}` → `{v.target}`")
            lines.append(f"  - **Detail:** {v.detail}")
            lines.append(f"  - **Axiom:** {v.axiom}")
            lines.append(f"  - **Fix:** {v.fix_hint}")
        if len(vs) > 10:
            lines.append(f"- …and {len(vs) - 10} more.")
        lines.append("")

    lines.append("**Override:** add `[skip-qse]` to PR title or commit message (logged in telemetry).")
    return "\n".join(lines)


def write_telemetry(
    result: GateResult,
    jsonl_path: str,
    repo: Optional[str] = None,
    pr: Optional[int] = None,
    commit: Optional[str] = None,
) -> None:
    """Append one JSONL line per rule evaluated (telemetry)."""
    p = Path(jsonl_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    base_row = {
        "ts": ts,
        "repo": repo,
        "pr": pr,
        "commit": commit,
        "verdict": "PASS" if result.passed else "FAIL",
        "override": result.override,
    }

    with open(p, "a", encoding="utf-8") as f:
        # one row per rule (for aggregation), plus one row per violation
        for rule in result.rules_evaluated:
            rule_violations = [v for v in result.violations if v.rule == rule]
            f.write(json.dumps({
                **base_row,
                "event": "rule_evaluated",
                "rule": rule,
                "violation_count": len(rule_violations),
            }) + "\n")
        for v in result.violations:
            f.write(json.dumps({
                **base_row,
                "event": "violation",
                "rule": v.rule,
                "source": v.source,
                "target": v.target,
            }) + "\n")
