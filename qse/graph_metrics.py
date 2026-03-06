"""
AGQ Graph Metrics — architecture-agnostic, Level 1.

Modularity (Q):  Newman's modularity via Louvain on import graph
Acyclicity (A):  1 - (nodes_in_cycles / total_nodes) via Tarjan SCC
Stability (St):  1 - mean(|Abstractness + Instability - 1|) per module (Martin)
Cohesion (Co):   1 - mean(LCOM4) per class (connected components in method-attribute graph)

All metrics normalized to [0, 1] where 1 = best.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx


@dataclass
class AGQMetrics:
    """Architecture Graph Quality metrics."""
    modularity: float    # Newman's Q normalized to [0,1]
    acyclicity: float    # 1 - fraction of nodes in cycles
    stability: float     # 1 - mean distance from main sequence
    cohesion: float      # 1 - mean(LCOM4 - 1) / max_lcom4

    @property
    def agq_score(self) -> float:
        """Equal-weight composite. Override weights via compute_agq()."""
        return (self.modularity + self.acyclicity + self.stability + self.cohesion) / 4


# ---------------------------------------------------------------------------
# Modularity — Newman's Q via Louvain
# ---------------------------------------------------------------------------

def compute_modularity(G: nx.DiGraph) -> float:
    """
    Newman's modularity Q on the undirected projection of import graph.
    Uses Louvain community detection (networkx >= 3.x).

    Q in [-0.5, 1.0], we normalize to [0, 1] via (Q + 0.5) / 1.5.
    Single-node or empty graph returns 1.0 (trivially modular).
    """
    if G.number_of_nodes() <= 1:
        return 1.0

    U = G.to_undirected()
    # Remove self-loops
    U.remove_edges_from(nx.selfloop_edges(U))

    if U.number_of_edges() == 0:
        return 1.0  # No dependencies = each module is its own community

    try:
        communities = nx.community.louvain_communities(U, seed=42)
        Q = nx.community.modularity(U, communities)
    except Exception:
        return 0.5  # Fallback if algo fails

    # Normalize from [-0.5, 1.0] to [0, 1]
    return max(0.0, min(1.0, (Q + 0.5) / 1.5))


# ---------------------------------------------------------------------------
# Acyclicity — Tarjan SCC
# ---------------------------------------------------------------------------

def compute_acyclicity(G: nx.DiGraph) -> float:
    """
    Fraction of nodes NOT participating in any cycle.

    A = 1 - (nodes_in_cycles / total_nodes)

    Uses Tarjan's SCC: any SCC with size > 1 contains a cycle.
    Empty/single-node graph returns 1.0.
    """
    n = G.number_of_nodes()
    if n <= 1:
        return 1.0

    nodes_in_cycles = 0
    for scc in nx.strongly_connected_components(G):
        if len(scc) > 1:
            nodes_in_cycles += len(scc)

    return 1.0 - (nodes_in_cycles / n)


# ---------------------------------------------------------------------------
# Stability — Martin's Distance from Main Sequence
# ---------------------------------------------------------------------------

def compute_stability(G: nx.DiGraph,
                      abstract_modules: Optional[Set[str]] = None) -> float:
    """
    Mean distance from main sequence per package (second-level grouping).

    For each package:
      Ca = afferent coupling (in-degree from outside package)
      Ce = efferent coupling (out-degree to outside package)
      I  = Ce / (Ca + Ce)                    # Instability [0,1]
      A  = abstract_members / total_members  # Abstractness [0,1]
      D  = |A + I - 1|                       # Distance from main sequence

    Stability = 1 - mean(D)

    abstract_modules: set of node names containing abstract classes (ABC, Protocol, etc.)
    If None, A=0 for all — this PENALIZES stable interfaces (D=1.0 for stable+concrete).
    """
    if abstract_modules is None:
        abstract_modules = set()

    nodes = list(G.nodes())
    if not nodes:
        return 1.0

    # Group by second-level package for finer granularity
    # e.g. "core.user" → "core", "services.order_service" → "services"
    # For single-segment names, use the name itself
    packages: Dict[str, List[str]] = {}
    for node in nodes:
        parts = node.split(".")
        # Use up to 2 levels for grouping: "a.b.c" → "a.b", "a" → "a"
        pkg = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
        packages.setdefault(pkg, []).append(node)

    distances = []
    for pkg, members in packages.items():
        member_set = set(members)

        # Ca and Ce for package (external edges only)
        ca = 0
        ce = 0
        for m in members:
            for pred in G.predecessors(m):
                if pred not in member_set:
                    ca += 1
            for succ in G.successors(m):
                if succ not in member_set:
                    ce += 1

        total_coupling = ca + ce
        I = ce / total_coupling if total_coupling > 0 else 0.5

        n_abstract = sum(1 for m in members if m in abstract_modules)
        A = n_abstract / len(members) if members else 0.0

        D = abs(A + I - 1.0)
        distances.append(D)

    if not distances:
        return 1.0

    return 1.0 - (sum(distances) / len(distances))


def compute_instability_variance(G: nx.DiGraph) -> float:
    """
    Variance of per-node instability I = Ce / (Ca + Ce).

    High coupling (all nodes import everything) → all I ≈ 0.5 → low variance.
    Clean layered code → leaf nodes I=1.0, core I=0.0 → high variance.

    Returns 1 - var (so higher = better differentiation = healthier).
    """
    nodes = list(G.nodes())
    if len(nodes) <= 1:
        return 1.0

    instabilities = []
    for n in nodes:
        ca = G.in_degree(n)
        ce = G.out_degree(n)
        total = ca + ce
        I = ce / total if total > 0 else 0.5
        instabilities.append(I)

    mean = sum(instabilities) / len(instabilities)
    var = sum((i - mean) ** 2 for i in instabilities) / len(instabilities)
    # Normalize: max possible var for [0,1] values is 0.25
    return min(1.0, var / 0.25)  # Higher = more differentiated = better


# ---------------------------------------------------------------------------
# Cohesion — LCOM4
# ---------------------------------------------------------------------------

def compute_lcom4(methods_attrs: List[Tuple[str, Set[str]]]) -> int:
    """
    LCOM4: number of connected components in method-attribute bipartite graph.

    methods_attrs: [(method_name, {attr1, attr2, ...}), ...]

    LCOM4 = 1 means perfectly cohesive.
    LCOM4 > 1 means class should be split.
    """
    if not methods_attrs:
        return 1

    # Build undirected graph: methods connected if they share attributes
    method_graph = nx.Graph()
    method_names = [m for m, _ in methods_attrs]
    method_graph.add_nodes_from(method_names)

    for i, (m1, attrs1) in enumerate(methods_attrs):
        for j, (m2, attrs2) in enumerate(methods_attrs):
            if i < j and attrs1 & attrs2:
                method_graph.add_edge(m1, m2)

    return nx.number_connected_components(method_graph)


def compute_cohesion(classes_lcom4: List[int]) -> float:
    """
    Cohesion = 1 - mean(penalty) where penalty = (LCOM4 - 1) / n_methods.

    LCOM4=1 is ideal. LCOM4=n_methods is worst (every method is isolated).
    Uses absolute normalization: penalty per class = (LCOM4-1) / max(LCOM4-1, 1)
    capped at 1.0, so a god class with LCOM4=15 gets penalty=1.0.

    This avoids the relative-to-max problem where 1 god class + 99 good classes
    would look fine because only the god class hits penalty=1.0.
    """
    if not classes_lcom4:
        return 1.0

    penalties = []
    for lcom in classes_lcom4:
        excess = max(0, lcom - 1)
        # Penalty: 0 for LCOM4=1, ramps to 1.0 at LCOM4=5+
        # Using sigmoid-like: min(1, excess / 4) gives linear ramp, cap at 4 components
        penalty = min(1.0, excess / 4.0)
        penalties.append(penalty)

    if not penalties:
        return 1.0

    return 1.0 - (sum(penalties) / len(penalties))


# ---------------------------------------------------------------------------
# Composite
# ---------------------------------------------------------------------------

def compute_agq(G: nx.DiGraph,
                abstract_modules: Optional[Set[str]] = None,
                classes_lcom4: Optional[List[int]] = None,
                weights: Tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25)
                ) -> AGQMetrics:
    """Compute all AGQ metrics."""
    mod = compute_modularity(G)
    acy = compute_acyclicity(G)
    stab = compute_stability(G, abstract_modules)
    coh = compute_cohesion(classes_lcom4 or [])

    return AGQMetrics(
        modularity=mod,
        acyclicity=acy,
        stability=stab,
        cohesion=coh,
    )
