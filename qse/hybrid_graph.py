"""
Merge static and dynamic edges into a unified hybrid dependency graph G.

G = S ∪ D where S = static edges, D = dynamic edges.
Each edge is annotated with its source: 'static', 'dynamic', or 'both'.
"""

import networkx as nx

from qse.scanner import StaticAnalysis
from qse.tracer import TraceResult


def build_hybrid_graph(static: StaticAnalysis, dynamic: TraceResult) -> nx.DiGraph:
    """
    Merge static import graph with dynamically discovered edges.

    Returns a new DiGraph where:
    - All static nodes/edges are preserved with edge attr source='static'
    - Dynamic edges are added with source='dynamic'
    - Edges present in both get source='both'
    """
    G = static.graph.copy()

    # Tag existing edges as static
    for u, v in G.edges():
        G.edges[u, v]["source"] = "static"

    # Merge dynamic edges
    for u, v in dynamic.dynamic_edges:
        if G.has_edge(u, v):
            G.edges[u, v]["source"] = "both"
        else:
            G.add_edge(u, v, source="dynamic")
            # Infer layer from module path for new nodes (e.g., "domain.order" → "domain")
            for node in (u, v):
                if "layer" not in G.nodes.get(node, {}):
                    parts = node.split(".")
                    if parts[0] in ("domain", "application", "infrastructure", "presentation"):
                        G.nodes[node]["layer"] = parts[0]

    return G


def graph_stats(G: nx.DiGraph) -> dict:
    """Summary statistics of the hybrid graph."""
    static_edges = sum(1 for _, _, d in G.edges(data=True) if d.get("source") == "static")
    dynamic_edges = sum(1 for _, _, d in G.edges(data=True) if d.get("source") == "dynamic")
    both_edges = sum(1 for _, _, d in G.edges(data=True) if d.get("source") == "both")
    return {
        "nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "static_only_edges": static_edges,
        "dynamic_only_edges": dynamic_edges,
        "both_edges": both_edges,
    }
