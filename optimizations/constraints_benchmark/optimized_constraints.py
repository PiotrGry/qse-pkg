"""Optimized forbidden-edge checker for constraints benchmarking.

This module is intentionally isolated from production code. It provides an
alternative implementation that can be compared 1:1 against the baseline
checker from experiments/exp4_constraints/run.py.
"""

from collections import defaultdict
from fnmatch import translate as fnmatch_translate
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


EdgeRow = Tuple[str, str, str, str]  # (src, tgt, src_path, tgt_path)


def _root_prefix(pattern: str) -> Optional[str]:
    """Return deterministic first path segment if it has no wildcards.

    Examples:
      "api/*" -> "api"
      "src/api/**" -> "src"
      "*/api/*" -> None
    """
    clean = pattern.strip("/")
    if not clean:
        return None
    first = clean.split("/", 1)[0]
    if any(ch in first for ch in "*?[]"):
        return None
    return first


def _build_edge_cache(edges: Iterable[Tuple[str, str]]) -> Tuple[List[EdgeRow], Dict[str, List[EdgeRow]]]:
    """Precompute path-converted edges and root index."""
    rows: List[EdgeRow] = []
    by_root: Dict[str, List[EdgeRow]] = defaultdict(list)
    for src, tgt in edges:
        src_path = src.replace(".", "/")
        tgt_path = tgt.replace(".", "/")
        row = (src, tgt, src_path, tgt_path)
        rows.append(row)
        root = src_path.split("/", 1)[0]
        by_root[root].append(row)
    return rows, by_root


def check_constraints_optimized(analysis, constraints: Sequence[dict]) -> List[dict]:
    """Check forbidden-edge rules using cached paths + compiled globs.

    Output format matches baseline:
      {"rule": rule_dict, "source": src_module, "target": tgt_module}
    """
    violations: List[dict] = []

    edge_rows, rows_by_root = _build_edge_cache(analysis.graph.edges())

    compiled_rules = []
    for rule in constraints:
        if rule.get("type") != "forbidden":
            continue
        from_pattern = rule["from"]
        to_pattern = rule["to"]
        compiled_rules.append(
            (
                rule,
                re.compile(fnmatch_translate(from_pattern)),
                re.compile(fnmatch_translate(to_pattern)),
                _root_prefix(from_pattern),
            )
        )

    for rule, from_re, to_re, root_prefix in compiled_rules:
        candidates = rows_by_root.get(root_prefix, []) if root_prefix is not None else edge_rows
        for src, tgt, src_path, tgt_path in candidates:
            if from_re.fullmatch(src_path) and to_re.fullmatch(tgt_path):
                violations.append(
                    {
                        "rule": rule,
                        "source": src,
                        "target": tgt,
                    }
                )

    return violations

