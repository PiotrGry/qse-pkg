/// Acyclicity: 1 - (largest_SCC_size / total_nodes)
/// Only counts internal nodes (those that are source files, not external imports).
/// Mirrors Python: compute_acyclicity() in graph_metrics.py
use petgraph::algo::tarjan_scc;
use petgraph::graph::DiGraph;

pub fn compute(g: &DiGraph<String, ()>) -> f64 {
    let n = g.node_count();
    if n <= 1 { return 1.0; }

    let sccs = tarjan_scc(g);
    let largest_cycle = sccs.iter()
        .filter(|scc| scc.len() > 1)
        .map(|scc| scc.len())
        .max()
        .unwrap_or(0);

    if largest_cycle == 0 { return 1.0; }
    1.0 - (largest_cycle as f64 / n as f64)
}
