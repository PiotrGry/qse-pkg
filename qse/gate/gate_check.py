"""Delta-based architectural gate check.

gate_check(G_before, G_after) compares two dependency graphs and returns a
list of human-readable violation strings. Empty list = clean.

Metrics checked (all delta-based — architecture-style agnostic):
  CYCLE       SCC_count increased  → new cycle group introduced
  PC_DELTA    propagation_cost increased past threshold delta
  RC_EXCEED   relative_cyclicity exceeded absolute threshold (>4%)
  HUB_SPIKE   max_hub_score increased by ≥ HUB_SPIKE_FACTOR (new god file)
  ISOLATED    isolated_pct increased by > ISOLATED_DELTA (archipelago drift)

All thresholds are empirically grounded:
  PC threshold: von Zitzewitz (2022), 300+ architectural assessments
  RC threshold: same source, "zero cycles between packages"
  HUB_SPIKE:    micro-lab calibration (god file = 5-32× hub_score spike)
  ISOLATED:     micro-lab calibration (archipelago = silent dead code)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import networkx as nx

from qse.graph_metrics import (
    _internal_subgraph,
    compute_propagation_cost,
    compute_relative_cyclicity,
)

# ── Thresholds (defaults; per-language overrides in LANG_THRESHOLDS) ──────────

# PC: absolute cap — if after-PC exceeds this, fail regardless of delta
PC_FAIL = 0.20          # von Zitzewitz: concerning for 500≤n<5000
PC_MIN_NODES = 50       # below this, PC is informational only (small repos inflate PC naturally)

# PC: delta cap — if PC increased by more than this in one commit, fail
PC_DELTA_FAIL = 0.05

# RC: absolute threshold — any value above this fails
RC_FAIL = 4.0           # %  (von Zitzewitz zero-tolerance for packages)

# HUB: factor by which max_hub_score may grow before triggering
HUB_SPIKE_FACTOR = 3.0  # 3× increase in one commit = god-file risk
HUB_MIN_SCORE = 10      # absolute floor — hubs below this are ignored (small repos)

# ISOLATED: percentage-point increase in isolated nodes that triggers warning
ISOLATED_DELTA = 5.0    # % of total nodes


# Diff-geometry rules — fire on the *shape* of the diff, not the resulting graph.
# Captures AI-burst patterns (many new files at once) before they manifest as
# graph topology problems. The static benchmark dataset cannot validate these
# (it is snapshot-only, not delta), so they are calibrated by intent: AI-burst
# tools generate scaffolding in batches, humans rarely add 5+ new modules in
# one commit.
ARCHIPELAGO_NEW_RATIO  = 0.6   # new_files / total_changed_files
ARCHIPELAGO_MIN_FILES  = 5     # absolute floor — small diffs ignored
VOLUME_NEW_FILE_LIMIT  = 15    # raw count of new files in one commit


# ── Per-language thresholds ───────────────────────────────────────────────────
# Calibrated from artifacts/benchmark/agq_240_{python,java,go}80.json (Apr 2026):
#   Python: p90 of (1-acyclicity) = 0%   — most repos cycle-free, strict RC=4%
#   Java:   p90 of (1-acyclicity) = 8.8% — culturally cyclic (frameworks), RC=10%
#   Go:     p90 of (1-acyclicity) = 0%   — Go discourages cycles, even stricter RC=2%
# E/N (edges/nodes) p75 per language: python=3.46, java=4.73, go=4.83 — Java/Go
# tolerate higher PC. PC defaults preserve von Zitzewitz threshold for Python (0.20)
# and adjust ±0.05 for Java/Go based on coupling-density distribution.
#
# IMPORTANT: these are starting points from STRUCTURAL distribution. Predictive
# validity (PC/RC vs bugs) is under empirical investigation. Use deltas, not
# absolute thresholds, for actionable signals.

LANG_THRESHOLDS: dict[str, dict[str, float]] = {
    "python": {
        "pc_fail":           0.20,
        "pc_delta_fail":     0.05,
        "rc_fail":           4.0,
        "hub_spike_factor":  3.0,
        "hub_min_score":     10,
        "isolated_delta":    5.0,
    },
    "java": {
        "pc_fail":           0.25,   # Java has denser coupling culturally
        "pc_delta_fail":     0.05,
        "rc_fail":           10.0,   # 71% of Java OSS has some cycles
        "hub_spike_factor":  3.0,
        "hub_min_score":     10,
        "isolated_delta":    5.0,
    },
    "go": {
        "pc_fail":           0.18,   # Go encourages flatter dep trees
        "pc_delta_fail":     0.05,
        "rc_fail":           2.0,    # Go culturally cycle-free; even small RC alarming
        "hub_spike_factor":  3.0,
        "hub_min_score":     10,
        "isolated_delta":    5.0,
    },
}


def get_thresholds(language: str = "python") -> dict[str, float]:
    """Return threshold dict for a given language; falls back to python."""
    return LANG_THRESHOLDS.get(language.lower(), LANG_THRESHOLDS["python"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _scc_count(G: nx.DiGraph) -> int:
    SG = _internal_subgraph(G)
    return sum(1 for s in nx.strongly_connected_components(SG) if len(s) >= 2)


def _max_hub(G: nx.DiGraph) -> int:
    if G.number_of_nodes() == 0:
        return 0
    fi = dict(G.in_degree())
    fo = dict(G.out_degree())
    return max(fi[v] * fo[v] for v in G.nodes())


def _isolated_pct(G: nx.DiGraph) -> float:
    n = G.number_of_nodes()
    if n == 0:
        return 0.0
    isolated = sum(
        1 for v in G.nodes()
        if G.in_degree(v) == 0 and G.out_degree(v) == 0
    )
    return 100.0 * isolated / n


# ── Public API ────────────────────────────────────────────────────────────────

@dataclass
class Violation:
    """Structured violation with culprit identification and explanation."""
    rule: str            # CYCLE, PC_HIGH, PC_DELTA, RC_HIGH, HUB_SPIKE, ISOLATED
    summary: str         # short, one-line description (numbers + rule)
    why: str             # 1-2 sentence explanation of why this matters
    fix: str             # suggested action
    culprits: list[str]  # specific nodes/edges/files involved (often empty for global rules)

    def render(self) -> str:
        lines = [f"[{self.rule}] {self.summary}"]
        if self.culprits:
            for c in self.culprits[:5]:
                lines.append(f"    • {c}")
            if len(self.culprits) > 5:
                lines.append(f"    • ... +{len(self.culprits) - 5} more")
        lines.append(f"    Why: {self.why}")
        lines.append(f"    Fix: {self.fix}")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.render()


@dataclass
class GateResult:
    passed: bool
    violations: list                # list[Violation] OR list[str] for back-compat
    metrics_before: dict
    metrics_after: dict

    def __str__(self) -> str:
        if self.passed:
            return "gate: PASS"
        lines = ["gate: FAIL"]
        for v in self.violations:
            if isinstance(v, Violation):
                lines.append(f"  {v.render()}")
            else:
                lines.append(f"  {v}")
        return "\n".join(lines)


def _new_sccs(G_before: nx.DiGraph, G_after: nx.DiGraph) -> list[list[str]]:
    """Return SCCs (≥2 nodes) present in G_after but not in G_before."""
    SG_b = _internal_subgraph(G_before)
    SG_a = _internal_subgraph(G_after)
    before_sets = [frozenset(s) for s in nx.strongly_connected_components(SG_b) if len(s) >= 2]
    after_sets = [frozenset(s) for s in nx.strongly_connected_components(SG_a) if len(s) >= 2]
    return [sorted(s) for s in after_sets if s not in before_sets]


def _hub_node(G: nx.DiGraph) -> Optional[str]:
    """Return the node with the highest hub_score (fi×fo), or None if empty."""
    if G.number_of_nodes() == 0:
        return None
    fi = dict(G.in_degree())
    fo = dict(G.out_degree())
    return max(G.nodes(), key=lambda v: fi[v] * fo[v], default=None)


def _new_isolated(G_before: nx.DiGraph, G_after: nx.DiGraph) -> list[str]:
    """Nodes isolated in G_after that were absent or non-isolated in G_before."""
    def isolated(G):
        return {v for v in G.nodes()
                if G.in_degree(v) == 0 and G.out_degree(v) == 0}
    return sorted(isolated(G_after) - isolated(G_before))


def _snapshot(G: nx.DiGraph) -> dict:
    return {
        "n":          G.number_of_nodes(),
        "e":          G.number_of_edges(),
        "scc_count":  _scc_count(G),
        "pc":         compute_propagation_cost(G),
        "rc":         compute_relative_cyclicity(G),
        "max_hub":    _max_hub(G),
        "isolated_pct": _isolated_pct(G),
    }


def gate_check(
    G_before: nx.DiGraph,
    G_after: nx.DiGraph,
    language: str = "python",
    pc_fail: Optional[float] = None,
    pc_delta_fail: Optional[float] = None,
    rc_fail: Optional[float] = None,
    hub_spike_factor: Optional[float] = None,
    hub_min_score: Optional[int] = None,
    isolated_delta: Optional[float] = None,
    diff_meta: Optional[dict] = None,
) -> GateResult:
    """Compare two dependency graphs and return architectural violations.

    Args:
        G_before: graph before the proposed change (e.g. HEAD~1)
        G_after:  graph after the proposed change (e.g. HEAD)
        language: 'python' (default), 'java', or 'go' — selects threshold preset.
        Remaining args override individual thresholds (None = use language preset).

    Returns:
        GateResult with passed=True if no violations, else list of strings.
    """
    # Resolve thresholds: explicit args > language preset > module defaults
    presets = get_thresholds(language)
    pc_fail          = pc_fail          if pc_fail          is not None else presets["pc_fail"]
    pc_delta_fail    = pc_delta_fail    if pc_delta_fail    is not None else presets["pc_delta_fail"]
    rc_fail          = rc_fail          if rc_fail          is not None else presets["rc_fail"]
    hub_spike_factor = hub_spike_factor if hub_spike_factor is not None else presets["hub_spike_factor"]
    hub_min_score    = hub_min_score    if hub_min_score    is not None else int(presets["hub_min_score"])
    isolated_delta   = isolated_delta   if isolated_delta   is not None else presets["isolated_delta"]

    before = _snapshot(G_before)
    after  = _snapshot(G_after)
    violations: list[Violation] = []

    # 1. New cycle groups
    new_sccs_count = after["scc_count"] - before["scc_count"]
    if new_sccs_count > 0:
        new_groups = _new_sccs(G_before, G_after)
        culprits = []
        for grp in new_groups[:3]:
            culprits.append(f"SCC: {' → '.join(grp[:6])}{' → ...' if len(grp) > 6 else ''}")
        violations.append(Violation(
            rule="CYCLE",
            summary=(f"{new_sccs_count} new cycle group(s) introduced "
                     f"(total SCC: {before['scc_count']} → {after['scc_count']})"),
            why=("Cycles make modules impossible to reason about independently. "
                 "Once introduced, cycle groups tend to grow over time (Apache "
                 "Cassandra pattern: 450→900→1300 nodes over 3 years)."),
            fix=("Identify the back-edge that closed the cycle (often the most "
                 "recent import). Invert the dependency via dependency injection, "
                 "or extract shared types to a third module."),
            culprits=culprits,
        ))

    # 2. Propagation Cost: newly crossed the absolute cap this commit
    _n_after = after["n"]
    if after["pc"] > pc_fail and before["pc"] <= pc_fail and _n_after >= PC_MIN_NODES:
        violations.append(Violation(
            rule="PC_HIGH",
            summary=(f"propagation_cost crossed threshold {pc_fail} "
                     f"({before['pc']:.3f} → {after['pc']:.3f})"),
            why=("PC is the fraction of the codebase a random change can ripple "
                 f"through. {after['pc']*100:.0f}% means refactoring one module "
                 "touches that share of the codebase on average."),
            fix=("Look for the new long import chains. Break tight coupling by "
                 "introducing interfaces, or split the affected module."),
            culprits=[],
        ))
    # 3. Propagation Cost delta
    elif after["pc"] - before["pc"] > pc_delta_fail and _n_after >= PC_MIN_NODES:
        violations.append(Violation(
            rule="PC_DELTA",
            summary=(f"propagation_cost jumped +{after['pc'] - before['pc']:.3f} "
                     f"({before['pc']:.3f} → {after['pc']:.3f}) in one change"),
            why=("A single commit increased the codebase's coupling depth by more "
                 f"than {pc_delta_fail}. AI tools often add this when they connect "
                 "many modules to one new helper."),
            fix=("Review imports added in this diff. If a single new module is "
                 "imported by many existing modules, consider whether it should "
                 "be split or its API narrowed."),
            culprits=[],
        ))

    # 4. Relative Cyclicity absolute threshold
    if after["rc"] > rc_fail and (before["rc"] <= rc_fail or after["rc"] > before["rc"]):
        violations.append(Violation(
            rule="RC_HIGH",
            summary=(f"relative_cyclicity={after['rc']:.1f}% exceeds {rc_fail}% threshold "
                     f"(before: {before['rc']:.1f}%)"),
            why=("Relative Cyclicity weighs cycle group size: large SCCs hurt "
                 "exponentially more than small ones. Crossing the threshold "
                 "predicts continued growth absent intervention."),
            fix=("Use `qse archeology` to find when the largest SCC formed. "
                 "Break it by inverting one or two key edges via interfaces."),
            culprits=[],
        ))

    # 5. Hub / god-file spike
    hub_before = before["max_hub"]
    if (hub_before > 0
            and after["max_hub"] > hub_before * hub_spike_factor
            and after["max_hub"] >= hub_min_score):
        hub = _hub_node(G_after)
        culprits = [f"{hub} (hub_score = {after['max_hub']})"] if hub else []
        violations.append(Violation(
            rule="HUB_SPIKE",
            summary=(f"max_hub_score {before['max_hub']} → {after['max_hub']} "
                     f"({after['max_hub'] / hub_before:.1f}x increase)"),
            why=("hub_score = fan-in × fan-out. High values mean a module both "
                 "depends on many things AND is depended upon by many things — "
                 "the classic god-file shape that becomes a refactoring blocker."),
            fix=(f"Investigate {hub or 'the top hub'}. Often a 'utils' or 'core' "
                 "module that has accreted unrelated responsibilities. Split by "
                 "concern, move helpers closer to their callers."),
            culprits=culprits,
        ))

    # 6. Archipelago drift — isolated files accumulating
    delta_iso = after["isolated_pct"] - before["isolated_pct"]
    if delta_iso > isolated_delta:
        new_iso = _new_isolated(G_before, G_after)
        culprits = [f"isolated: {n}" for n in new_iso[:5]]
        violations.append(Violation(
            rule="ISOLATED",
            summary=(f"isolated files grew +{delta_iso:.1f}pp "
                     f"({before['isolated_pct']:.1f}% → {after['isolated_pct']:.1f}% of nodes)"),
            why=("Modules with zero in-degree AND zero out-degree are unreachable. "
                 "AI tools commonly generate scaffolding that never gets wired "
                 "into the graph — dead code that costs maintenance forever."),
            fix=("Remove the new isolated files, or wire them into an existing "
                 "import chain. If they are intentional (scripts, fixtures), "
                 "exclude their path via --exclude in your gate config."),
            culprits=culprits,
        ))

    # 7. Diff-geometry: archipelago-bias (AI-burst signal)
    # Only fires when caller passed diff_meta (typically pre-commit hook
    # or gate-diff CLI which can introspect git diff).
    if diff_meta:
        new_count   = int(diff_meta.get("new_files", 0))
        total       = int(diff_meta.get("total_changed", 0))
        new_paths   = list(diff_meta.get("new_paths", []))[:8]

        if total >= ARCHIPELAGO_MIN_FILES:
            ratio = new_count / total
            if ratio >= ARCHIPELAGO_NEW_RATIO:
                violations.append(Violation(
                    rule="ARCHIPELAGO_BIAS",
                    summary=(f"diff is {ratio*100:.0f}% new files "
                             f"({new_count}/{total} changed). Archipelago risk."),
                    why=("AI tools generate scaffolding in batches: many new "
                         "modules with shallow integration. Pure new-file diffs "
                         "predict isolated_pct drift in upcoming commits."),
                    fix=("Review the new files. If they form a coherent feature, "
                         "ensure they wire into the existing graph. If scaffolding "
                         "is intentional (tests, fixtures), exclude their path."),
                    culprits=[f"new: {p}" for p in new_paths],
                ))

        if new_count > VOLUME_NEW_FILE_LIMIT:
            violations.append(Violation(
                rule="VOLUME_SPIKE",
                summary=f"{new_count} new files added in one commit",
                why=("Single-commit volume spike. AI agents often dump generated "
                     "code in batches; reviewers cannot reason about that much "
                     "new architecture at once."),
                fix=("Split into smaller commits, one logical unit per commit. "
                     "If this is intentional bulk work (refactor, codegen), "
                     "consider --no-verify and document the rationale."),
                culprits=[f"new: {p}" for p in new_paths],
            ))

    return GateResult(
        passed=len(violations) == 0,
        violations=violations,
        metrics_before=before,
        metrics_after=after,
    )
