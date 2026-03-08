/// Newman modularity Q via O(m) Louvain algorithm.
/// Normalized: max(0, Q) / 0.75, returns 0.5 neutral for n<10 with edges.
use petgraph::graph::DiGraph;

pub fn compute(g: &DiGraph<String, ()>) -> f64 {
    let n = g.node_count();
    if n <= 1 { return 1.0; }

    // Build undirected symmetric adjacency for Louvain
    let mut adj: Vec<Vec<usize>> = vec![Vec::new(); n];
    let mut degree = vec![0usize; n];

    for e in g.edge_indices() {
        let (a, b) = g.edge_endpoints(e).unwrap();
        let ai = a.index();
        let bi = b.index();
        if ai == bi { continue; }
        adj[ai].push(bi);
        adj[bi].push(ai);
        degree[ai] += 1;
        degree[bi] += 1;
    }

    // Deduplicate adjacency lists
    for a in adj.iter_mut() {
        a.sort_unstable();
        a.dedup();
    }

    let m: usize = degree.iter().sum::<usize>() / 2;
    if m == 0 { return 1.0; }
    if n < 10 { return 0.5; }

    let m_f = m as f64;

    // Louvain phase 1: greedy O(m) per pass
    let mut community: Vec<usize> = (0..n).collect();
    // community_degree[c] = sum of degrees of nodes in community c
    let mut comm_deg: Vec<f64> = degree.iter().map(|&d| d as f64).collect();
    // community_internal[c] = sum of internal edges * 2
    let mut comm_int: Vec<f64> = vec![0.0; n];

    let mut improved = true;
    let mut iters = 0;
    while improved && iters < 50 {
        improved = false;
        iters += 1;

        for node in 0..n {
            let curr_c = community[node];
            let ki = degree[node] as f64;

            // Count edges to each neighbouring community
            let mut neigh_weight: std::collections::HashMap<usize, f64> =
                std::collections::HashMap::new();
            for &nb in &adj[node] {
                *neigh_weight.entry(community[nb]).or_insert(0.0) += 1.0;
            }

            // ΔQ for removing node from current community
            let ki_in_curr = *neigh_weight.get(&curr_c).unwrap_or(&0.0);
            let dq_remove = -(ki_in_curr / m_f)
                + (comm_deg[curr_c] - ki) * ki / (2.0 * m_f * m_f);

            // Find best community to move to
            let mut best_c = curr_c;
            let mut best_dq = 0.0_f64;

            for (&nc, &ki_in_nc) in &neigh_weight {
                if nc == curr_c { continue; }
                let dq = dq_remove
                    + (ki_in_nc / m_f)
                    - comm_deg[nc] * ki / (2.0 * m_f * m_f);
                if dq > best_dq {
                    best_dq = dq;
                    best_c = nc;
                }
            }

            if best_c != curr_c {
                // Move node from curr_c to best_c
                comm_deg[curr_c] -= ki;
                comm_int[curr_c] -= 2.0 * ki_in_curr;
                comm_deg[best_c] += ki;
                let ki_in_best = *neigh_weight.get(&best_c).unwrap_or(&0.0);
                comm_int[best_c] += 2.0 * ki_in_best;
                community[node] = best_c;
                improved = true;
            }
        }
    }

    // Compute final Q
    let mut q = 0.0_f64;
    for node in 0..n {
        let c = community[node];
        for &nb in &adj[node] {
            if community[nb] == c {
                let ki = degree[node] as f64;
                let kj = degree[nb] as f64;
                q += 1.0 - ki * kj / (2.0 * m_f);
            }
        }
    }
    q /= 2.0 * m_f; // each edge counted twice

    let q_ref = 0.75_f64;
    (q.max(0.0) / q_ref).min(1.0)
}
