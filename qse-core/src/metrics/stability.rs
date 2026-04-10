/// Package-level instability variance — with flat-library correction.
///
/// FIX: Previously returned 0.0 for repos with a single package. This
/// unfairly penalized deliberately flat/focused libraries (e.g. click,
/// itsdangerous, arrow) that have good architectural reasons to be flat.
///
/// New behavior for single-package repos:
///   - Compute node-level instability variance instead
///   - This captures fan-in vs fan-out balance even without package hierarchy
///   - Score is halved (0.5×) to reflect that flat structure is less
///     informative than true layering — but not zero
///
/// Additionally: if packages.len() == 2, the variance is driven by just
/// two data points which is statistically unreliable. We apply a correction
/// factor of 0.8× to reflect the small-sample uncertainty.
///
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

    // FIX: single package — use node-level variance (scaled)
    if packages.len() <= 1 {
        return compute_node_level(g) * 0.5;
    }

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

    let raw = (var / 0.25_f64).min(1.0);

    // FIX: two packages → small-sample correction
    if packages.len() == 2 {
        return raw * 0.8;
    }

    raw
}

/// Node-level instability variance (fallback for flat libs).
fn compute_node_level(g: &DiGraph<String, ()>) -> f64 {
    let nodes: Vec<_> = g.node_indices().collect();
    let n = nodes.len();
    if n <= 1 { return 1.0; }

    let instabilities: Vec<f64> = nodes.iter().map(|&ni| {
        let ca = g.neighbors_directed(ni, petgraph::Direction::Incoming).count();
        let ce = g.neighbors_directed(ni, petgraph::Direction::Outgoing).count();
        let total = ca + ce;
        if total > 0 { ce as f64 / total as f64 } else { 0.5 }
    }).collect();

    let mean = instabilities.iter().sum::<f64>() / n as f64;
    let var = instabilities.iter()
        .map(|&i| (i - mean).powi(2))
        .sum::<f64>() / n as f64;

    (var / 0.25_f64).min(1.0)
}
