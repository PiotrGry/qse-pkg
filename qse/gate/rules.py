"""Three named rules for Sprint 0 gate.

Each rule is axiom-backed (see PR comment rationale in report.py).
Rules are deterministic: same input graph + config => same verdict.

Rules:
    CYCLE_NEW       — no new strongly-connected components in the import graph.
                      (Sprint 0: mode=any flags all cycles. mode=delta requires
                       base graph — deferred to next session.)
    LAYER_VIOLATION — no edges from high-level layer to low-level layer where
                      forbidden in config.
    BOUNDARY_LEAK   — no edges into a protected module from callers outside
                      its allowed_callers list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch, translate as fnmatch_translate
from pathlib import Path
import re
from typing import Dict, List, Optional, Sequence, Tuple

import networkx as nx

from qse.gate.config import GateConfig


@dataclass
class RuleViolation:
    rule: str                            # CYCLE_NEW | LAYER_VIOLATION | BOUNDARY_LEAK
    source: str                          # source module / cycle node
    target: str                          # target module / empty for cycles
    detail: str                          # human-readable context
    axiom: str                           # axiom citation
    fix_hint: str                        # one-line how-to-fix

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "source": self.source,
            "target": self.target,
            "detail": self.detail,
            "axiom": self.axiom,
            "fix_hint": self.fix_hint,
        }


@dataclass
class GateResult:
    passed: bool
    violations: List[RuleViolation] = field(default_factory=list)
    override: bool = False               # [skip-qse] used
    override_reason: Optional[str] = None
    rules_evaluated: List[str] = field(default_factory=list)
    meta: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "gate": "PASS" if self.passed else "FAIL",
            "violations": [v.to_dict() for v in self.violations],
            "override": self.override,
            "override_reason": self.override_reason,
            "rules_evaluated": self.rules_evaluated,
            "meta": self.meta,
        }


def _glob_to_regex(pattern: str) -> re.Pattern:
    """Convert glob (path or dotted) to compiled regex. Supports ** and *."""
    return re.compile(fnmatch_translate(pattern))


def _layer_for_module(
    module: str,
    file_path_hint: Optional[str],
    layer_globs: Dict[str, List[str]],
) -> Optional[str]:
    """Resolve layer for a module.

    Tries file path globs first (if hint given), then dotted-module globs.
    """
    candidates: List[str] = []
    if file_path_hint:
        candidates.append(file_path_hint)
    candidates.append(module)
    candidates.append(module.replace(".", "/"))

    for layer, globs in layer_globs.items():
        for g in globs:
            for cand in candidates:
                if fnmatch(cand, g):
                    return layer
    return None


def check_cycle_new(
    head_graph: nx.DiGraph,
    base_graph: Optional[nx.DiGraph],
    mode: str,
) -> List[RuleViolation]:
    """Detect new SCCs in head graph that weren't in base graph.

    mode='any'   → flag all non-trivial SCCs (Sprint 0 single-scan default).
    mode='delta' → flag SCCs whose node-set is not a subset of any base SCC.
    """
    violations: List[RuleViolation] = []
    head_sccs = [c for c in nx.strongly_connected_components(head_graph) if len(c) > 1]
    # Also include self-loops as size-1 cycles
    for n in head_graph.nodes():
        if head_graph.has_edge(n, n):
            head_sccs.append({n})

    base_sccs: List[set] = []
    if mode == "delta" and base_graph is not None:
        base_sccs = [set(c) for c in nx.strongly_connected_components(base_graph) if len(c) > 1]
        for n in base_graph.nodes():
            if base_graph.has_edge(n, n):
                base_sccs.append({n})

    for scc in head_sccs:
        scc_set = set(scc)
        if mode == "delta" and base_sccs:
            # NEW if no base SCC contains this scc_set
            is_new = not any(scc_set.issubset(b) for b in base_sccs)
            if not is_new:
                continue

        nodes_sorted = sorted(scc_set)
        # Pick a representative edge inside the SCC for source/target
        subg = head_graph.subgraph(scc_set)
        edges = list(subg.edges())
        if edges:
            src, tgt = edges[0]
        else:
            src, tgt = nodes_sorted[0], nodes_sorted[0]

        cycle_path = " → ".join(nodes_sorted[:4]) + (" → …" if len(nodes_sorted) > 4 else "")

        violations.append(RuleViolation(
            rule="CYCLE_NEW",
            source=src,
            target=tgt,
            detail=f"Cycle among {len(scc_set)} modules: {cycle_path}",
            axiom="acyclicity (MDL: cycle increases graph description length; flow: bidirectional information transport blurs module boundaries)",
            fix_hint="Extract a shared interface to break the cycle, or invert one dependency via dependency injection.",
        ))

    return violations


def check_layer_violation(
    graph: nx.DiGraph,
    layers: Dict[str, List[str]],
    forbidden: List,
    file_hints: Optional[Dict[str, str]] = None,
) -> List[RuleViolation]:
    """Detect edges matching a forbidden (from_layer, to_layer) pair."""
    violations: List[RuleViolation] = []
    if not layers or not forbidden:
        return violations

    file_hints = file_hints or {}

    # Cache layer resolution
    node_layer: Dict[str, Optional[str]] = {}
    for node in graph.nodes():
        node_layer[node] = _layer_for_module(node, file_hints.get(node), layers)

    for src, tgt in graph.edges():
        src_layer = node_layer.get(src)
        tgt_layer = node_layer.get(tgt)
        if src_layer is None or tgt_layer is None:
            continue
        for fe in forbidden:
            if src_layer == fe.from_layer and tgt_layer == fe.to_layer:
                violations.append(RuleViolation(
                    rule="LAYER_VIOLATION",
                    source=src,
                    target=tgt,
                    detail=f"Edge {src} ({src_layer}) → {tgt} ({tgt_layer}) violates forbidden layering {fe.from_layer}→{fe.to_layer}",
                    axiom="layering (MDL: high-level layer compressed independently of low-level; flow: information must not flow inward to core)",
                    fix_hint=f"Define a port/interface in {fe.from_layer} that {fe.to_layer} implements. Depend on the port, not the concrete.",
                ))
                break

    return violations


def check_boundary_leak(
    graph: nx.DiGraph,
    protected: List,
) -> List[RuleViolation]:
    """Detect edges entering a protected module from an un-whitelisted caller."""
    violations: List[RuleViolation] = []
    if not protected:
        return violations

    compiled = []
    for pm in protected:
        compiled.append((
            pm,
            _glob_to_regex(pm.module),
            [_glob_to_regex(c) for c in pm.allowed_callers],
        ))

    for src, tgt in graph.edges():
        for pm, target_re, allowed_res in compiled:
            if not target_re.fullmatch(tgt):
                continue
            # target is protected; check caller
            if any(ar.fullmatch(src) for ar in allowed_res):
                continue
            # Allow self-references within the same protected namespace
            if target_re.fullmatch(src):
                continue
            violations.append(RuleViolation(
                rule="BOUNDARY_LEAK",
                source=src,
                target=tgt,
                detail=f"Caller {src} is not in allowed_callers for protected {pm.module}",
                axiom="encapsulation (MDL: protected partition compressed through its API surface only; flow: external callers must go through named entry points)",
                fix_hint=f"Call the public API of {pm.module} instead, or add {src} to allowed_callers if this access is intentional.",
            ))
            break

    return violations


def _check_override(override_token: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Return (override_active, reason) from a commit message or PR title."""
    if not override_token:
        return False, None
    if "[skip-qse]" in override_token.lower():
        return True, override_token.strip()
    return False, None


def run_gate(
    head_graph: nx.DiGraph,
    config: GateConfig,
    base_graph: Optional[nx.DiGraph] = None,
    file_hints: Optional[Dict[str, str]] = None,
    override_token: Optional[str] = None,
) -> GateResult:
    """Run all enabled rules against the head graph.

    If override_token contains '[skip-qse]' the gate PASSes but records violations.
    """
    violations: List[RuleViolation] = []
    rules_evaluated: List[str] = []

    if config.cycle_new.enabled:
        rules_evaluated.append("CYCLE_NEW")
        violations.extend(check_cycle_new(head_graph, base_graph, config.cycle_new.mode))

    if config.layer_violation.enabled:
        rules_evaluated.append("LAYER_VIOLATION")
        violations.extend(check_layer_violation(
            head_graph, config.layers, config.layer_violation.forbidden, file_hints,
        ))

    if config.boundary_leak.enabled:
        rules_evaluated.append("BOUNDARY_LEAK")
        violations.extend(check_boundary_leak(head_graph, config.boundary_leak.protected))

    override, reason = _check_override(override_token)
    passed = len(violations) == 0 or override

    meta: Dict[str, object] = {
        "head_nodes": head_graph.number_of_nodes(),
        "head_edges": head_graph.number_of_edges(),
        "cycle_mode": config.cycle_new.mode,
        "delta_mode": base_graph is not None and config.cycle_new.mode == "delta",
    }

    return GateResult(
        passed=passed,
        violations=violations,
        override=override,
        override_reason=reason,
        rules_evaluated=rules_evaluated,
        meta=meta,
    )
