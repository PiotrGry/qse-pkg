//! Deterministic Louvain modularity on a simple undirected projection.

use petgraph::graph::DiGraph;
use std::collections::{BTreeMap, BTreeSet};

const EPSILON: f64 = 1.0e-12;

#[derive(Debug)]
struct LevelGraph {
    /// Symmetric weighted adjacency. Diagonal values are twice self-loop weight.
    adjacency: Vec<BTreeMap<usize, f64>>,
    /// Original graph nodes represented by each level node.
    groups: Vec<Vec<usize>>,
}

pub fn compute(graph: &DiGraph<String, ()>) -> f64 {
    let n = graph.node_count();
    if n <= 1 {
        return 1.0;
    }

    let edges = simple_edges(graph);
    if edges.is_empty() {
        return 1.0;
    }
    if n < 10 {
        return 0.5;
    }

    let mut level = initial_level(n, &edges);
    let mut best_partition: Vec<usize> = (0..n).collect();
    let mut best_q = modularity_score(n, &edges, &best_partition);

    loop {
        let assignment = local_move(&level.adjacency);
        let merged_groups = merge_groups(&level.groups, &assignment);
        let mut partition = vec![0usize; n];
        for (community, members) in merged_groups.iter().enumerate() {
            for &member in members {
                partition[member] = community;
            }
        }
        let q = modularity_score(n, &edges, &partition);
        let improvement = q - best_q;
        if q > best_q + EPSILON {
            best_q = q;
            best_partition = partition;
        }

        if merged_groups.len() == level.adjacency.len() || improvement <= EPSILON {
            break;
        }
        level = aggregate_level(&level.adjacency, merged_groups, &assignment);
    }

    let q = modularity_score(n, &edges, &best_partition);
    (q.max(0.0) / 0.75).min(1.0)
}

fn simple_edges(graph: &DiGraph<String, ()>) -> Vec<(usize, usize)> {
    let mut edges = BTreeSet::new();
    for edge in graph.edge_indices() {
        let Some((source, target)) = graph.edge_endpoints(edge) else {
            continue;
        };
        let (a, b) = (source.index(), target.index());
        if a != b {
            edges.insert((a.min(b), a.max(b)));
        }
    }
    edges.into_iter().collect()
}

fn initial_level(n: usize, edges: &[(usize, usize)]) -> LevelGraph {
    let mut adjacency = vec![BTreeMap::new(); n];
    for &(a, b) in edges {
        *adjacency[a].entry(b).or_default() += 1.0;
        *adjacency[b].entry(a).or_default() += 1.0;
    }
    LevelGraph {
        adjacency,
        groups: (0..n).map(|node| vec![node]).collect(),
    }
}

fn local_move(adjacency: &[BTreeMap<usize, f64>]) -> Vec<usize> {
    let n = adjacency.len();
    let degree: Vec<f64> = adjacency
        .iter()
        .map(|neighbors| neighbors.values().sum())
        .collect();
    let m2 = degree.iter().sum::<f64>();
    if m2 <= EPSILON {
        return (0..n).collect();
    }

    let mut community: Vec<usize> = (0..n).collect();
    let mut totals = degree.clone();
    for _ in 0..100 {
        let mut moved = false;
        for node in 0..n {
            let current = community[node];
            let node_degree = degree[node];
            totals[current] -= node_degree;

            let mut neighbor_weights: BTreeMap<usize, f64> = BTreeMap::new();
            for (&neighbor, &weight) in &adjacency[node] {
                if neighbor != node {
                    *neighbor_weights.entry(community[neighbor]).or_default() += weight;
                }
            }

            let mut best = current;
            let mut best_gain = 0.0;
            for (&candidate, &weight_in) in &neighbor_weights {
                let gain = weight_in - totals[candidate] * node_degree / m2;
                if gain > best_gain + EPSILON
                    || ((gain - best_gain).abs() <= EPSILON && gain > 0.0 && candidate < best)
                {
                    best = candidate;
                    best_gain = gain;
                }
            }

            totals[best] += node_degree;
            if best != current {
                community[node] = best;
                moved = true;
            }
        }
        if !moved {
            break;
        }
    }
    renumber(&community)
}

fn renumber(assignment: &[usize]) -> Vec<usize> {
    let mut mapping = BTreeMap::new();
    let mut next = 0usize;
    assignment
        .iter()
        .map(|community| {
            *mapping.entry(*community).or_insert_with(|| {
                let id = next;
                next += 1;
                id
            })
        })
        .collect()
}

fn merge_groups(groups: &[Vec<usize>], assignment: &[usize]) -> Vec<Vec<usize>> {
    let count = assignment
        .iter()
        .copied()
        .max()
        .map_or(0, |value| value + 1);
    let mut merged = vec![Vec::new(); count];
    for (node, &community) in assignment.iter().enumerate() {
        merged[community].extend_from_slice(&groups[node]);
    }
    merged
}

fn aggregate_level(
    adjacency: &[BTreeMap<usize, f64>],
    groups: Vec<Vec<usize>>,
    assignment: &[usize],
) -> LevelGraph {
    let mut aggregated = vec![BTreeMap::new(); groups.len()];
    for source in 0..adjacency.len() {
        for (&target, &weight) in &adjacency[source] {
            if source > target {
                continue;
            }
            let source_community = assignment[source];
            let target_community = assignment[target];
            if source == target {
                *aggregated[source_community]
                    .entry(source_community)
                    .or_default() += weight;
            } else if source_community == target_community {
                *aggregated[source_community]
                    .entry(source_community)
                    .or_default() += 2.0 * weight;
            } else {
                *aggregated[source_community]
                    .entry(target_community)
                    .or_default() += weight;
                *aggregated[target_community]
                    .entry(source_community)
                    .or_default() += weight;
            }
        }
    }
    LevelGraph {
        adjacency: aggregated,
        groups,
    }
}

fn modularity_score(n: usize, edges: &[(usize, usize)], partition: &[usize]) -> f64 {
    let m = edges.len() as f64;
    if m == 0.0 {
        return 0.0;
    }
    let community_count = partition.iter().copied().max().map_or(0, |value| value + 1);
    let mut degree = vec![0.0f64; n];
    let mut internal_edges = vec![0.0f64; community_count];
    for &(a, b) in edges {
        degree[a] += 1.0;
        degree[b] += 1.0;
        if partition[a] == partition[b] {
            internal_edges[partition[a]] += 1.0;
        }
    }
    let mut community_degree = vec![0.0f64; community_count];
    for node in 0..n {
        community_degree[partition[node]] += degree[node];
    }
    (0..community_count)
        .map(|community| {
            internal_edges[community] / m - (community_degree[community] / (2.0 * m)).powi(2)
        })
        .sum()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn graph_with_nodes(n: usize) -> DiGraph<String, ()> {
        let mut graph = DiGraph::new();
        for node in 0..n {
            graph.add_node(node.to_string());
        }
        graph
    }

    #[test]
    fn reciprocal_edges_equal_one_undirected_edge() {
        let mut one_way = graph_with_nodes(10);
        let nodes: Vec<_> = one_way.node_indices().collect();
        for i in 0..9 {
            one_way.add_edge(nodes[i], nodes[i + 1], ());
        }
        let mut reciprocal = one_way.clone();
        for i in 0..9 {
            reciprocal.add_edge(nodes[i + 1], nodes[i], ());
        }
        assert_eq!(compute(&one_way), compute(&reciprocal));
    }

    #[test]
    fn separated_cliques_have_modularity() {
        let mut graph = graph_with_nodes(10);
        let nodes: Vec<_> = graph.node_indices().collect();
        for start in [0usize, 5usize] {
            for a in start..(start + 5) {
                for b in (a + 1)..(start + 5) {
                    graph.add_edge(nodes[a], nodes[b], ());
                }
            }
        }
        graph.add_edge(nodes[4], nodes[5], ());
        // NetworkX Louvain finds the two cliques: Q=0.45238095, normalized by 0.75.
        assert!((compute(&graph) - 0.603_174_603_174_603_1).abs() < 1.0e-12);
    }

    #[test]
    fn repeated_runs_are_deterministic() {
        let mut graph = graph_with_nodes(12);
        let nodes: Vec<_> = graph.node_indices().collect();
        for i in 0..12 {
            graph.add_edge(nodes[i], nodes[(i + 1) % 12], ());
        }
        let expected = compute(&graph);
        for _ in 0..20 {
            assert_eq!(compute(&graph), expected);
        }
    }
}
