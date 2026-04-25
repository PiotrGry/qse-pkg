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

# ── Thresholds ────────────────────────────────────────────────────────────────

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
class GateResult:
    passed: bool
    violations: list[str]
    metrics_before: dict
    metrics_after: dict

    def __str__(self) -> str:
        if self.passed:
            return "gate: PASS"
        lines = ["gate: FAIL"]
        for v in self.violations:
            lines.append(f"  {v}")
        return "\n".join(lines)


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
    pc_fail: float = PC_FAIL,
    pc_delta_fail: float = PC_DELTA_FAIL,
    rc_fail: float = RC_FAIL,
    hub_spike_factor: float = HUB_SPIKE_FACTOR,
    hub_min_score: int = HUB_MIN_SCORE,
    isolated_delta: float = ISOLATED_DELTA,
) -> GateResult:
    """Compare two dependency graphs and return architectural violations.

    Args:
        G_before: graph before the proposed change (e.g. HEAD~1)
        G_after:  graph after the proposed change (e.g. HEAD)
        Remaining args override default thresholds.

    Returns:
        GateResult with passed=True if no violations, else list of strings.
    """
    before = _snapshot(G_before)
    after  = _snapshot(G_after)
    violations: list[str] = []

    # 1. New cycle groups
    new_sccs = after["scc_count"] - before["scc_count"]
    if new_sccs > 0:
        violations.append(
            f"CYCLE: {new_sccs} new cycle group(s) introduced "
            f"(total SCC: {before['scc_count']} → {after['scc_count']}). "
            "Axiom: acyclicity — cycles make components impossible to reason about independently."
        )

    # 2. Propagation Cost: newly crossed the absolute cap this commit
    # Skip for small repos (n<PC_MIN_NODES) — PC is structurally high on small graphs
    _n_after = after["n"]
    if after["pc"] > pc_fail and before["pc"] <= pc_fail and _n_after >= PC_MIN_NODES:
        violations.append(
            f"PC_HIGH: propagation_cost crossed threshold {pc_fail} "
            f"({before['pc']:.3f} → {after['pc']:.3f}). "
            "A random change now ripples through >20% of the codebase on average."
        )
    # 3. Propagation Cost delta — rapid increase even if under absolute cap
    elif after["pc"] - before["pc"] > pc_delta_fail and _n_after >= PC_MIN_NODES:
        violations.append(
            f"PC_DELTA: propagation_cost jumped +{after['pc'] - before['pc']:.3f} "
            f"({before['pc']:.3f} → {after['pc']:.3f}) in one change. "
            f"Threshold: +{pc_delta_fail}."
        )

    # 4. Relative Cyclicity absolute threshold — flag any commit that crosses or worsens the threshold
    if after["rc"] > rc_fail and (before["rc"] <= rc_fail or after["rc"] > before["rc"]):
        violations.append(
            f"RC_HIGH: relative_cyclicity={after['rc']:.1f}% exceeds {rc_fail}% threshold "
            f"(before: {before['rc']:.1f}%). "
            "Cycle groups tend to grow continuously once above threshold (Apache Cassandra pattern)."
        )

    # 5. Hub / god-file spike
    hub_before = before["max_hub"]
    if (hub_before > 0
            and after["max_hub"] > hub_before * hub_spike_factor
            and after["max_hub"] >= hub_min_score):
        violations.append(
            f"HUB_SPIKE: max_hub_score {before['max_hub']} → {after['max_hub']} "
            f"({after['max_hub'] / hub_before:.1f}x increase). "
            "A module is becoming a god file — high fan-in AND fan-out."
        )

    # 6. Archipelago drift — isolated files accumulating
    delta_iso = after["isolated_pct"] - before["isolated_pct"]
    if delta_iso > isolated_delta:
        violations.append(
            f"ISOLATED: isolated files grew +{delta_iso:.1f}pp "
            f"({before['isolated_pct']:.1f}% → {after['isolated_pct']:.1f}% of nodes). "
            "Dead/unreachable code accumulating."
        )

    return GateResult(
        passed=len(violations) == 0,
        violations=violations,
        metrics_before=before,
        metrics_after=after,
    )
