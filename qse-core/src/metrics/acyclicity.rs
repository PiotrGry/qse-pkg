/// Acyclicity: 1 - (largest_cyclic_SCC_size / internal_node_count)
///
/// FIX: Previously operated on the full internal_graph which includes both
/// internal nodes (source files) AND their direct import targets (which may
/// be external packages). This inflated the denominator and underestimated
/// cycle severity.
///
/// Now: uses only nodes that are in result.internal_nodes — i.e. nodes
/// that correspond to actual source files we scanned. Mirrors Python exactly:
///   internal = [n for n, d in G.nodes(data=True) if d.get("file")]
///
/// Example: project with 50 internal files + 200 external import targets
///   BEFORE fix: acyclicity measured on n=250 — cycle of 10 = 1-(10/250)=0.96
///   AFTER fix:  acyclicity measured on n=50  — cycle of 10 = 1-(10/50)=0.80
///
/// This matches Python behavior and correctly reflects architectural severity.
use petgraph::algo::tarjan_scc;
use petgraph::graph::DiGraph;
use petgraph::graph::NodeIndex;
use std::collections::HashSet;

pub fn compute(
    g: &DiGraph<String, ()>,
    internal_nodes: &HashSet<String>,
) -> f64 {
    let n_total = g.node_count();
    if n_total <= 1 { return 1.0; }

    // Filter to internal nodes only (source files we actually scanned)
    let internal_indices: Vec<NodeIndex> = g
        .node_indices()
        .filter(|&ni| internal_nodes.contains(&g[ni]))
        .collect();

    let n = internal_indices.len();
    if n <= 1 { return 1.0; }

    // Build subgraph of internal nodes only
    let mut sub: DiGraph<String, ()> = DiGraph::new();
    let mut idx_map = std::collections::HashMap::new();
    for &ni in &internal_indices {
        let new_ni = sub.add_node(g[ni].clone());
        idx_map.insert(ni, new_ni);
    }
    for &ni in &internal_indices {
        for nb in g.neighbors(ni) {
            // Only add edges between internal nodes
            if let Some(&nb_new) = idx_map.get(&nb) {
                let ni_new = idx_map[&ni];
                if !sub.contains_edge(ni_new, nb_new) {
                    sub.add_edge(ni_new, nb_new, ());
                }
            }
        }
    }

    let sccs = tarjan_scc(&sub);
    let largest_cycle = sccs.iter()
        .filter(|scc| scc.len() > 1)
        .map(|scc| scc.len())
        .max()
        .unwrap_or(0);

    if largest_cycle == 0 { return 1.0; }
    1.0 - (largest_cycle as f64 / n as f64)
}
