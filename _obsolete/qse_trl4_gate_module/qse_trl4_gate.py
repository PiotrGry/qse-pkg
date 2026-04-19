"""TRL4 gate: QSE threshold + constraints + ratchet baseline.

Weekend-ready wrapper for laboratory validation:
- deterministic architecture constraints (`forbidden` edges),
- monotonic ratchet against persisted baseline,
- single JSON report with PASS/FAIL.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from fnmatch import translate as fnmatch_translate
import json
import os
import re
from typing import Dict, List, Optional, Sequence, Tuple

import networkx as nx

from qse.presets.ddd.config import QSEConfig
from qse.presets.ddd.pipeline import analyze_repo
from qse.scanner import scan_repo


@dataclass
class TRL4Rules:
    """Rules for the TRL4 quality gate."""

    threshold: float = 0.80
    min_constraint_score: float = 0.95
    constraints: List[dict] = field(default_factory=list)
    ratchet_enabled: bool = False
    ratchet_baseline_file: str = ".qse/ratchet_baseline.json"
    ratchet_delta: float = 0.01
    ratchet_update_on_pass: bool = True

    @classmethod
    def from_file(cls, path: str) -> "TRL4Rules":
        with open(path) as f:
            data = json.load(f)

        gate_cfg = data.get("gate", {})
        ratchet_cfg = data.get("ratchet", {})

        rules = cls()
        # Support both flat and nested config styles.
        rules.threshold = float(data.get("threshold", gate_cfg.get("threshold", rules.threshold)))
        rules.min_constraint_score = float(
            data.get("min_constraint_score", gate_cfg.get("min_constraint_score", rules.min_constraint_score))
        )
        rules.constraints = list(data.get("constraints", []))
        rules.ratchet_enabled = bool(
            data.get("ratchet_enabled", ratchet_cfg.get("enabled", rules.ratchet_enabled))
        )
        rules.ratchet_baseline_file = str(
            data.get("ratchet_baseline_file", ratchet_cfg.get("baseline_file", rules.ratchet_baseline_file))
        )
        rules.ratchet_delta = float(
            data.get("ratchet_delta", ratchet_cfg.get("delta", rules.ratchet_delta))
        )
        rules.ratchet_update_on_pass = bool(
            data.get("ratchet_update_on_pass", ratchet_cfg.get("update_on_pass", rules.ratchet_update_on_pass))
        )
        return rules


@dataclass
class TRL4GateResult:
    passed: bool
    qse_total: float
    constraint_score: float
    constraint_violations: List[dict]
    failures: List[str]
    ratchet: Dict[str, object]

    def to_dict(self) -> dict:
        return {
            "gate": "PASS" if self.passed else "FAIL",
            "qse_total": round(self.qse_total, 4),
            "constraint_score": round(self.constraint_score, 4),
            "constraint_violations": self.constraint_violations,
            "failures": self.failures,
            "ratchet": self.ratchet,
        }


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
    """Detect forbidden-edge violations on a module dependency graph."""
    edge_rows = []
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
    total_edges = graph.number_of_edges()
    if total_edges == 0:
        return 1.0
    return max(0.0, 1.0 - (len(violations) / total_edges))


def _read_baseline(path: str) -> Optional[dict]:
    if not path or not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def _write_baseline(path: str, qse_total: float, constraint_score: float) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = {"qse_total": float(qse_total), "constraint_score": float(constraint_score)}
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)


def run_trl4_gate(repo_path: str, rules: TRL4Rules, qse_config: Optional[QSEConfig] = None) -> TRL4GateResult:
    """Run TRL4 gate logic in one call."""
    if qse_config is None:
        qse_config = QSEConfig()

    report = analyze_repo(repo_path, qse_config)
    qse_total = float(report.qse_total)

    analysis = scan_repo(repo_path, layer_map=qse_config.layer_map or None)
    violations = check_constraints_graph(analysis.graph, rules.constraints)
    constraint_score = compute_constraint_score(analysis.graph, violations)

    failures: List[str] = []
    if qse_total < rules.threshold:
        failures.append(f"qse_total={qse_total:.4f} below threshold {rules.threshold:.2f}")
    if constraint_score < rules.min_constraint_score:
        failures.append(
            f"Constraint score={constraint_score:.4f} below minimum {rules.min_constraint_score:.2f}"
        )

    ratchet_meta: Dict[str, object] = {
        "enabled": rules.ratchet_enabled,
        "baseline_file": rules.ratchet_baseline_file,
        "delta": rules.ratchet_delta,
        "baseline_found": False,
    }

    baseline = None
    if rules.ratchet_enabled:
        baseline = _read_baseline(rules.ratchet_baseline_file)
        ratchet_meta["baseline_found"] = baseline is not None
        if baseline is not None:
            # Accept both new "qse_total" and legacy "qse4" baseline keys
            base_qse = float(baseline.get("qse_total", baseline.get("qse4", 0.0)))
            base_c = float(baseline.get("constraint_score", 0.0))
            ratchet_meta["baseline_qse_total"] = base_qse
            ratchet_meta["baseline_constraint_score"] = base_c

            if qse_total + rules.ratchet_delta < base_qse:
                failures.append(
                    f"Ratchet violation: qse_total={qse_total:.4f} < baseline={base_qse:.4f} - delta={rules.ratchet_delta:.4f}"
                )
            if constraint_score + rules.ratchet_delta < base_c:
                failures.append(
                    f"Ratchet violation: constraint_score={constraint_score:.4f} < baseline={base_c:.4f} - delta={rules.ratchet_delta:.4f}"
                )

    passed = len(failures) == 0

    if passed and rules.ratchet_enabled and rules.ratchet_update_on_pass:
        if baseline is None:
            _write_baseline(rules.ratchet_baseline_file, qse_total=qse_total, constraint_score=constraint_score)
            ratchet_meta["baseline_updated"] = True
        else:
            prev_qse = float(baseline.get("qse_total", baseline.get("qse4", 0.0)))
            prev_c = float(baseline.get("constraint_score", 0.0))
            new_qse = max(prev_qse, qse_total)
            new_c = max(prev_c, constraint_score)
            if new_qse > prev_qse or new_c > prev_c:
                _write_baseline(rules.ratchet_baseline_file, qse_total=new_qse, constraint_score=new_c)
                ratchet_meta["baseline_updated"] = True
            else:
                ratchet_meta["baseline_updated"] = False

    return TRL4GateResult(
        passed=passed,
        qse_total=qse_total,
        constraint_score=constraint_score,
        constraint_violations=violations,
        failures=failures,
        ratchet=ratchet_meta,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="TRL4 gate: QSE + constraints + ratchet")
    parser.add_argument("path", help="Repository path")
    parser.add_argument("--config", type=str, default=None, help="JSON config path")
    parser.add_argument("--output-json", type=str, default=None, metavar="FILE")
    parser.add_argument("--threshold", type=float, default=None, help="Override QSE threshold")
    parser.add_argument(
        "--min-constraint-score",
        type=float,
        default=None,
        help="Override minimum constraint score",
    )
    parser.add_argument("--ratchet", action="store_true", help="Force enable ratchet")
    parser.add_argument("--no-ratchet", action="store_true", help="Force disable ratchet")
    parser.add_argument("--baseline-file", type=str, default=None, help="Ratchet baseline JSON file")
    parser.add_argument("--no-trace", action="store_true", help="Disable tracer in QSE pipeline")
    args = parser.parse_args()

    rules = TRL4Rules.from_file(args.config) if args.config else TRL4Rules()
    qse_cfg = QSEConfig.from_file(args.config) if args.config else QSEConfig()

    if args.no_trace:
        qse_cfg.enable_trace = False
    if args.threshold is not None:
        rules.threshold = args.threshold
    if args.min_constraint_score is not None:
        rules.min_constraint_score = args.min_constraint_score
    if args.ratchet:
        rules.ratchet_enabled = True
    if args.no_ratchet:
        rules.ratchet_enabled = False
    if args.baseline_file:
        rules.ratchet_baseline_file = args.baseline_file

    result = run_trl4_gate(args.path, rules=rules, qse_config=qse_cfg)
    payload = result.to_dict()

    if args.output_json:
        with open(args.output_json, "w") as f:
            json.dump(payload, f, indent=2)

    if result.passed:
        print(
            f"TRL4 GATE PASS  qse_total={result.qse_total:.4f}  constraint_score={result.constraint_score:.4f}"
        )
        raise SystemExit(0)

    print("TRL4 GATE FAIL")
    for failure in result.failures:
        print(f"  - {failure}")
    raise SystemExit(1)


if __name__ == "__main__":
    main()

