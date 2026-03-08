/// LCOM4: number of connected components in method-attribute bipartite graph.
/// cohesion = 1 - mean(penalty) where penalty = min(1, (LCOM4-1)/4)
/// Mirrors Python: compute_cohesion() + compute_lcom4() in graph_metrics.py
use crate::scanner::ClassInfo;
use std::collections::HashMap;
use petgraph::graph::UnGraph;
use petgraph::algo::connected_components;

fn lcom4(method_attrs: &[(String, std::collections::HashSet<String>)]) -> usize {
    if method_attrs.is_empty() { return 1; }

    let mut g: UnGraph<usize, ()> = UnGraph::new_undirected();
    let nodes: Vec<_> = (0..method_attrs.len()).map(|_| g.add_node(0)).collect();

    for i in 0..method_attrs.len() {
        for j in (i + 1)..method_attrs.len() {
            let shared = method_attrs[i].1.intersection(&method_attrs[j].1).count();
            if shared > 0 {
                g.add_edge(nodes[i], nodes[j], ());
            }
        }
    }

    connected_components(&g)
}

pub fn compute(classes: &HashMap<String, ClassInfo>) -> f64 {
    if classes.is_empty() { return 1.0; }

    let penalties: Vec<f64> = classes.values()
        .filter(|c| !c.method_attrs.is_empty())
        .map(|c| {
            let lcom = lcom4(&c.method_attrs);
            let excess = lcom.saturating_sub(1);
            (excess as f64 / 4.0).min(1.0)
        })
        .collect();

    if penalties.is_empty() { return 1.0; }
    1.0 - penalties.iter().sum::<f64>() / penalties.len() as f64
}
