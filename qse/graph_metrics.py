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
# Adaptive Package Boundary Crossing — depth-aware (D'Ambros & Lanza 2009)
# ---------------------------------------------------------------------------

def _detect_package_depth(G: nx.DiGraph) -> int:
    """Auto-detect the meaningful grouping depth from module path distribution.

    Strategy: find the depth level where packages have the most multi-member
    groups (i.e. where grouping is actually meaningful and non-trivial).

    Examples:
      flask (mean_depth=1.3):  depth 1 → {"flask": [flask.app, flask.views, ...]}
      django (mean_depth=3.3): depth 2 → {"django.db": [...], "django.http": [...]}
      ansible (mean_depth=5):  depth 3 → {"ansible.modules.cloud": [...], ...}
    """
    nodes = [n for n in G.nodes() if "." in n]
    if not nodes:
        return 1

    depths = [len(n.split(".")) for n in nodes]
    mean_depth = sum(depths) / len(depths)

    # Group one level above the leaves: round(mean_depth) - 1
    # flask (mean=1.3) → 1   — group at "flask"
    # django (mean=3.3) → 2  — group at "django.db"
    # ansible (mean=5)  → 4  — group at "ansible.modules.cloud"
    level = max(1, min(4, round(mean_depth) - 1))
    return level


def compute_boundary_crossing_ratio(G: nx.DiGraph) -> float:
    """
    Fraction of internal edges that cross package boundaries, where the
    grouping depth is auto-detected from the project's module path structure.

    Flat libraries (flask, mean_depth≈1.3)  → group at depth 1: "flask.*"
    Frameworks (django, mean_depth≈3.3)     → group at depth 2: "django.db"
    Deep systems (ansible, mean_depth≈5.0)  → group at depth 3: "ansible.modules.cloud"

    This ensures the metric is meaningful regardless of how deeply nested
    the project's package structure is.

    Returns 1 - crossing_ratio: higher = better (fewer cross-boundary edges).
    Returns 0.5 neutral when no edges or single package.

    Ref: D'Ambros & Lanza (WCRE 2009).
    """
    nodes = list(G.nodes())
    if not nodes:
        return 1.0

    depth = _detect_package_depth(G)

    packages: Dict[str, str] = {}
    for node in nodes:
        parts = node.split(".")
        packages[node] = ".".join(parts[:depth]) if len(parts) >= depth else parts[0]

    # Don't short-circuit on single package — compute normally.
    # All edges within one package → 0 crossing → BCR = 1.0 (correct: perfectly isolated).

    internal = {n for n, d in G.nodes(data=True) if d.get("file")}
    if not internal:
        internal = set(nodes)

    total_edges = 0
    crossing_edges = 0
    for src, tgt in G.edges():
        if src not in internal:
            continue
        total_edges += 1
        if packages.get(src) != packages.get(tgt):
            crossing_edges += 1

    if total_edges == 0:
        return 0.5

    return 1.0 - (crossing_edges / total_edges)


def compute_hierarchical_modularity(G: nx.DiGraph) -> float:
    """Deprecated alias — use compute_boundary_crossing_ratio() instead.

    hierarchical_modularity was redundant with Newman modularity Q when
    package boundaries align with natural graph clusters. BCR with adaptive
    depth provides the same signal more directly.
    """
    return compute_boundary_crossing_ratio(G)


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


# ---------------------------------------------------------------------------
# NEW METRICS — validated in perplexity/experiment_total pilot (iter 1-2)
# Empirical basis: 14-repo Python pilot, Spearman correlations:
#   GraphDensity  → bug_mean_days    r=+0.881 p=0.004 (STRONG)
#   GraphDensity  → hotspot_ratio    r=+0.815 p=0.0004 (STRONG)
#   SCCEntropy    → hotspot_ratio    r=-0.640 p=0.014 (moderate)
#   HubRatio      → hotspot_ratio    r=+0.609 p=0.021 (moderate)
# ---------------------------------------------------------------------------


def compute_graph_density(G: nx.DiGraph) -> float:
    """Graph density — fraction of possible edges that exist.

    density = |E| / (|V| * (|V| - 1))

    Empirically validated as the strongest predictor of:
      - bug fix lead time (r=+0.881, p=0.004, n=14 Python OSS repos)
      - hotspot_ratio     (r=+0.815, p=0.0004, n=14)

    Lower density = better architecture (fewer tangled dependencies).
    Dense graphs are harder to reason about and slower to fix bugs in.

    Normalized score (0=worst, 1=best):
      density_score = 1 - min(1, density / DENSITY_REFERENCE)
    where DENSITY_REFERENCE=0.020 (p90 of 14-repo Python pilot).

    Note: differs from modularity — modularity measures clustering,
    density measures overall edge concentration.
    """
    n = G.number_of_nodes()
    e = G.number_of_edges()
    if n <= 1:
        return 0.0
    return round(e / (n * (n - 1)), 6)


# Reference threshold for density score normalization.
# Calibrated on 14-repo Python pilot (p90 = 0.026, conservatively 0.020).
# Projects above this threshold get density_score → 0.0.
DENSITY_REFERENCE = 0.020


def compute_density_score(density: float) -> float:
    """Normalize graph_density to [0, 1] where 1 = best (lowest density).

    density_score = 1 - min(1, density / DENSITY_REFERENCE)
    """
    return round(max(0.0, 1.0 - min(1.0, density / DENSITY_REFERENCE)), 4)


def compute_scc_entropy(G: nx.DiGraph) -> float:
    """Information entropy of the SCC (Strongly Connected Component) distribution.

    H_SCC = -Σ p_k * log2(p_k)
    where p_k = |SCC_k| / |V|

    Empirically validated:
      SCCEntropy → hotspot_ratio  r=-0.640 p=0.014 (n=14 Python OSS repos)

    Higher entropy = more, smaller SCCs = more modular decomposition.
    Lower entropy = one dominant SCC = tangled, harder to change.

    DAG (no cycles): each node is its own SCC → H_SCC = log2(n) [maximum]
    Full cycle:      one SCC of size n         → H_SCC = 0 [minimum]

    Normalized score (0=worst, 1=best):
      scc_entropy_score = H_SCC / log2(n)   [fraction of maximum entropy]
    """
    n = G.number_of_nodes()
    if n <= 1:
        return 0.0
    sccs = list(nx.strongly_connected_components(G))
    probs = [len(scc) / n for scc in sccs if len(scc) > 0]
    import math as _math
    entropy = -sum(p * _math.log2(p) for p in probs if p > 0)
    return round(entropy, 4)


def compute_scc_entropy_score(G: nx.DiGraph) -> float:
    """Normalize scc_entropy to [0, 1] where 1 = best (most modular).

    scc_entropy_score = H_SCC / log2(n)
    """
    import math as _math
    n = G.number_of_nodes()
    if n <= 1:
        return 1.0
    h = compute_scc_entropy(G)
    max_h = _math.log2(n)
    if max_h <= 0:
        return 1.0
    return round(min(1.0, h / max_h), 4)


def compute_hub_ratio(G: nx.DiGraph) -> float:
    """Fraction of nodes with in_degree > 2 * mean_in_degree (hubs).

    hub_ratio = |{v : in_degree(v) > 2 * mean_in_degree}| / |V|

    Empirically validated:
      HubRatio → hotspot_ratio  r=+0.609 p=0.021 (n=14 Python OSS repos)

    High hub_ratio means a few modules attract most dependencies — these
    become hotspots: hard to change without touching many other modules.

    hub_score = 1 - hub_ratio  (lower ratio = better architecture)
    """
    n = G.number_of_nodes()
    if n <= 1:
        return 0.0
    in_degrees = [d for _, d in G.in_degree()]
    mean_in = sum(in_degrees) / n if n > 0 else 0.0
    hub_count = sum(1 for d in in_degrees if d > 2 * mean_in)
    return round(hub_count / n, 4)


def compute_hub_score(hub_ratio: float) -> float:
    """Normalize hub_ratio to [0, 1] where 1 = best (no hubs).

    hub_score = 1 - hub_ratio
    """
    return round(max(0.0, 1.0 - hub_ratio), 4)


# ---------------------------------------------------------------------------
# Extended AGQMetrics — backward compatible
# ---------------------------------------------------------------------------

def compute_agq_extended(
    G: nx.DiGraph,
    abstract_modules: Optional[Set[str]] = None,
    classes_lcom4: Optional[List[int]] = None,
    weights: Tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25),
) -> "AGQMetrics":
    """Compute AGQ + new structural descriptors validated in pilot experiments.

    Returns the same AGQMetrics as compute_agq() but with additional
    attributes injected: graph_density, scc_entropy, hub_ratio, and their
    normalized scores.

    The composite AGQ score remains unchanged (backward compatible).
    New metrics are available as extra attributes on the returned object:
      m.graph_density      float  — raw density
      m.density_score      float  — normalized [0,1], 1=best
      m.scc_entropy        float  — raw Shannon entropy of SCC distribution
      m.scc_entropy_score  float  — normalized [0,1], 1=best
      m.hub_ratio          float  — raw fraction of hub nodes
      m.hub_score          float  — normalized [0,1], 1=best
    """
    m = compute_agq(G, abstract_modules, classes_lcom4, weights)

    # Inject new metrics
    m.graph_density     = compute_graph_density(G)
    m.density_score     = compute_density_score(m.graph_density)
    m.scc_entropy       = compute_scc_entropy(G)
    m.scc_entropy_score = compute_scc_entropy_score(G)
    m.hub_ratio         = compute_hub_ratio(G)
    m.hub_score         = compute_hub_score(m.hub_ratio)

    return m
