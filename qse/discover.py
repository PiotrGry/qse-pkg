"""
Auto-discovery of architectural boundaries from dependency graphs.

Analyzes an existing graph to propose constraints (forbidden edges)
based on detected clusters, directional patterns, and isolation.
No manual configuration needed — rules are inferred from code structure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx


@dataclass
class ProposedRule:
    """A proposed architectural constraint with confidence and rationale."""
    type: str               # "forbidden" | "direction"
    from_pattern: str       # glob pattern for source
    to_pattern: str         # glob pattern for target
    confidence: float       # [0, 1] — how certain we are this should be a rule
    rationale: str          # human-readable explanation
    evidence: Dict          # supporting data (edge counts, cluster info)

    def to_constraint(self) -> dict:
        """Convert to QSE constraint format."""
        return {
            "type": "forbidden",
            "from": self.from_pattern,
            "to": self.to_pattern,
            "_confidence": round(self.confidence, 2),
            "_rationale": self.rationale,
        }


@dataclass
class DiscoveryReport:
    """Result of auto-discovery analysis."""
    clusters: List[Dict]           # detected module clusters
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


def _cluster_label(members: Set[str]) -> str:
    """Derive a human-readable label for a cluster from its member names."""
    if not members:
        return "unknown"
    # Use common prefix of top-level package names
    roots = set()
    for m in members:
        parts = m.split(".")
        roots.add(parts[0])
    if len(roots) == 1:
        return roots.pop()
    # Multiple roots — use the most frequent
    from collections import Counter
    root_counts = Counter()
    for m in members:
        root_counts[m.split(".")[0]] += 1
    return root_counts.most_common(1)[0][0]


def _glob_pattern(cluster_label: str) -> str:
    """Create a glob pattern for a cluster."""
    return f"{cluster_label}/*"


def detect_clusters(graph: nx.DiGraph,
                    min_cluster_size: int = 2) -> List[Dict]:
    """Detect module clusters using Louvain community detection.

    Returns list of dicts with 'label', 'members', 'size'.
    """
    if graph.number_of_nodes() <= 1:
        return []

    U = graph.to_undirected()
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
        clusters.append({
            "label": label,
            "members": sorted(community),
            "size": len(community),
        })

    return sorted(clusters, key=lambda c: c["size"], reverse=True)


def _count_cross_edges(graph: nx.DiGraph,
                       from_set: Set[str],
                       to_set: Set[str]) -> int:
    """Count directed edges from from_set to to_set."""
    count = 0
    for src, tgt in graph.edges():
        if src in from_set and tgt in to_set:
            count += 1
    return count


def _infer_direction_confidence(edges_a_to_b: int,
                                edges_b_to_a: int) -> Tuple[float, str]:
    """Infer whether there's a dominant direction between two clusters.

    Returns (confidence, direction) where direction is "a_to_b", "b_to_a",
    "bidirectional", or "isolated".
    """
    total = edges_a_to_b + edges_b_to_a
    if total == 0:
        return 0.9, "isolated"

    if edges_a_to_b > 0 and edges_b_to_a == 0:
        return 0.85, "a_to_b"
    if edges_b_to_a > 0 and edges_a_to_b == 0:
        return 0.85, "b_to_a"

    # Both directions exist — check dominance ratio
    ratio = max(edges_a_to_b, edges_b_to_a) / total
    if ratio >= 0.9:
        direction = "a_to_b" if edges_a_to_b > edges_b_to_a else "b_to_a"
        return 0.6, direction
    return 0.3, "bidirectional"


def discover_policies(graph: nx.DiGraph,
                      min_confidence: float = 0.5,
                      min_cluster_size: int = 2) -> DiscoveryReport:
    """Auto-discover architectural boundaries and propose constraints.

    Analyzes the dependency graph to find:
    1. Module clusters (Louvain community detection)
    2. Isolated cluster pairs (no edges between them → forbidden both ways)
    3. Directional patterns (A→B but never B→A → forbidden reverse direction)
    4. Layering hints (topological ordering suggests layer structure)

    Returns a DiscoveryReport with proposed rules and confidence scores.
    """
    clusters = detect_clusters(graph, min_cluster_size)
    proposed: List[ProposedRule] = []

    if len(clusters) < 2:
        return DiscoveryReport(
            clusters=clusters,
            proposed_rules=[],
            graph_summary={
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "clusters_found": len(clusters),
            },
        )

    # Analyze every pair of clusters
    for i, j in combinations(range(len(clusters)), 2):
        ca = clusters[i]
        cb = clusters[j]
        members_a = set(ca["members"])
        members_b = set(cb["members"])

        edges_a_to_b = _count_cross_edges(graph, members_a, members_b)
        edges_b_to_a = _count_cross_edges(graph, members_b, members_a)

        confidence, direction = _infer_direction_confidence(
            edges_a_to_b, edges_b_to_a
        )

        if confidence < min_confidence:
            continue

        pat_a = _glob_pattern(ca["label"])
        pat_b = _glob_pattern(cb["label"])

        evidence = {
            "edges_a_to_b": edges_a_to_b,
            "edges_b_to_a": edges_b_to_a,
            "cluster_a_size": ca["size"],
            "cluster_b_size": cb["size"],
        }

        if direction == "isolated":
            # No connections → propose forbidden both ways
            proposed.append(ProposedRule(
                type="forbidden",
                from_pattern=pat_a,
                to_pattern=pat_b,
                confidence=confidence,
                rationale=(f"No dependencies exist between '{ca['label']}' and "
                           f"'{cb['label']}' — they appear to be independent boundaries."),
                evidence=evidence,
            ))
            proposed.append(ProposedRule(
                type="forbidden",
                from_pattern=pat_b,
                to_pattern=pat_a,
                confidence=confidence,
                rationale=(f"No dependencies exist between '{cb['label']}' and "
                           f"'{ca['label']}' — they appear to be independent boundaries."),
                evidence=evidence,
            ))

        elif direction == "a_to_b":
            # A→B only → forbid B→A (preserve layering)
            proposed.append(ProposedRule(
                type="forbidden",
                from_pattern=pat_b,
                to_pattern=pat_a,
                confidence=confidence,
                rationale=(f"'{ca['label']}' depends on '{cb['label']}' "
                           f"({edges_a_to_b} edges) but never the reverse — "
                           f"this appears to be a directional boundary."),
                evidence=evidence,
            ))

        elif direction == "b_to_a":
            # B→A only → forbid A→B
            proposed.append(ProposedRule(
                type="forbidden",
                from_pattern=pat_a,
                to_pattern=pat_b,
                confidence=confidence,
                rationale=(f"'{cb['label']}' depends on '{ca['label']}' "
                           f"({edges_b_to_a} edges) but never the reverse — "
                           f"this appears to be a directional boundary."),
                evidence=evidence,
            ))

    # Sort by confidence (highest first)
    proposed.sort(key=lambda r: r.confidence, reverse=True)

    return DiscoveryReport(
        clusters=clusters,
        proposed_rules=proposed,
        graph_summary={
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "clusters_found": len(clusters),
            "rules_proposed": len(proposed),
            "high_confidence_rules": sum(
                1 for r in proposed if r.confidence >= 0.7
            ),
        },
    )
