"""Architecture-agnostic forbidden-edge constraint checking.

Used by the `qse agq --constraints` path (policy-as-a-service). The newer,
richer rules engine for CI/CD gating lives in `qse.gate.rules`; this module
remains as the minimal-API shim that older callers and the legacy JSON
constraint format depend on.

Extracted from `qse/trl4_gate.py` during Sprint 0 Slice 2b when that module
moved to `_obsolete/`.
"""

from __future__ import annotations

from fnmatch import translate as fnmatch_translate
import re
from typing import Dict, List, Optional, Sequence, Tuple

import networkx as nx


def _root_prefix(pattern: str) -> Optional[str]:
    """Return first path segment if no wildcard is present there."""
    clean = pattern.strip("/")
    if not clean:
        return None
    first = clean.split("/", 1)[0]
    if any(ch in first for ch in "*?[]"):
        return None
    return first


def check_constraints_graph(graph: nx.DiGraph, constraints: Sequence[dict]) -> List[dict]:
    """Detect forbidden-edge violations on a module dependency graph.

    Each constraint is a dict of the form:
        {"type": "forbidden", "from": "<glob>", "to": "<glob>"}

    Globs are matched against the dotted module path after '.' → '/' rewrite.
    Returns a list of violation dicts: {"rule", "source", "target"}.
    """
    edge_rows: List[Tuple[str, str, str, str]] = []
    by_root: Dict[str, List[Tuple[str, str, str, str]]] = {}
    for src, tgt in graph.edges():
        src_path = src.replace(".", "/")
        tgt_path = tgt.replace(".", "/")
        row = (src, tgt, src_path, tgt_path)
        edge_rows.append(row)
        root = src_path.split("/", 1)[0]
        by_root.setdefault(root, []).append(row)

    compiled = []
    for rule in constraints:
        if rule.get("type") != "forbidden":
            continue
        from_pat = rule["from"]
        to_pat = rule["to"]
        compiled.append(
            (
                rule,
                re.compile(fnmatch_translate(from_pat)),
                re.compile(fnmatch_translate(to_pat)),
                _root_prefix(from_pat),
            )
        )

    violations: List[dict] = []
    for rule, from_re, to_re, root_prefix in compiled:
        candidates = by_root.get(root_prefix, []) if root_prefix is not None else edge_rows
        for src, tgt, src_path, tgt_path in candidates:
            if from_re.fullmatch(src_path) and to_re.fullmatch(tgt_path):
                violations.append({"rule": rule, "source": src, "target": tgt})
    return violations


def compute_constraint_score(graph: nx.DiGraph, violations: Sequence[dict]) -> float:
    """Fraction of edges that are not violations. 1.0 = clean, 0.0 = all forbidden."""
    total_edges = graph.number_of_edges()
    if total_edges == 0:
        return 1.0
    return max(0.0, 1.0 - (len(violations) / total_edges))
