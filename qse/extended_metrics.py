"""
Extended metrics computed on the dependency graph exported by Rust scanner.

Provides CCD, Indirect Coupling, and per-module breakdown using the full
graph (internal + external nodes) from scan_to_graph_json.

Usage:
    from qse.extended_metrics import compute_extended_metrics
    result = compute_extended_metrics("/path/to/repo")
"""
from __future__ import annotations

import json
from typing import Dict, Optional

import networkx as nx


def _build_graph(graph_json: str) -> nx.DiGraph:
    """Build nx.DiGraph from Rust scanner JSON output."""
    data = json.loads(graph_json)
    G = nx.DiGraph()
    for n in data["nodes"]:
        G.add_node(n["id"], file=n.get("internal", False))
    for src, tgt in data["edges"]:
        G.add_edge(src, tgt)
    return G


def compute_extended_metrics(repo_path: str) -> Optional[Dict]:
    """Compute CCD, IC, per-module metrics using Rust scanner graph.

    Returns None if Rust scanner not available.
    """
    try:
        from _qse_core import scan_to_graph_json
    except ImportError:
        return None

    graph_json = scan_to_graph_json(repo_path)
    G = _build_graph(graph_json)

    internal = [n for n, d in G.nodes(data=True) if d.get("file")]
    if not internal:
        return None

    # --- CCD ---
    ccd = _compute_ccd(G, internal)

    # --- Indirect Coupling ---
    ic = _compute_ic(G, internal)

    # --- Per-module ---
    pm = _compute_per_module(G, internal)

    return {
        "ccd": ccd,
        "indirect_coupling": ic,
        "per_module": pm,
    }


def _compute_ccd(G: nx.DiGraph, internal: list) -> Dict:
    """CCD on internal nodes using full graph reachability."""
    import math
    n = len(internal)
    if n <= 1:
        return {"ccd_raw": 0, "ccd_norm": 0.0, "avg_reachable": 0.0}

    # For large graphs, sample
    sample = internal
    if n > 2000:
        import random
        random.seed(42)
        sample = random.sample(internal, 500)

    total = 0
    for node in sample:
        reachable = nx.descendants(G, node)
        # Count only internal reachable nodes
        internal_reachable = sum(1 for r in reachable if G.nodes[r].get("file"))
        total += internal_reachable + 1  # +1 for self

    if len(sample) < n:
        total = int(total * n / len(sample))

    ccd_tree = n * math.log2(n + 1) if n > 1 else 1
    ccd_norm = min(total / ccd_tree, 10.0) if ccd_tree > 0 else 0.0

    return {
        "ccd_raw": total,
        "ccd_norm": round(ccd_norm, 4),
        "avg_reachable": round(total / n, 2),
    }


def _compute_ic(G: nx.DiGraph, internal: list) -> Dict:
    """Indirect coupling: ESM on outgoing edges from internal nodes.

    For two internal nodes u, v: if they import many of the same external
    modules, they are indirectly coupled (shared dependencies).
    """
    internal_set = set(internal)

    # Build dependency profile per internal node: set of successors (imports)
    profiles = {}
    for node in internal:
        profiles[node] = set(G.successors(node))

    # Compute pairwise ESM between internal nodes that share dependencies
    esm_values = []
    internal_list = list(internal_set)
    n = len(internal_list)

    # For large graphs, sample pairs
    import random
    random.seed(42)
    if n > 200:
        pairs = [(random.choice(internal_list), random.choice(internal_list))
                 for _ in range(10000)]
    else:
        pairs = [(internal_list[i], internal_list[j])
                 for i in range(n) for j in range(i + 1, n)]

    for u, v in pairs:
        if u == v:
            continue
        pu, pv = profiles.get(u, set()), profiles.get(v, set())
        if not pu and not pv:
            continue
        union = pu | pv
        if not union:
            continue
        intersection = pu & pv
        esm = len(intersection) / len(union)
        if esm > 0:
            esm_values.append(esm)

    if not esm_values:
        return {"mean_ic": 0.0, "max_ic": 0.0, "ic_above_05": 0.0, "n_coupled_pairs": 0}

    return {
        "mean_ic": round(sum(esm_values) / len(esm_values), 4),
        "max_ic": round(max(esm_values), 4),
        "ic_above_05": round(sum(1 for v in esm_values if v > 0.5) / len(esm_values), 4),
        "n_coupled_pairs": len(esm_values),
    }


def _compute_per_module(G: nx.DiGraph, internal: list) -> Dict:
    """Per-module fan-in, fan-out, instability, SCC membership."""
    import statistics as _stats

    internal_set = set(internal)

    # SCC on internal subgraph
    subgraph = G.subgraph(internal)
    scc_nodes = set()
    for scc in nx.strongly_connected_components(subgraph):
        if len(scc) > 1:
            scc_nodes.update(scc)

    modules = []
    fan_ins, fan_outs = [], []

    for node in internal:
        fi = G.in_degree(node)
        fo = G.out_degree(node)
        instability = fo / (fi + fo) if (fi + fo) > 0 else 0.5

        fan_ins.append(fi)
        fan_outs.append(fo)
        modules.append({
            "name": node,
            "fan_in": fi,
            "fan_out": fo,
            "instability": round(instability, 3),
            "in_scc": node in scc_nodes,
        })

    modules.sort(key=lambda m: -m["fan_out"])

    summary = {
        "n_modules": len(internal),
        "avg_fan_in": round(sum(fan_ins) / len(fan_ins), 2) if fan_ins else 0,
        "max_fan_in": max(fan_ins) if fan_ins else 0,
        "avg_fan_out": round(sum(fan_outs) / len(fan_outs), 2) if fan_outs else 0,
        "max_fan_out": max(fan_outs) if fan_outs else 0,
        "fan_out_std": round(_stats.stdev(fan_outs), 3) if len(fan_outs) > 1 else 0,
        "n_in_scc": len(scc_nodes),
        "scc_fraction": round(len(scc_nodes) / len(internal), 4) if internal else 0,
    }

    return {
        "summary": summary,
        "modules": modules[:50],
        "scc_modules": sorted(scc_nodes),
    }
