"""
AGQ Graph Metrics — architecture-agnostic, Level 1.

Modularity (Q):  Newman's modularity via Louvain on import graph
Acyclicity (A):  1 - (largest_SCC / internal_nodes) via Tarjan SCC
Stability (St):  package-level instability variance (layering quality)
Cohesion (Co):   1 - mean(LCOM4) per class (connected components in method-attribute graph)

Additional metrics:
  hierarchical_modularity: M-score inspired — density ratio within vs between
                           second-level packages. Fixes leaf-module size bias
                           in Newman Q (Pisch et al. ESEM 2024).
  boundary_crossing_ratio: fraction of cross-package edges vs total internal edges.
                           Architecturally grounded coupling measure.

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
        """Weighted composite. Weights set by compute_agq(); defaults to equal."""
        w = getattr(self, "_weights", (0.25, 0.25, 0.25, 0.25))
        return (w[0] * self.modularity + w[1] * self.acyclicity +
                w[2] * self.stability + w[3] * self.cohesion)


# ---------------------------------------------------------------------------
# Modularity — Newman's Q via Louvain
# ---------------------------------------------------------------------------

def compute_modularity(G: nx.DiGraph) -> float:
    """
    Newman's modularity Q on the undirected projection of import graph.
    Uses Louvain community detection (networkx >= 3.x).

    Normalization: max(0, Q) / Q_REF where Q_REF = 0.75.
    Empirically, real codebases rarely exceed Q=0.75 (OSS-80 max ≈ 0.80).
    Negative Q (anti-structure) maps to 0.0.
    Q=0 (no community structure) maps to 0.0.
    Q=0.75 (strong modular structure) maps to 1.0.

    Graphs with fewer than 10 nodes return 0.5 (neutral): Louvain is
    unreliable on tiny graphs and always produces Q≈0 regardless of
    structure, which would unfairly penalize small focused libraries.
    """
    n = G.number_of_nodes()
    if n <= 1:
        return 1.0
    U = G.to_undirected()
    U.remove_edges_from(nx.selfloop_edges(U))

    if U.number_of_edges() == 0:
        return 1.0  # No dependencies = each module is its own community

    if n < 10:
        return 0.5  # Too small for reliable community detection (Louvain unreliable)

    try:
        communities = nx.community.louvain_communities(U, seed=42)
        Q = nx.community.modularity(U, communities)
    except Exception:
        return 0.5

    Q_REF = 0.75
    return max(0.0, min(1.0, max(0.0, Q) / Q_REF))


# ---------------------------------------------------------------------------
# Acyclicity — Tarjan SCC
# ---------------------------------------------------------------------------

def compute_acyclicity(G: nx.DiGraph) -> float:
    """
    Acyclicity based on the largest strongly-connected component (SCC),
    restricted to internal nodes (those with a 'file' attribute).

    A = 1 - (largest_cyclic_SCC_size / total_internal_nodes)

    Only internal nodes are considered: cycles through external nodes
    (stdlib, third-party packages) are import artefacts, not architectural
    issues. If no 'file' attribute is present on any node, all nodes are
    treated as internal (direct graph usage without scanner).

    Using the largest SCC as severity: one god-cycle of 100 modules is
    architecturally catastrophic and should not average away in large graphs.
    """
    all_nodes = list(G.nodes())
    if len(all_nodes) <= 1:
        return 1.0

    # Restrict to internal nodes when file metadata is available
    internal = [n for n, d in G.nodes(data=True) if d.get("file")]
    nodes = internal if internal else all_nodes
    n = len(nodes)
    if n <= 1:
        return 1.0

    subgraph = G.subgraph(nodes)
    largest_cycle_size = 0
    for scc in nx.strongly_connected_components(subgraph):
        if len(scc) > 1:
            largest_cycle_size = max(largest_cycle_size, len(scc))

    if largest_cycle_size == 0:
        return 1.0

    return 1.0 - (largest_cycle_size / n)


# ---------------------------------------------------------------------------
# Stability — Martin's Distance from Main Sequence
# ---------------------------------------------------------------------------

def compute_stability(G: nx.DiGraph,
                      abstract_modules: Optional[Set[str]] = None) -> float:
    """
    Architectural layering quality via package-level instability variance.

    Nodes are grouped into second-level packages (e.g. "a.b.c" → "a.b"),
    then instability I = Ce/(Ca+Ce) is computed per package using only
    cross-package edges. Variance of I across packages is the score.

    Package-level grouping prevents leaf-module inflation: a repo with
    1000 isolated extractor files (all I=1.0) collapses to one "extractor"
    package, correctly reflecting flat structure instead of false high variance.

    Clean layered architecture  → packages have differentiated I → high score
    Flat / plugin-heavy repo    → few packages, similar I         → low score
    Tangled (everything→hub)    → all I≈0.5                      → low score

    stability = var(I) / 0.25   clamped to [0, 1]

    abstract_modules: retained for API compatibility, not used.
    """
    nodes = list(G.nodes())
    if not nodes:
        return 1.0

    # Group nodes by second-level package
    packages: Dict[str, List[str]] = {}
    for node in nodes:
        parts = node.split(".")
        pkg = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
        packages.setdefault(pkg, []).append(node)

    if len(packages) <= 1:
        return 0.0  # single package: no layering structure to measure

    instabilities = []
    for pkg, members in packages.items():
        member_set = set(members)
        ca = sum(1 for m in members for p in G.predecessors(m) if p not in member_set)
        ce = sum(1 for m in members for s in G.successors(m) if s not in member_set)
        total = ca + ce
        I = ce / total if total > 0 else 0.5
        instabilities.append(I)

    mean_i = sum(instabilities) / len(instabilities)
    var = sum((i - mean_i) ** 2 for i in instabilities) / len(instabilities)
    return min(1.0, var / 0.25)


def compute_instability_variance(G: nx.DiGraph) -> float:
    """Per-node instability variance — kept for backward compatibility.

    Deprecated: use compute_stability() which applies package-level grouping
    to prevent leaf-module inflation in large repos.
    Returns var(I)/0.25 at the node level (not package level).
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

    mean_i = sum(instabilities) / len(instabilities)
    var = sum((i - mean_i) ** 2 for i in instabilities) / len(instabilities)
    return min(1.0, var / 0.25)


# ---------------------------------------------------------------------------
# Hierarchical Modularity — M-score inspired (Pisch et al. ESEM 2024)
# ---------------------------------------------------------------------------

def compute_hierarchical_modularity(G: nx.DiGraph) -> float:
    """
    Hierarchical modularity based on within-package vs cross-package edge density.

    Inspired by M-score (Pisch, Cai, Kazman et al., ESEM 2024) which clusters
    dependencies hierarchically and measures density ratios rather than Newman Q.
    Key advantage: isolated files don't inflate the score (fixes leaf-module bias).

    Groups nodes by second-level package (e.g. "a.b.c" → "a.b").
    For each package, computes:
      within_density  = internal_edges / possible_internal_edges
      cross_edges     = edges leaving this package

    modularity = mean(within_density) / (1 + mean_cross_ratio)

    Returns [0, 1] where 1 = perfect internal cohesion, no cross-package edges.
    Returns 0.5 neutral if fewer than 2 packages.
    """
    nodes = list(G.nodes())
    if not nodes:
        return 1.0

    # Group by first-level package (e.g. "flask.app" → "flask").
    # First-level is the right granularity here: we measure whether flask's
    # internal modules are tightly coupled vs well-isolated from other packages.
    # Second-level grouping (used in stability) would leave each file as its
    # own package for 2-level paths, giving trivially 0 within-density.
    packages: Dict[str, List[str]] = {}
    for node in nodes:
        pkg = node.split(".")[0]
        packages.setdefault(pkg, []).append(node)

    if len(packages) < 2:
        return 0.5  # can't measure modularity with one package

    within_densities = []
    cross_ratios = []

    for pkg, members in packages.items():
        member_set = set(members)
        n_m = len(members)

        # Internal edges (within package)
        internal_edges = sum(
            1 for u in members for v in G.successors(u) if v in member_set
        )
        max_internal = n_m * (n_m - 1)
        within_density = internal_edges / max_internal if max_internal > 0 else 0.0

        # Cross-package edges
        cross_out = sum(
            1 for u in members for v in G.successors(u) if v not in member_set
        )
        total_out = sum(G.out_degree(u) for u in members)
        cross_ratio = cross_out / total_out if total_out > 0 else 0.0

        within_densities.append(within_density)
        cross_ratios.append(cross_ratio)

    mean_within = sum(within_densities) / len(within_densities)
    mean_cross = sum(cross_ratios) / len(cross_ratios)

    # High within-density + low cross-ratio = good modularity
    # Normalize: (1 - mean_cross) is the "isolation" score [0,1]
    # Combined: geometric mean of within_density and isolation
    isolation = 1.0 - mean_cross
    if mean_within == 0 and isolation == 0:
        return 0.0
    return (mean_within * isolation) ** 0.5  # geometric mean


def compute_boundary_crossing_ratio(G: nx.DiGraph) -> float:
    """
    Fraction of internal edges that cross second-level package boundaries.

    Low ratio = good modularity (changes stay within packages).
    High ratio = tangled dependencies = bad architecture.

    Ref: D'Ambros & Lanza (WCRE 2009) — co-changes crossing architectural
    module boundaries correlate MORE with defects than within-module co-changes.

    Returns 1 - crossing_ratio so that higher = better (consistent with AGQ).
    Returns 0.5 neutral if graph has no internal edges.
    """
    nodes = list(G.nodes())
    if not nodes:
        return 1.0

    # First-level grouping: "flask.app" → "flask", "requests.models" → "requests"
    packages: Dict[str, str] = {}
    for node in nodes:
        packages[node] = node.split(".")[0]

    internal = {n for n, d in G.nodes(data=True) if d.get("file")}
    if not internal:
        internal = set(nodes)

    total_internal_edges = 0
    crossing_edges = 0
    for src, tgt in G.edges():
        if src not in internal:
            continue
        total_internal_edges += 1
        if packages.get(src) != packages.get(tgt):
            crossing_edges += 1

    if total_internal_edges == 0:
        return 0.5

    crossing_ratio = crossing_edges / total_internal_edges
    return 1.0 - crossing_ratio


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
    """Compute all AGQ metrics.

    weights: (modularity, acyclicity, stability, cohesion) — auto-normalized.
    Default equal weights. Calibrated churn-optimal: (0.0, 0.73, 0.05, 0.17).

    Scope note: meaningful discrimination requires ~50+ internal modules.
    Smaller graphs default to neutral/perfect component values
    (no cycles, no community structure to detect), inflating AGQ scores
    for trivially small codebases.
    """
    mod = compute_modularity(G)
    acy = compute_acyclicity(G)
    stab = compute_stability(G, abstract_modules)
    coh = compute_cohesion(classes_lcom4 or [])

    # Normalize weights and store on metrics object for weighted agq_score
    total = sum(weights)
    w = tuple(v / total for v in weights) if total > 0 else (0.25, 0.25, 0.25, 0.25)

    m = AGQMetrics(modularity=mod, acyclicity=acy, stability=stab, cohesion=coh)
    m._weights = w  # used by agq_score property if present
    return m
