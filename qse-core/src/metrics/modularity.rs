/// Newman modularity Q via Louvain-like greedy algorithm.
/// Normalized: max(0, Q) / 0.75, returns 0.5 neutral for n<10 with edges.
/// Mirrors Python: compute_modularity() in graph_metrics.py
use petgraph::graph::DiGraph;

pub fn compute(g: &DiGraph<String, ()>) -> f64 {
    let n = g.node_count();
    if n <= 1 { return 1.0; }

    // Build undirected edge list (ignore direction for modularity)
    let mut edges: Vec<(usize, usize)> = Vec::new();
    for e in g.edge_indices() {
        let (a, b) = g.edge_endpoints(e).unwrap();
        let ai = a.index();
        let bi = b.index();
        if ai != bi {
            edges.push((ai.min(bi), ai.max(bi)));
        }
    }
    edges.sort();
    edges.dedup();

    if edges.is_empty() { return 1.0; }
    if n < 10 { return 0.5; }

    let m = edges.len() as f64;
    let mut degree = vec![0usize; n];
    for &(a, b) in &edges {
        degree[a] += 1;
        degree[b] += 1;
    }

    // Greedy Louvain-inspired: start each node in own community,
    // then merge greedily for fixed iterations with deterministic order
    let mut community: Vec<usize> = (0..n).collect();

    // Simple modularity-maximizing merge: try all pairs, keep best
    // This is O(n^2) but fine for typical graph sizes (< 5000 nodes)
    let mut improved = true;
    let mut iterations = 0;
    while improved && iterations < 20 {
        improved = false;
        iterations += 1;
        for node in 0..n {
            let current_comm = community[node];
            let mut best_comm = current_comm;
            let mut best_gain = 0.0_f64;

            // Find neighboring communities
            let mut neighbor_comms: Vec<usize> = edges.iter()
                .filter_map(|&(a, b)| {
                    if a == node { Some(community[b]) }
                    else if b == node { Some(community[a]) }
                    else { None }
                })
                .collect();
            neighbor_comms.sort();
            neighbor_comms.dedup();

            for &nc in &neighbor_comms {
                if nc == current_comm { continue; }
                let gain = modularity_gain(node, nc, &community, &edges, &degree, m);
                if gain > best_gain {
                    best_gain = gain;
                    best_comm = nc;
                }
            }
            if best_comm != current_comm {
                community[node] = best_comm;
                improved = true;
            }
        }
    }

    // Compute Q
    let q = compute_q(&community, &edges, &degree, m);
    let q_ref = 0.75_f64;
    (q.max(0.0) / q_ref).min(1.0)
}

fn modularity_gain(
    node: usize,
    target_comm: usize,
    community: &[usize],
    edges: &[(usize, usize)],
    degree: &[usize],
    m: f64,
) -> f64 {
    // ΔQ when moving node to target_comm
    // Simplified: count edges to target_comm vs current_comm
    let mut edges_to_target = 0;
    let mut edges_to_current = 0;
    let current_comm = community[node];

    for &(a, b) in edges {
        let other = if a == node { b } else if b == node { a } else { continue };
        let other_comm = community[other];
        if other_comm == target_comm { edges_to_target += 1; }
        if other_comm == current_comm && other != node { edges_to_current += 1; }
    }

    let sum_target: usize = community.iter().enumerate()
        .filter(|(_, &c)| c == target_comm)
        .map(|(i, _)| degree[i])
        .sum();

    let ki = degree[node] as f64;
    let sum_t = sum_target as f64;

    // Simplified ΔQ formula
    (edges_to_target as f64 - edges_to_current as f64) / m
        - ki * (sum_t - ki) / (2.0 * m * m)
}

fn compute_q(community: &[usize], edges: &[(usize, usize)], degree: &[usize], m: f64) -> f64 {
    if m == 0.0 { return 0.0; }
    let mut q = 0.0_f64;
    for &(i, j) in edges {
        if community[i] == community[j] {
            let ki = degree[i] as f64;
            let kj = degree[j] as f64;
            q += 1.0 - ki * kj / (2.0 * m);
        }
    }
    q / m
}
