"""
AGQ Graph Metrics - architecture-agnostic, Level 1.

Modularity (Q):  Newman's modularity via Louvain on import graph
Acyclicity (A):  1 - (largest_SCC / internal_nodes) via Tarjan SCC
Stability (St):  package-level instability variance (layering quality)
Cohesion (Co):   1 - mean(LCOM4) per class (connected components in method-attribute graph)

Additional metrics:
  hierarchical_modularity: M-score inspired - density ratio within vs between
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
    coupling_density: float = 0.0  # E2: 1 - normalized(edges/nodes); lower ratio = better
    qse_rank: Optional[float] = None  # E11: rank(C)+rank(S) percentile vs benchmark
    qse_track_m: Optional[float] = None  # E11: M score for within-repo tracking

    @property
    def agq_score(self) -> float:
        """Weighted composite (v1). Weights set by compute_agq(); defaults to equal."""
        w = getattr(self, "_weights", (0.20, 0.20, 0.55, 0.05))
        return (w[0] * self.modularity + w[1] * self.acyclicity +
                w[2] * self.stability + w[3] * self.cohesion)

    @property
    def flat_score(self) -> float:
        """E6: 1 - flat_ratio. Fraction of nodes NOT in shallow namespaces (depth<=2).
        Python-specific signal: flat spaghetti (youtube-dl) -> flat_score~0.0.
        Well-layered Python apps -> flat_score~0.7-0.9.
        Java: always ~1.0 (deep package convention) — not useful for Java.
        Set externally by compute_agq() after scan_to_graph_json() call.
        """
        return getattr(self, "_flat_score", 1.0)

    @property
    def agq_v3c(self) -> float:
        """AGQ v3c — language-aware formula (April 2026).

        Java:   0.20*M + 0.20*A + 0.20*S + 0.20*C + 0.20*CD  [PCA equal weights]
        Python: 0.15*M + 0.05*A + 0.20*S + 0.10*C + 0.15*CD + 0.35*flat_score

        flat_score = 1 - flat_ratio (fraction of nodes NOT in depth<=2 namespaces)
        Rationale:
          - Java flat_score always ~1.0 (no information) -> use PCA equal weights
          - Python flat_score separates POS/NEG: MW p=0.004**, partial|nodes r=+0.670**
          - AGQ_v3c Python: MW p=0.045*, partial|nodes r=+0.460*
            vs AGQ_v2 Python: MW p=0.066 ns, partial|nodes r=-0.309 ns (INVERTED!)
          - AGQ_v3c Java: identical to v2 (partial|nodes r=+0.675**)

        Empirical basis (GT n=14 Java + n=19 Python, April 2026):
          Java  AGQ_v3c: pos=0.564 neg=0.458 MW p=0.001*** partial r=+0.675**
          Python AGQ_v3c: pos=0.565 neg=0.453 MW p=0.045*   partial r=+0.460*
        """
        lang = getattr(self, "_language", "Java")
        fs   = getattr(self, "_flat_score", 1.0)
        M, A, S, C, CD = (self.modularity, self.acyclicity,
                          self.stability, self.cohesion, self.coupling_density)
        if lang == "Python":
            return (0.15*M + 0.05*A + 0.20*S + 0.10*C + 0.15*CD + 0.35*fs)
        else:  # Java, Go, COBOL — PCA equal weights (no flat_score signal)
            return (0.20*M + 0.20*A + 0.20*S + 0.20*C + 0.20*CD)

    @property
    def agq_v2(self) -> float:
        """AGQ v2: includes coupling_density (E2 experiment, April 2026).

        Formula: 0.20*M + 0.20*A + 0.35*S + 0.05*C + 0.20*CD
        Rationale:
          - coupling_density (CD) = 1 - clip(edges/nodes / CD_REF, 0, 1)
          - CD_REF = 6.0 (empirical: 95th pct of Java OSS iter6 = 5.8)
          - Lower edges/nodes ratio = fewer tangled dependencies = better
          - S weight reduced 0.55->0.35 to compensate (S blind to DDD hierarchy)
          - CD weight 0.20 = same as M and A (same evidence level: p<0.05 on GT n=10)

        Empirical basis (GT dataset n=10 certain, April 2026):
          r(edges/nodes, Panel) = -0.787**  p=0.007 (raw, n=10 original)
          r(edges/nodes, Panel) = -0.697*   p<0.05  (partial | nodes)
          Mann-Whitney pos vs neg: p=0.010 **
        """
        w_v2 = getattr(self, "_weights_v2", (0.20, 0.20, 0.35, 0.05, 0.20))
        return (w_v2[0] * self.modularity +
                w_v2[1] * self.acyclicity +
                w_v2[2] * self.stability +
                w_v2[3] * self.cohesion +
                w_v2[4] * self.coupling_density)


# ---------------------------------------------------------------------------
# Modularity - Newman's Q via Louvain
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
# Acyclicity - Tarjan SCC
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
# Stability - Martin's Distance from Main Sequence
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
        # FIX: flat libraries (single package) previously got 0.0, unfairly
        # penalizing deliberately focused libs (click, arrow, itsdangerous).
        # Use node-level instability variance instead, scaled by 0.5 to
        # reflect that flat structure is less informative than true layering.
        return _compute_node_level_stability(G) * 0.5

    if len(packages) == 2:
        # Small-sample correction: two packages → unreliable variance
        # (will be computed below and multiplied by 0.8)
        pass

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
    raw = min(1.0, var / 0.25)
    # Small-sample correction for 2-package repos
    if len(packages) == 2:
        return raw * 0.8
    return raw


def compute_instability_variance(G: nx.DiGraph) -> float:
    """Per-node instability variance - kept for backward compatibility.

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
    raw = min(1.0, var / 0.25)
    # Small-sample correction for 2-node graphs
    if len(nodes) == 2:
        return raw * 0.8
    return raw


def _compute_node_level_stability(G: nx.DiGraph) -> float:
    """Node-level instability variance — fallback for flat single-package repos.

    Used when the repo has only one package (e.g. click, arrow, itsdangerous).
    These are deliberately flat libraries — returning 0.0 unfairly penalizes them.
    We compute instability per node instead and scale by 0.5 to reflect that
    flat structure is less informative than true package layering.
    """
    nodes = list(G.nodes())
    n = len(nodes)
    if n <= 1:
        return 1.0
    instabilities = []
    for node in nodes:
        ca = G.in_degree(node)
        ce = G.out_degree(node)
        total = ca + ce
        I = ce / total if total > 0 else 0.5
        instabilities.append(I)
    mean_i = sum(instabilities) / len(instabilities)
    var = sum((i - mean_i) ** 2 for i in instabilities) / len(instabilities)
    return min(1.0, var / 0.25)


# ---------------------------------------------------------------------------
# Adaptive Package Boundary Crossing - depth-aware (D'Ambros & Lanza 2009)
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
    # flask (mean=1.3) → 1   - group at "flask"
    # django (mean=3.3) → 2  - group at "django.db"
    # ansible (mean=5)  → 4  - group at "ansible.modules.cloud"
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

    # Don't short-circuit on single package - compute normally.
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
    """Deprecated alias - use compute_boundary_crossing_ratio() instead.

    hierarchical_modularity was redundant with Newman modularity Q when
    package boundaries align with natural graph clusters. BCR with adaptive
    depth provides the same signal more directly.
    """
    return compute_boundary_crossing_ratio(G)


# ---------------------------------------------------------------------------
# Cohesion - LCOM4
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
        # FIX: returning 1.0 (perfect) when no classes found is misleading.
        # For Python/Java: no classes = scanner likely found nothing = neutral 0.75.
        # The caller (Rust scanner) passes [] for Go by design — Go returns 1.0
        # at the Rust level before reaching here.
        return 0.75

    penalties = []
    for lcom in classes_lcom4:
        # FIX: LCOM4=1 always for single-method classes — exclude them.
        # They trivially satisfy cohesion but add no signal.
        # We receive pre-computed LCOM4 values; filter out trivial ones.
        if lcom <= 1:
            continue  # LCOM4=1 = perfectly cohesive, no penalty, no signal
        excess = lcom - 1
        # Penalty ramp: 0 at LCOM4=2 (excess=1), 1.0 at LCOM4=5+ (excess=4)
        penalty = min(1.0, excess / 4.0)
        penalties.append(penalty)

    if not penalties:
        return 1.0  # All classes are cohesive (LCOM4=1)

    return 1.0 - (sum(penalties) / len(penalties))


# ---------------------------------------------------------------------------
# CCD - Cumulative Component Dependency (Lakos 1996)
# ---------------------------------------------------------------------------

def compute_ccd(G: nx.DiGraph) -> Dict[str, float]:
    """Cumulative Component Dependency - measures ripple effect.

    CCD = sum of reachable nodes from each node (including self).
    Normalized by CCD of a balanced binary tree: n * log2(n).

    High CCD_norm means a change in one module propagates widely.

    Returns dict with ccd_raw, ccd_norm, avg_reachable.
    Only internal nodes (with 'file' attribute) are considered.
    """
    internal = [n for n, d in G.nodes(data=True) if d.get("file")]
    nodes = internal if internal else list(G.nodes())
    n = len(nodes)
    if n <= 1:
        return {"ccd_raw": 0, "ccd_norm": 0.0, "avg_reachable": 0.0}

    subgraph = G.subgraph(nodes)

    # For large graphs, sample to avoid O(V*(V+E)) explosion
    import math as _math
    sample_nodes = nodes
    if n > 2000:
        import random
        random.seed(42)
        sample_nodes = random.sample(nodes, min(500, n))

    total_reachable = 0
    for node in sample_nodes:
        reachable = nx.descendants(subgraph, node)
        total_reachable += len(reachable) + 1  # +1 for self

    if len(sample_nodes) < n:
        # Extrapolate from sample
        total_reachable = int(total_reachable * n / len(sample_nodes))

    # CCD of balanced binary tree = n * log2(n+1)
    ccd_tree = n * _math.log2(n + 1) if n > 1 else 1
    ccd_norm = min(total_reachable / ccd_tree, 10.0) if ccd_tree > 0 else 0.0
    avg_reachable = total_reachable / n if n > 0 else 0.0

    return {
        "ccd_raw": total_reachable,
        "ccd_norm": round(ccd_norm, 4),
        "avg_reachable": round(avg_reachable, 2),
    }


# ---------------------------------------------------------------------------
# Indirect Coupling - Edge Strength Metric (Šora 2013, Chiricota 2003)
# ---------------------------------------------------------------------------

def compute_indirect_coupling(G: nx.DiGraph) -> Dict[str, float]:
    """Indirect coupling via shared neighbors (Edge Strength Metric).

    For each edge (u,v), ESM = |neighbors(u) ∩ neighbors(v)| / |neighbors(u) ∪ neighbors(v)|
    High ESM means u and v share many dependencies - strongly coupled indirectly.

    Returns dict with mean_ic, max_ic, ic_above_05 (fraction of edges with IC > 0.5).
    Only internal nodes considered.
    """
    internal = set(n for n, d in G.nodes(data=True) if d.get("file"))
    nodes = internal if internal else set(G.nodes())

    # Use full graph for neighbor computation (including external nodes)
    # but only measure IC for edges involving internal nodes
    edges = [(u, v) for u, v in G.edges() if u in nodes]
    if not edges:
        return {"mean_ic": 0.0, "max_ic": 0.0, "ic_above_05": 0.0}

    # Precompute undirected neighbor sets on full graph for ESM
    neighbors = {}
    undirected = G.to_undirected()
    for node in G.nodes():
        neighbors[node] = set(undirected.neighbors(node))

    esm_values = []
    for u, v in edges:
        if u not in neighbors or v not in neighbors:
            continue
        nu, nv = neighbors[u], neighbors[v]
        union = nu | nv
        if not union:
            continue
        intersection = nu & nv
        esm = len(intersection) / len(union)
        esm_values.append(esm)

    if not esm_values:
        return {"mean_ic": 0.0, "max_ic": 0.0, "ic_above_05": 0.0}

    mean_ic = sum(esm_values) / len(esm_values)
    max_ic = max(esm_values)
    ic_above_05 = sum(1 for v in esm_values if v > 0.5) / len(esm_values)

    return {
        "mean_ic": round(mean_ic, 4),
        "max_ic": round(max_ic, 4),
        "ic_above_05": round(ic_above_05, 4),
    }


# ---------------------------------------------------------------------------
# Per-module metrics (fan-in, fan-out, SCC membership)
# ---------------------------------------------------------------------------

def compute_per_module_metrics(G: nx.DiGraph) -> Dict[str, object]:
    """Per-module breakdown: fan-in, fan-out, instability, SCC membership.

    Returns dict with:
      - summary: avg/max/variance stats
      - modules: list of per-module dicts (sorted by fan_out desc)
      - scc_modules: list of module names in cycles
    """
    internal = [n for n, d in G.nodes(data=True) if d.get("file")]
    nodes = internal if internal else list(G.nodes())
    if not nodes:
        return {"summary": {}, "modules": [], "scc_modules": []}

    node_set = set(nodes)
    subgraph = G.subgraph(nodes)

    # SCC membership
    scc_nodes = set()
    for scc in nx.strongly_connected_components(subgraph):
        if len(scc) > 1:
            scc_nodes.update(scc)

    modules = []
    fan_ins, fan_outs = [], []

    for node in nodes:
        # Fan-in: all predecessors (internal + external imports of this module)
        fi = G.in_degree(node)
        # Fan-out: all successors (what this module imports, including external)
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

    # Sort by fan_out descending (hotspot ranking)
    modules.sort(key=lambda m: -m["fan_out"])

    import statistics as _stats
    summary = {
        "n_modules": len(nodes),
        "avg_fan_in": round(sum(fan_ins) / len(fan_ins), 2) if fan_ins else 0,
        "max_fan_in": max(fan_ins) if fan_ins else 0,
        "avg_fan_out": round(sum(fan_outs) / len(fan_outs), 2) if fan_outs else 0,
        "max_fan_out": max(fan_outs) if fan_outs else 0,
        "fan_out_std": round(_stats.stdev(fan_outs), 3) if len(fan_outs) > 1 else 0,
        "n_in_scc": len(scc_nodes),
        "scc_fraction": round(len(scc_nodes) / len(nodes), 4) if nodes else 0,
    }

    return {
        "summary": summary,
        "modules": modules[:50],  # top 50 by fan-out
        "scc_modules": sorted(scc_nodes),
    }


# ---------------------------------------------------------------------------
# Package-level structural metrics (E10, April 2026)
# ---------------------------------------------------------------------------

def _build_package_map(G: nx.DiGraph,
                       internal_nodes: Optional[Set[str]] = None,
                       packages: Optional[Set[str]] = None
                       ) -> Dict[str, str]:
    """Map each internal node to its package.

    If *packages* is provided, uses longest-prefix matching.
    Otherwise derives packages by stripping the last dotted segment
    from each fully-qualified node name.

    Returns dict  node -> package_name.
    """
    nodes = internal_nodes if internal_nodes else set(G.nodes())
    pkg_map: Dict[str, str] = {}

    if packages:
        sorted_pkgs = sorted(packages, key=len, reverse=True)
        for n in nodes:
            if n not in G:
                continue
            for p in sorted_pkgs:
                if n.startswith(p + "."):
                    pkg_map[n] = p
                    break
            else:
                # fallback: strip last segment
                if "." in n:
                    pkg_map[n] = n.rsplit(".", 1)[0]
    else:
        for n in nodes:
            if n not in G:
                continue
            if "." in n:
                pkg_map[n] = n.rsplit(".", 1)[0]
            else:
                pkg_map[n] = ""

    return pkg_map


def compute_package_acyclicity(G: nx.DiGraph,
                               internal_nodes: Optional[Set[str]] = None,
                               packages: Optional[Set[str]] = None
                               ) -> float:
    """Package-level acyclicity (PCA).

    Builds a package-level dependency graph from cross-package edges,
    then measures: PCA = 1 - (largest_pkg_SCC / total_packages).

    Unlike class-level acyclicity (A), this catches architectural
    layer violations that create package-level cycles even when
    no class-level cycle exists.

    Returns float in [0, 1] where 1.0 = no package cycles.
    """
    pkg_map = _build_package_map(G, internal_nodes, packages)
    if len(set(pkg_map.values())) <= 1:
        return 1.0

    # Build package-level digraph
    pkg_graph = nx.DiGraph()
    for u, v in G.edges():
        if u in pkg_map and v in pkg_map:
            pu, pv = pkg_map[u], pkg_map[v]
            if pu != pv:
                pkg_graph.add_edge(pu, pv)

    if pkg_graph.number_of_nodes() <= 1:
        return 1.0

    # Largest SCC (package-level)
    largest_scc = 0
    for scc in nx.strongly_connected_components(pkg_graph):
        if len(scc) > 1:
            largest_scc = max(largest_scc, len(scc))

    total_pkgs = pkg_graph.number_of_nodes()
    if largest_scc == 0:
        return 1.0

    return 1.0 - (largest_scc / total_pkgs)


def compute_layer_violation_ratio(G: nx.DiGraph,
                                  internal_nodes: Optional[Set[str]] = None,
                                  packages: Optional[Set[str]] = None
                                  ) -> float:
    """Layer Violation Ratio (LVR) — DIP + layer-bypass score.

    Classifies each package into a layer heuristically:
      - DOMAIN:  package name contains 'domain', 'model', 'entity', 'core'
      - SERVICE: package name contains 'service', 'usecase', 'application'
      - INFRA:   package name contains 'repository', 'persistence', 'config',
                 'security', 'web', 'rest', 'controller', 'api', 'gateway',
                 'adapter', 'infrastructure'
      - OTHER:   everything else

    Violations counted:
      1. DIP violation: DOMAIN -> INFRA edge  (domain must not know infra)
      2. DIP violation: DOMAIN -> SERVICE edge (domain must not know service in strict DDD)
      3. Layer bypass:  INFRA -> DOMAIN edge that skips SERVICE (direct repo access from controller)
         Specifically: controller/web/rest -> repository/persistence (bypasses service)

    LVR = 1 - (violation_edges / total_cross_pkg_edges)
    Returns float in [0, 1] where 1.0 = no violations.
    """
    pkg_map = _build_package_map(G, internal_nodes, packages)

    # Classify packages into layers
    DOMAIN_KEYWORDS = {'domain', 'model', 'entity', 'core', 'aggregate'}
    SERVICE_KEYWORDS = {'service', 'usecase', 'application', 'interactor'}
    INFRA_KEYWORDS = {'repository', 'persistence', 'config', 'configuration',
                      'security', 'web', 'rest', 'controller', 'api', 'gateway',
                      'adapter', 'infrastructure', 'filter', 'handler', 'client'}
    # Higher-layer infra that should not be accessed by lower infra
    PRESENTATION_KEYWORDS = {'web', 'rest', 'controller', 'api', 'gateway'}
    PERSISTENCE_KEYWORDS = {'repository', 'persistence', 'dao'}

    def classify_package(pkg: str) -> str:
        segments = set(pkg.lower().split('.'))
        if segments & DOMAIN_KEYWORDS:
            return 'DOMAIN'
        if segments & SERVICE_KEYWORDS:
            return 'SERVICE'
        if segments & INFRA_KEYWORDS:
            return 'INFRA'
        return 'OTHER'

    def is_presentation(pkg: str) -> bool:
        segments = set(pkg.lower().split('.'))
        return bool(segments & PRESENTATION_KEYWORDS)

    def is_persistence(pkg: str) -> bool:
        segments = set(pkg.lower().split('.'))
        return bool(segments & PERSISTENCE_KEYWORDS)

    # Count cross-package edges and violations
    total_cross = 0
    violations = 0

    for u, v in G.edges():
        if u not in pkg_map or v not in pkg_map:
            continue
        pu, pv = pkg_map[u], pkg_map[v]
        if pu == pv:
            continue

        total_cross += 1
        lu = classify_package(pu)
        lv = classify_package(pv)

        # DIP violation: domain depends on infra
        if lu == 'DOMAIN' and lv == 'INFRA':
            violations += 1
        # DIP violation: domain depends on service (strict DDD)
        elif lu == 'DOMAIN' and lv == 'SERVICE':
            violations += 1
        # Layer bypass: presentation -> persistence (skips service)
        elif is_presentation(pu) and is_persistence(pv):
            violations += 1

    if total_cross == 0:
        return 1.0

    return 1.0 - (violations / total_cross)


def compute_structural_health(G: nx.DiGraph,
                              internal_nodes: Optional[Set[str]] = None,
                              packages: Optional[Set[str]] = None
                              ) -> Dict[str, float]:
    """Compute all three new structural metrics.

    Returns dict with:
      - pca: Package-level acyclicity [0,1]
      - lvr: Layer violation ratio [0,1]
      - combined: geometric mean of pca and lvr [0,1]
    """
    pca = compute_package_acyclicity(G, internal_nodes, packages)
    lvr = compute_layer_violation_ratio(G, internal_nodes, packages)
    combined = (pca * lvr) ** 0.5  # geometric mean

    return {
        'pca': round(pca, 4),
        'lvr': round(lvr, 4),
        'combined': round(combined, 4),
    }


# ---------------------------------------------------------------------------
# Composite
# ---------------------------------------------------------------------------

def compute_agq(G: nx.DiGraph,
                abstract_modules: Optional[Set[str]] = None,
                classes_lcom4: Optional[List[int]] = None,
                weights: Tuple[float, float, float, float] = (0.20, 0.20, 0.55, 0.05)
                ) -> AGQMetrics:
    """Compute all AGQ metrics.

    weights: (modularity, acyclicity, stability, cohesion) - auto-normalized.

    Default weights calibrated empirically on n=279 OSS repos
    (projects with bug fix lead time ≤14 days, Spearman CV optimization):

      Stability   = 0.55  — dominant predictor (single metric CV r=-0.170*)
                            model degrades most when removed (ΔCV=-0.048)
      Modularity  = 0.20  — important signal (ΔCV=-0.021 when removed)
      Acyclicity  = 0.20  — best pair with Stability (pair CV r=-0.169)
                            neutral alone but amplifies Stability signal
      Cohesion    = 0.05  — redundant (model improves +0.022 without it)
                            retained at minimum weight for interpretability

    Previous calibration (churn-optimal: 0.0/0.73/0.05/0.17) was based
    on git churn as ground truth — replaced by bug_lead_time ground truth.

    CV improvement vs equal weights (0.25/0.25/0.25/0.25): +17%
    (CV mean r: -0.143 → -0.167)

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

    # E2: coupling_density = 1 - clip(edges/nodes / CD_REF, 0, 1)
    # CD_REF=6.0: empirical 95th percentile of Java OSS repos (iter6, n=147)
    # Low ratio -> sparse deps -> high coupling_density score (good)
    # High ratio -> tangled deps -> low coupling_density score (bad)
    CD_REF = 6.0
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()
    raw_ratio = (n_edges / n_nodes) if n_nodes > 0 else 0.0
    cd = max(0.0, 1.0 - min(raw_ratio / CD_REF, 1.0))

    m = AGQMetrics(modularity=mod, acyclicity=acy, stability=stab, cohesion=coh,
                   coupling_density=cd)
    m._weights = w  # used by agq_score property if present
    m._weights_v2 = (0.20, 0.20, 0.35, 0.05, 0.20)  # AGQ v2 weights
    m._raw_ratio = raw_ratio  # store for diagnostics
    # v3c: language and flat_score set externally (requires scan_to_graph_json)
    # Default: Java-like (flat_score=1.0 -> PCA equal weights used)
    m._flat_score = 1.0
    m._language   = "Java"
    return m


# ═══════════════════════════════════════════════════════════════════════════
# QSE Three-Layer Framework (E11/E12/E12b validated)
#
#   Layer 1 — QSE-Rank:       cross-repo benchmarking (rank(C)+rank(S))
#   Layer 2 — QSE-Track:      within-repo refactoring monitoring (M, PCA, violations)
#   Layer 3 — QSE-Diagnostic: component-level problem identification (all metrics)
# ═══════════════════════════════════════════════════════════════════════════


def compute_qse_rank(
    metrics: AGQMetrics,
    benchmark_C: List[float],
    benchmark_S: List[float],
) -> float:
    """QSE-Rank: benchmark-relative quality score using rank aggregation.

    Computes percentile rank of cohesion (C) and stability (S) against
    a reference benchmark distribution, then sums them (Borda count).

    Result in [0, 2]: higher = better architecture quality.
    - 2.0: better than all benchmark repos on both C and S
    - 1.0: median on both (or mixed)
    - 0.0: worse than all benchmark repos on both

    Empirical validation (E11/E12b, n=52 GT dataset):
      - In-sample ρ = +0.410, p = 0.0025**
      - LOOCV ρ = +0.414 (no overfitting)
      - 50/50 split mean ρ = +0.406, 88.2% of splits significant
      - Permutation p = 0.0018
      - AUC = 0.760 (POS vs NEG separation)
      - 51% better than AGQ (ρ = 0.272)

    Rank aggregation eliminates scale bias:
      C range [0.22, 0.75], S range [0.03, 0.92] → both normalized to [0, 1].

    Intended use: cross-repo benchmarking ("how good is this repo?").
    Not suitable for within-repo monitoring (C and S are class-level metrics
    that don't change with package refactoring). Use compute_qse_track() instead.

    Args:
        metrics: AGQMetrics from compute_agq()
        benchmark_C: list of cohesion values from reference repos
        benchmark_S: list of stability values from reference repos

    Returns:
        QSE-Rank score in [0, 2]
    """
    import numpy as np

    bench_c = np.array(benchmark_C)
    bench_s = np.array(benchmark_S)
    c_pct = float(np.mean(bench_c <= metrics.cohesion))
    s_pct = float(np.mean(bench_s <= metrics.stability))
    score = c_pct + s_pct
    metrics.qse_rank = score
    return score


def compute_qse_track(
    G: nx.DiGraph,
    internal_nodes: Optional[Set[str]] = None,
    packages: Optional[Set[str]] = None,
) -> Dict[str, object]:
    """QSE-Track: within-repo architecture monitoring.

    Returns metrics that respond to package-level refactoring,
    intended for CI/CD pipelines and before/after comparison.

    Tracked signals:
      - M (modularity):  only significant within-repo metric (ρ = 0.426*, E10b)
      - PCA (package acyclicity): reacts to cycle-breaking
      - dip_violations:  count of DIP/layer-bypass edges
      - largest_scc:     size of largest package-level strongly connected component

    Root cause (E11): C and S are class-level aggregates with literally
    zero delta (Δ = 0.0) across package refactoring iterations in all 5
    tested repos. Only M and structure-level metrics respond.

    NOT suitable for cross-repo benchmarking (use compute_qse_rank).

    Args:
        G: directed import graph
        internal_nodes: set of internal node names (optional filter)
        packages: set of package prefixes (optional filter)

    Returns:
        dict with keys: M, PCA, dip_violations, largest_scc
    """
    m = compute_modularity(G)

    # PCA + largest SCC
    pca = compute_package_acyclicity(G, internal_nodes, packages)
    largest_scc = _compute_largest_pkg_scc(G, internal_nodes, packages)

    # DIP violations from LVR computation
    dip = _count_dip_violations(G, internal_nodes, packages)

    return {
        "M": round(m, 4),
        "PCA": round(float(pca), 4),
        "dip_violations": int(dip),
        "largest_scc": int(largest_scc),
    }


def compute_qse_diagnostic(
    G: nx.DiGraph,
    metrics: AGQMetrics,
    benchmark_C: Optional[List[float]] = None,
    benchmark_S: Optional[List[float]] = None,
    internal_nodes: Optional[Set[str]] = None,
    packages: Optional[Set[str]] = None,
) -> Dict[str, object]:
    """QSE-Diagnostic: component-level problem identification.

    Returns the full metric decomposition for root-cause analysis.
    Each metric comes with its raw value AND a percentile rank against
    the GT benchmark (if provided), so the user can see exactly which
    dimension is weak.

    Intended use: "What specifically is wrong with this architecture?"

    Args:
        G: directed import graph
        metrics: AGQMetrics from compute_agq()
        benchmark_C: optional reference cohesion values (default: GT_BENCHMARK_C)
        benchmark_S: optional reference stability values (default: GT_BENCHMARK_S)
        internal_nodes: optional filter
        packages: optional filter

    Returns:
        dict with per-metric raw values, percentiles, and problem flags
    """
    import numpy as np

    bench_c = np.array(benchmark_C or GT_BENCHMARK_C)
    bench_s = np.array(benchmark_S or GT_BENCHMARK_S)

    # Structural metrics
    pca = compute_package_acyclicity(G, internal_nodes, packages)
    lvr = compute_layer_violation_ratio(G, internal_nodes, packages)
    dip = _count_dip_violations(G, internal_nodes, packages)
    largest_scc = _compute_largest_pkg_scc(G, internal_nodes, packages)

    # Percentiles vs benchmark
    c_pct = float(np.mean(bench_c <= metrics.cohesion))
    s_pct = float(np.mean(bench_s <= metrics.stability))

    # Problem flags (bottom quartile = flag)
    problems = []
    if c_pct < 0.25:
        problems.append("LOW_COHESION")
    if s_pct < 0.25:
        problems.append("LOW_STABILITY")
    if metrics.modularity < 0.4:
        problems.append("LOW_MODULARITY")
    if pca < 0.8:
        problems.append("PACKAGE_CYCLES")
    if lvr < 0.95:
        problems.append("DIP_VIOLATIONS")
    if metrics.coupling_density < 0.3:
        problems.append("HIGH_COUPLING_DENSITY")

    return {
        "C": round(metrics.cohesion, 4),
        "C_percentile": round(c_pct, 3),
        "S": round(metrics.stability, 4),
        "S_percentile": round(s_pct, 3),
        "M": round(metrics.modularity, 4),
        "A": round(metrics.acyclicity, 4),
        "CD": round(metrics.coupling_density, 4),
        "PCA": round(float(pca), 4),
        "LVR": round(float(lvr), 4),
        "dip_violations": int(dip),
        "largest_scc": int(largest_scc),
        "problems": problems,
    }


# ── Internal helpers for QSE-Track/Diagnostic ─────────────────────────

def _compute_largest_pkg_scc(
    G: nx.DiGraph,
    internal_nodes: Optional[Set[str]] = None,
    packages: Optional[Set[str]] = None,
) -> int:
    """Return size of largest package-level SCC (>1 node means cycle)."""
    pkg_map = _build_package_map(G, internal_nodes, packages)
    if len(set(pkg_map.values())) <= 1:
        return 0

    pkg_graph = nx.DiGraph()
    for u, v in G.edges():
        if u in pkg_map and v in pkg_map:
            pu, pv = pkg_map[u], pkg_map[v]
            if pu != pv:
                pkg_graph.add_edge(pu, pv)

    largest = 0
    for scc in nx.strongly_connected_components(pkg_graph):
        if len(scc) > 1:
            largest = max(largest, len(scc))
    return largest


def _count_dip_violations(
    G: nx.DiGraph,
    internal_nodes: Optional[Set[str]] = None,
    packages: Optional[Set[str]] = None,
) -> int:
    """Count DIP violation edges (domain->infra, domain->service, presentation->persistence)."""
    pkg_map = _build_package_map(G, internal_nodes, packages)

    DOMAIN_KEYWORDS = {'domain', 'model', 'entity', 'core', 'aggregate'}
    SERVICE_KEYWORDS = {'service', 'usecase', 'application', 'interactor'}
    INFRA_KEYWORDS = {'repository', 'persistence', 'config', 'configuration',
                      'security', 'web', 'rest', 'controller', 'api', 'gateway',
                      'adapter', 'infrastructure', 'filter', 'handler', 'client'}
    PRESENTATION_KEYWORDS = {'web', 'rest', 'controller', 'api', 'gateway'}
    PERSISTENCE_KEYWORDS = {'repository', 'persistence', 'dao'}

    def classify(pkg: str) -> str:
        segments = set(pkg.lower().split('.'))
        if segments & DOMAIN_KEYWORDS:
            return 'DOMAIN'
        if segments & SERVICE_KEYWORDS:
            return 'SERVICE'
        if segments & INFRA_KEYWORDS:
            return 'INFRA'
        return 'OTHER'

    violations = 0
    for u, v in G.edges():
        if u not in pkg_map or v not in pkg_map:
            continue
        pu, pv = pkg_map[u], pkg_map[v]
        if pu == pv:
            continue
        lu, lv = classify(pu), classify(pv)
        if lu == 'DOMAIN' and lv in ('INFRA', 'SERVICE'):
            violations += 1
        elif (set(pu.lower().split('.')) & PRESENTATION_KEYWORDS and
              set(pv.lower().split('.')) & PERSISTENCE_KEYWORDS):
            violations += 1
    return violations


# ── Built-in GT benchmark (n=52, E10 validated, April 2026) ──────────────
# Used as default reference for compute_qse_rank when no custom benchmark.
GT_BENCHMARK_C = [
    0.4643, 0.2884, 0.4865, 0.587, 0.4002, 0.3479, 0.3985, 0.307, 0.3511,
    0.2909, 0.4199, 0.4795, 0.3975, 0.575, 0.4058, 0.3446, 0.3634, 0.318,
    0.4219, 0.4634, 0.447, 0.4227, 0.3667, 0.4203, 0.5731, 0.4265, 0.6081,
    0.75, 0.2172, 0.3024, 0.4177, 0.2401, 0.2328, 0.3341, 0.3998, 0.4301,
    0.3498, 0.2839, 0.3042, 0.3051, 0.3536, 0.3264, 0.4091, 0.2883, 0.25,
    0.3811, 0.5147, 0.575, 0.5952, 0.4276, 0.3514, 0.3541,
]
GT_BENCHMARK_S = [
    0.2353, 0.1814, 0.1736, 0.2344, 0.255, 0.1052, 0.25, 0.1226, 0.0714,
    0.2099, 0.5813, 0.1814, 0.6424, 0.1142, 0.0754, 0.111, 0.0999, 0.093,
    0.1856, 0.1479, 0.1211, 0.0952, 0.5778, 0.1247, 0.1664, 0.1814, 0.19,
    0.36, 0.2177, 0.9147, 0.4119, 0.1736, 0.2489, 0.8427, 0.3314, 0.0689,
    0.1294, 0.2095, 0.098, 0.4327, 0.5034, 0.1175, 0.3951, 0.1253, 0.3951,
    0.076, 0.19, 0.9239, 0.2099, 0.2215, 0.0331, 0.1211,
]

