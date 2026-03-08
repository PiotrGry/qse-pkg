"""
Auto-discovery of architectural boundaries from dependency graphs.

Analyzes an existing graph to propose constraints (forbidden edges)
based on detected clusters, directional patterns, and isolation.
No manual configuration needed — rules are inferred from code structure.

Fixes vs v1:
  1. Filters internal nodes only (removes stdlib/test/external noise)
  2. Smarter cluster labeling — uses longest common prefix, not just root
  3. Directional rules forbid the REVERSE of the observed direction
     (A→B means B should never import A, not the other way)
  4. Deduplicates rules with same from/to pattern
  5. Skips self-referential rules (same label on both sides)
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx


_TEST_RE = re.compile(r"(^|\.)tests?(\.|$)|test_|_test$", re.IGNORECASE)


@dataclass
class ProposedRule:
    """A proposed architectural constraint with confidence and rationale."""
    type: str
    from_pattern: str
    to_pattern: str
    confidence: float
    rationale: str
    evidence: Dict

    def to_constraint(self) -> dict:
        return {
            "type": "forbidden",
            "from": self.from_pattern,
            "to": self.to_pattern,
            "_confidence": round(self.confidence, 2),
            "_rationale": self.rationale,
        }


@dataclass
class DiscoveryReport:
    clusters: List[Dict]
    proposed_rules: List[ProposedRule]
    graph_summary: Dict

    def to_dict(self) -> dict:
        return {
            "clusters": self.clusters,
            "proposed_rules": [
                {
                    "type": r.type,
                    "from": r.from_pattern,
                    "to": r.to_pattern,
                    "confidence": round(r.confidence, 2),
                    "rationale": r.rationale,
                    "evidence": r.evidence,
                }
                for r in self.proposed_rules
            ],
            "graph_summary": self.graph_summary,
            "constraints": [r.to_constraint() for r in self.proposed_rules
                            if r.confidence >= 0.7],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def discover_multilang(repo_path: str, **kwargs) -> "DiscoveryReport":
    """Run discover on any language repo using Rust qse-core scanner.

    Supports Python, Java (Maven/Gradle), and Go repositories.
    Falls back to Python scanner if Rust scanner not available.

    Args:
        repo_path: path to repository root
        **kwargs: passed to discover_policies (min_confidence, min_cluster_size)
    """
    try:
        import json as _json
        import networkx as _nx
        from _qse_core import scan_to_graph_json
        raw = scan_to_graph_json(repo_path)
        data = _json.loads(raw)
        G = _nx.DiGraph()
        for node in data["nodes"]:
            G.add_node(node["id"], internal=node["internal"])
        for src, tgt in data["edges"]:
            G.add_edge(src, tgt)
        return discover_policies(G, **kwargs)
    except ImportError:
        # Fallback: Python scanner (Python only)
        from qse.scanner import scan_repo
        analysis = scan_repo(repo_path)
        return discover_policies(analysis.graph, **kwargs)


# ---------------------------------------------------------------------------
# Internal graph filtering
# ---------------------------------------------------------------------------

def _filter_internal(graph: nx.DiGraph) -> nx.DiGraph:
    """Keep only internal nodes (have 'file' attr) + their direct targets.

    Removes stdlib, third-party, test modules from clustering.
    If no 'file' attrs present, filters test modules by name pattern.
    """
    has_file_attrs = any(d.get("file") for _, d in graph.nodes(data=True))

    if has_file_attrs:
        internal = {n for n, d in graph.nodes(data=True) if d.get("file")}
    else:
        # Fallback: detect the dominant top-level package(s) in the graph
        # and keep only nodes belonging to them.
        # e.g. scrapy graph → dominant root = "scrapy" (most nodes)
        root_counts = Counter(n.split(".")[0] for n in graph.nodes() if "." in n)
        if root_counts:
            # Keep top-1 or top-2 roots that together cover >60% of nodes
            total = sum(root_counts.values())
            dominant_roots: Set[str] = set()
            covered = 0
            for root, cnt in root_counts.most_common():
                dominant_roots.add(root)
                covered += cnt
                if covered / total >= 0.6:
                    break
            internal = {n for n in graph.nodes()
                        if n.split(".")[0] in dominant_roots
                        and not _TEST_RE.search(n)}
        else:
            internal = {n for n in graph.nodes()
                        if not _TEST_RE.search(n)
                        and n.split(".")[0] not in _STDLIB_ROOTS}

    # Keep internal nodes + their direct import targets
    connected: Set[str] = set(internal)
    for src, tgt in graph.edges():
        if src in internal:
            connected.add(tgt)

    return graph.subgraph(connected).copy()


# Common stdlib top-level modules to filter out
_STDLIB_ROOTS = {
    "os", "sys", "re", "io", "json", "time", "math", "abc", "ast",
    "typing", "collections", "itertools", "functools", "pathlib",
    "dataclasses", "enum", "copy", "hashlib", "logging", "threading",
    "subprocess", "importlib", "inspect", "warnings", "contextlib",
    "unittest", "pytest", "setuptools", "pkg_resources", "site",
    "email", "http", "urllib", "socket", "ssl", "struct", "ctypes",
    "argparse", "textwrap", "shutil", "tempfile", "glob", "fnmatch",
    "string", "random", "statistics", "decimal", "fractions",
}


# ---------------------------------------------------------------------------
# Cluster labeling
# ---------------------------------------------------------------------------

def _longest_common_prefix(strings: List[str]) -> str:
    """Find longest common dot-separated prefix."""
    if not strings:
        return ""
    parts_list = [s.split(".") for s in strings]
    common = []
    for level in zip(*parts_list):
        if len(set(level)) == 1:
            common.append(level[0])
        else:
            break
    return ".".join(common)


def _cluster_label(members: Set[str]) -> str:
    """Derive a meaningful label from cluster member names.

    Strategy:
    1. Find longest common prefix (e.g. 'scrapy.core' for scrapy.core.*)
    2. If prefix too short (just root), try second-level most common
    3. Fallback to most frequent root
    """
    if not members:
        return "unknown"

    member_list = sorted(members)
    prefix = _longest_common_prefix(member_list)

    # If prefix is meaningful (has at least 2 levels), use it
    if prefix and prefix.count(".") >= 1:
        return prefix

    # Prefix is just root (e.g. 'scrapy') — find most common second-level
    second_level = Counter()
    for m in members:
        parts = m.split(".")
        if len(parts) >= 2:
            second_level[f"{parts[0]}.{parts[1]}"] += 1
    if second_level and len(members) >= 5:
        top = second_level.most_common(1)[0]
        # Only use if it covers >40% of members in a large community
        if top[1] / len(members) > 0.4:
            return top[0]

    # Fallback to prefix or root
    if prefix:
        return prefix
    root_counts = Counter(m.split(".")[0] for m in members)
    return root_counts.most_common(1)[0][0]


def _glob_pattern(label: str) -> str:
    """Create glob pattern — label/* catches all sub-modules."""
    return f"{label}/*"


# ---------------------------------------------------------------------------
# Cluster detection
# ---------------------------------------------------------------------------

def _get_internal_nodes(graph: nx.DiGraph) -> Set[str]:
    """Return the set of truly internal source nodes."""
    has_file_attrs = any(d.get("file") for _, d in graph.nodes(data=True))
    if has_file_attrs:
        return {n for n, d in graph.nodes(data=True) if d.get("file")}
    # Dominant roots heuristic
    root_counts = Counter(n.split(".")[0] for n in graph.nodes() if "." in n)
    if not root_counts:
        return set(graph.nodes())
    total = sum(root_counts.values())
    dominant: Set[str] = set()
    covered = 0
    for root, cnt in root_counts.most_common():
        dominant.add(root)
        covered += cnt
        if covered / total >= 0.6:
            break
    return {n for n in graph.nodes()
            if n.split(".")[0] in dominant
            and not _TEST_RE.search(n)}


def detect_clusters(graph: nx.DiGraph,
                    min_cluster_size: int = 3) -> List[Dict]:
    """Detect module clusters via Louvain on internal-only nodes."""
    internal_nodes = _get_internal_nodes(graph)
    # Run Louvain ONLY on internal nodes — not on external import targets
    g = graph.subgraph(internal_nodes).copy()

    if g.number_of_nodes() <= 1:
        return []

    U = g.to_undirected()
    U.remove_edges_from(nx.selfloop_edges(U))

    if U.number_of_edges() == 0:
        return []

    try:
        communities = nx.community.louvain_communities(U, seed=42)
    except Exception:
        return []

    clusters = []
    for community in communities:
        if len(community) < min_cluster_size:
            continue
        label = _cluster_label(community)
        if _TEST_RE.search(label):
            continue
        clusters.append({
            "label": label,
            "members": sorted(community),
            "size": len(community),
        })

    # Merge clusters with identical labels (Louvain can split same-prefix groups)
    merged: Dict[str, Dict] = {}
    for c in clusters:
        lbl = c["label"]
        if lbl in merged:
            merged[lbl]["members"].extend(c["members"])
            merged[lbl]["size"] += c["size"]
        else:
            merged[lbl] = {"label": lbl, "members": list(c["members"]), "size": c["size"]}

    result = list(merged.values())
    return sorted(result, key=lambda c: c["size"], reverse=True)


# ---------------------------------------------------------------------------
# Edge counting and direction inference
# ---------------------------------------------------------------------------

def _count_cross_edges(graph: nx.DiGraph,
                       from_set: Set[str],
                       to_set: Set[str]) -> int:
    count = 0
    for src, tgt in graph.edges():
        if src in from_set and tgt in to_set:
            count += 1
    return count


def _infer_direction_confidence(edges_a_to_b: int,
                                edges_b_to_a: int) -> Tuple[float, str]:
    total = edges_a_to_b + edges_b_to_a
    if total == 0:
        return 0.9, "isolated"
    if edges_a_to_b > 0 and edges_b_to_a == 0:
        return 0.85, "a_to_b"
    if edges_b_to_a > 0 and edges_a_to_b == 0:
        return 0.85, "b_to_a"
    ratio = max(edges_a_to_b, edges_b_to_a) / total
    if ratio >= 0.9:
        direction = "a_to_b" if edges_a_to_b > edges_b_to_a else "b_to_a"
        return 0.6, direction
    return 0.3, "bidirectional"


# ---------------------------------------------------------------------------
# Main discovery
# ---------------------------------------------------------------------------

def discover_policies(graph: nx.DiGraph,
                      min_confidence: float = 0.5,
                      min_cluster_size: int = 3) -> DiscoveryReport:
    """Auto-discover architectural boundaries and propose constraints.

    1. Filter to internal nodes only (remove stdlib/test/external noise)
    2. Detect clusters via Louvain with better labeling
    3. For isolated pairs → forbidden both ways
    4. For directional pairs (A→B) → forbid REVERSE (B→A)
       Rationale: A depends on B means B is more stable/core;
       forbidding B→A preserves the dependency hierarchy.
    5. Deduplicate rules with same pattern pair
    """
    clusters = detect_clusters(graph, min_cluster_size)
    proposed: List[ProposedRule] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    internal_nodes = _get_internal_nodes(graph)
    g_internal = graph.subgraph(internal_nodes).copy()

    if len(clusters) < 2:
        return DiscoveryReport(
            clusters=clusters,
            proposed_rules=[],
            graph_summary={
                "nodes": graph.number_of_nodes(),
                "internal_nodes": g_internal.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "clusters_found": len(clusters),
            },
        )

    for i, j in combinations(range(len(clusters)), 2):
        ca = clusters[i]
        cb = clusters[j]

        # Skip if same label (can happen after merging)
        if ca["label"] == cb["label"]:
            continue

        members_a = set(ca["members"])
        members_b = set(cb["members"])

        edges_a_to_b = _count_cross_edges(g_internal, members_a, members_b)
        edges_b_to_a = _count_cross_edges(g_internal, members_b, members_a)

        confidence, direction = _infer_direction_confidence(edges_a_to_b, edges_b_to_a)

        if confidence < min_confidence:
            continue

        pat_a = _glob_pattern(ca["label"])
        pat_b = _glob_pattern(cb["label"])

        evidence = {
            "edges_a_to_b": edges_a_to_b,
            "edges_b_to_a": edges_b_to_a,
            "cluster_a": ca["label"],
            "cluster_b": cb["label"],
            "cluster_a_size": ca["size"],
            "cluster_b_size": cb["size"],
        }

        def _add_rule(frm: str, to: str, conf: float, rationale: str) -> None:
            key = (frm, to)
            if key in seen_pairs or frm == to:
                return
            seen_pairs.add(key)
            proposed.append(ProposedRule(
                type="forbidden",
                from_pattern=frm,
                to_pattern=to,
                confidence=conf,
                rationale=rationale,
                evidence=evidence,
            ))

        if direction == "isolated":
            _add_rule(pat_a, pat_b, confidence,
                      f"No dependencies between '{ca['label']}' and '{cb['label']}' "
                      f"— they are independent boundaries.")
            _add_rule(pat_b, pat_a, confidence,
                      f"No dependencies between '{cb['label']}' and '{ca['label']}' "
                      f"— they are independent boundaries.")

        elif direction == "a_to_b":
            # A imports B → B is more stable/core → forbid B→A (reverse)
            _add_rule(pat_b, pat_a, confidence,
                      f"'{ca['label']}' depends on '{cb['label']}' ({edges_a_to_b} edges) "
                      f"but never reverse — '{cb['label']}' is a stable dependency of "
                      f"'{ca['label']}', forbidding reverse import preserves layering.")

        elif direction == "b_to_a":
            # B imports A → A is more stable → forbid A→B
            _add_rule(pat_a, pat_b, confidence,
                      f"'{cb['label']}' depends on '{ca['label']}' ({edges_b_to_a} edges) "
                      f"but never reverse — '{ca['label']}' is a stable dependency of "
                      f"'{cb['label']}', forbidding reverse import preserves layering.")

    proposed.sort(key=lambda r: r.confidence, reverse=True)

    return DiscoveryReport(
        clusters=clusters,
        proposed_rules=proposed,
        graph_summary={
            "nodes": graph.number_of_nodes(),
            "internal_nodes": g_internal.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "clusters_found": len(clusters),
            "rules_proposed": len(proposed),
            "high_confidence_rules": sum(1 for r in proposed if r.confidence >= 0.7),
        },
    )
