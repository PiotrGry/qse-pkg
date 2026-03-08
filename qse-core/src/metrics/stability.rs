/// Package-level instability variance.
/// Groups nodes by second-level package, computes I=Ce/(Ca+Ce) per package,
/// returns var(I)/0.25 clamped to [0,1].
/// Mirrors Python: compute_stability() in graph_metrics.py
use petgraph::graph::DiGraph;
use std::collections::HashMap;

fn pkg(node: &str) -> &str {
    let mut dots = 0;
    for (i, c) in node.char_indices() {
        if c == '.' {
            dots += 1;
            if dots == 2 { return &node[..i]; }
        }
    }
    node
}

pub fn compute(g: &DiGraph<String, ()>) -> f64 {
    let n = g.node_count();
    if n <= 1 { return 1.0; }

    // Group nodes by second-level package
    let mut packages: HashMap<&str, Vec<petgraph::graph::NodeIndex>> = HashMap::new();
    for ni in g.node_indices() {
        let name = &g[ni];
        let p = pkg(name);
        packages.entry(p).or_default().push(ni);
    }

    if packages.len() <= 1 { return 0.0; }

    let mut instabilities: Vec<f64> = Vec::new();

    for members in packages.values() {
        let member_set: std::collections::HashSet<_> = members.iter().copied().collect();

        let ca = members.iter()
            .flat_map(|&ni| g.neighbors_directed(ni, petgraph::Direction::Incoming))
            .filter(|n| !member_set.contains(n))
            .count();
        let ce = members.iter()
            .flat_map(|&ni| g.neighbors_directed(ni, petgraph::Direction::Outgoing))
            .filter(|n| !member_set.contains(n))
            .count();

        let total = ca + ce;
        let i = if total > 0 { ce as f64 / total as f64 } else { 0.5 };
        instabilities.push(i);
    }

    let mean = instabilities.iter().sum::<f64>() / instabilities.len() as f64;
    let var = instabilities.iter()
        .map(|&i| (i - mean).powi(2))
        .sum::<f64>() / instabilities.len() as f64;

    (var / 0.25_f64).min(1.0)
}
