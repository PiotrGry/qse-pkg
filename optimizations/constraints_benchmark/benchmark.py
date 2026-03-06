#!/usr/bin/env python3
"""Benchmark baseline vs optimized forbidden-edge checker.

Comparability guarantees:
1) Both methods run on identical graph + identical constraint rules.
2) Seeded synthetic generation for deterministic workloads.
3) Each case validates exact violation-set equality before timing results.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
import random
import statistics
import sys
import time
from typing import Iterable, List, Sequence, Tuple

import networkx as nx


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Baseline (old) implementation from existing code.
from experiments.exp4_constraints.run import check_constraints as check_constraints_baseline

from optimizations.constraints_benchmark.optimized_constraints import check_constraints_optimized


@dataclass
class AnalysisStub:
    graph: nx.DiGraph


@dataclass
class Case:
    nodes: int
    edges: int
    rules: int


def check_constraints_legacy(analysis, constraints: Sequence[dict]) -> List[dict]:
    """Fallback baseline matching original O(rules*edges) logic."""
    violations = []
    for rule in constraints:
        if rule.get("type") != "forbidden":
            continue
        from_pattern = rule["from"]
        to_pattern = rule["to"]
        for src, tgt in analysis.graph.edges():
            src_path = src.replace(".", "/")
            tgt_path = tgt.replace(".", "/")
            if fnmatch(src_path, from_pattern) and fnmatch(tgt_path, to_pattern):
                violations.append({"rule": rule, "source": src, "target": tgt})
    return violations


def resolve_baseline_checker(mode: str):
    """Resolve baseline checker mode.

    Modes:
      - auto: prefer exp4 checker, fallback to legacy if not callable
      - exp4: force exp4 checker (fail if unusable)
      - legacy: force naive legacy checker
    """
    if mode == "legacy":
        return check_constraints_legacy, "legacy_fallback_baseline"

    probe_graph = nx.DiGraph()
    probe_graph.add_edge("api.routes", "core.user")
    probe_analysis = AnalysisStub(graph=probe_graph)
    probe_rules = [{"name": "_probe", "from": "api/*", "to": "core/*", "type": "forbidden"}]
    try:
        check_constraints_baseline(probe_analysis, probe_rules)
        return check_constraints_baseline, "experiments.exp4_constraints.run::check_constraints"
    except NameError:
        if mode == "exp4":
            raise RuntimeError("Baseline exp4 checker is not callable in current workspace") from None
        return check_constraints_legacy, "legacy_fallback_baseline"


def parse_cases(raw: str) -> List[Case]:
    cases: List[Case] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        parts = token.split(":")
        if len(parts) != 3:
            raise ValueError(f"Bad case format: {token}. Expected nodes:edges:rules")
        n, e, r = (int(parts[0]), int(parts[1]), int(parts[2]))
        cases.append(Case(nodes=n, edges=e, rules=r))
    if not cases:
        raise ValueError("At least one benchmark case is required")
    return cases


def build_graph(n_nodes: int, n_edges: int, seed: int) -> nx.DiGraph:
    rng = random.Random(seed)
    g = nx.DiGraph()

    packages = ["api", "app", "core", "domain", "infra", "services", "shared", "util"]
    modules = [f"{packages[i % len(packages)]}.m{i}" for i in range(n_nodes)]
    g.add_nodes_from(modules)

    max_edges = n_nodes * max(0, n_nodes - 1)
    target = min(n_edges, max_edges)

    seen = set()
    while len(seen) < target:
        src_idx = rng.randrange(n_nodes)
        tgt_idx = rng.randrange(n_nodes)
        if src_idx == tgt_idx:
            continue
        edge = (modules[src_idx], modules[tgt_idx])
        if edge in seen:
            continue
        seen.add(edge)
        g.add_edge(*edge)
    return g


def build_rules(n_rules: int, seed: int) -> List[dict]:
    rng = random.Random(seed)
    package_pool = ["api", "app", "core", "domain", "infra", "services", "shared", "util"]

    rules: List[dict] = []
    for i in range(n_rules):
        src = rng.choice(package_pool)
        dst = rng.choice(package_pool)

        # Mix narrow and broad patterns to avoid biased benchmark.
        mode = i % 5
        if mode == 0:
            from_pattern = f"{src}/*"
            to_pattern = f"{dst}/*"
        elif mode == 1:
            from_pattern = f"{src}/m*"
            to_pattern = f"{dst}/m*"
        elif mode == 2:
            from_pattern = "*/m*"
            to_pattern = f"{dst}/*"
        elif mode == 3:
            from_pattern = f"{src}/*"
            to_pattern = "*/m*"
        else:
            from_pattern = "*/*"
            to_pattern = f"{dst}/*"

        rules.append(
            {
                "name": f"rule_{i}",
                "from": from_pattern,
                "to": to_pattern,
                "type": "forbidden",
            }
        )
    return rules


def normalize_violations(violations: Sequence[dict]) -> List[Tuple[str, str, str, str, str]]:
    norm = []
    for v in violations:
        rule = v["rule"]
        norm.append(
            (
                v["source"],
                v["target"],
                rule.get("name", ""),
                rule.get("from", ""),
                rule.get("to", ""),
            )
        )
    return sorted(norm)


def constraint_score(total_edges: int, violations_count: int) -> float:
    if total_edges == 0:
        return 1.0
    return max(0.0, 1.0 - violations_count / total_edges)


def median(values: Sequence[float]) -> float:
    return statistics.median(values) if values else 0.0


def p95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(0.95 * (len(sorted_vals) - 1))
    return sorted_vals[idx]


def run_case(case: Case, repeats: int, seed: int, baseline_checker) -> dict:
    graph = build_graph(case.nodes, case.edges, seed=seed)
    rules = build_rules(case.rules, seed=seed + 1)
    analysis = AnalysisStub(graph=graph)

    # Correctness gate before perf: both methods must produce same violations.
    baseline_v = baseline_checker(analysis, rules)
    optimized_v = check_constraints_optimized(analysis, rules)
    baseline_n = normalize_violations(baseline_v)
    optimized_n = normalize_violations(optimized_v)

    if baseline_n != optimized_n:
        raise AssertionError(
            "Violation mismatch between baseline and optimized implementations"
        )

    total_edges = graph.number_of_edges()
    baseline_score = constraint_score(total_edges, len(baseline_v))
    optimized_score = constraint_score(total_edges, len(optimized_v))
    if abs(baseline_score - optimized_score) > 1e-12:
        raise AssertionError("Constraint score mismatch between methods")

    # Warmup
    baseline_checker(analysis, rules)
    check_constraints_optimized(analysis, rules)

    baseline_times: List[float] = []
    optimized_times: List[float] = []
    for i in range(repeats):
        if i % 2 == 0:
            t0 = time.perf_counter()
            baseline_checker(analysis, rules)
            baseline_times.append(time.perf_counter() - t0)

            t1 = time.perf_counter()
            check_constraints_optimized(analysis, rules)
            optimized_times.append(time.perf_counter() - t1)
        else:
            t0 = time.perf_counter()
            check_constraints_optimized(analysis, rules)
            optimized_times.append(time.perf_counter() - t0)

            t1 = time.perf_counter()
            baseline_checker(analysis, rules)
            baseline_times.append(time.perf_counter() - t1)

    b_med = median(baseline_times)
    o_med = median(optimized_times)
    speedup = (b_med / o_med) if o_med > 0 else float("inf")

    return {
        "nodes": case.nodes,
        "edges": total_edges,
        "rules": len(rules),
        "violations": len(baseline_v),
        "score": baseline_score,
        "baseline_median_s": b_med,
        "optimized_median_s": o_med,
        "baseline_p95_s": p95(baseline_times),
        "optimized_p95_s": p95(optimized_times),
        "speedup_x": speedup,
    }


def print_header() -> None:
    print(
        "case".ljust(18)
        + "edges".rjust(10)
        + "rules".rjust(8)
        + "viol".rjust(8)
        + "base_med".rjust(12)
        + "opt_med".rjust(12)
        + "speedup".rjust(10)
    )
    print("-" * 78)


def print_row(label: str, result: dict) -> None:
    print(
        label.ljust(18)
        + str(result["edges"]).rjust(10)
        + str(result["rules"]).rjust(8)
        + str(result["violations"]).rjust(8)
        + f"{result['baseline_median_s']:.6f}".rjust(12)
        + f"{result['optimized_median_s']:.6f}".rjust(12)
        + f"{result['speedup_x']:.2f}x".rjust(10)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark baseline vs optimized constraints checker")
    parser.add_argument(
        "--cases",
        default="300:3000:40,1200:15000:80,2500:40000:120",
        help="Comma-separated benchmark cases: nodes:edges:rules",
    )
    parser.add_argument("--repeats", type=int, default=15, help="Timing repeats per case")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic generation")
    parser.add_argument(
        "--baseline-mode",
        choices=["auto", "exp4", "legacy"],
        default="auto",
        help="Which baseline checker to use",
    )
    args = parser.parse_args()

    baseline_checker, baseline_name = resolve_baseline_checker(args.baseline_mode)
    cases = parse_cases(args.cases)
    print(f"Benchmark seed={args.seed}, repeats={args.repeats}")
    print(f"Baseline checker: {baseline_name}")
    print("Correctness mode: strict equality of violation set and score")
    print_header()

    all_results = []
    for i, case in enumerate(cases):
        result = run_case(case, repeats=args.repeats, seed=args.seed + i * 101, baseline_checker=baseline_checker)
        label = f"{case.nodes}n:{case.edges}e:{case.rules}r"
        print_row(label, result)
        all_results.append(result)

    med_speedup = median([r["speedup_x"] for r in all_results])
    print("-" * 78)
    print(f"Median speedup across cases: {med_speedup:.2f}x")


if __name__ == "__main__":
    main()
