//! Package-level instability variance with language-specific package boundaries.

use crate::scanner::Language;
use petgraph::graph::{DiGraph, NodeIndex};
use std::collections::{BTreeMap, HashSet};

fn package(node: &str, language: Language) -> String {
    match language {
        Language::Go => node.split('/').next().unwrap_or(node).to_string(),
        Language::Python | Language::Java => {
            let mut parts = node.split('.');
            match (parts.next(), parts.next()) {
                (Some(first), Some(second)) => format!("{first}.{second}"),
                (Some(first), None) => first.to_string(),
                _ => node.to_string(),
            }
        }
    }
}

pub fn compute(graph: &DiGraph<String, ()>, language: Language) -> f64 {
    if graph.node_count() <= 1 {
        return 1.0;
    }

    let mut packages: BTreeMap<String, Vec<NodeIndex>> = BTreeMap::new();
    for node in graph.node_indices() {
        packages
            .entry(package(&graph[node], language))
            .or_default()
            .push(node);
    }
    if packages.len() <= 1 {
        return node_level(graph) * 0.5;
    }

    let instabilities: Vec<f64> = packages
        .values()
        .map(|members| {
            let member_set: HashSet<NodeIndex> = members.iter().copied().collect();
            let afferent = members
                .iter()
                .flat_map(|&node| graph.neighbors_directed(node, petgraph::Direction::Incoming))
                .filter(|node| !member_set.contains(node))
                .count();
            let efferent = members
                .iter()
                .flat_map(|&node| graph.neighbors_directed(node, petgraph::Direction::Outgoing))
                .filter(|node| !member_set.contains(node))
                .count();
            let total = afferent + efferent;
            if total == 0 {
                0.5
            } else {
                efferent as f64 / total as f64
            }
        })
        .collect();

    let raw = normalized_variance(&instabilities);
    if packages.len() == 2 {
        raw * 0.8
    } else {
        raw
    }
}

fn node_level(graph: &DiGraph<String, ()>) -> f64 {
    let instabilities: Vec<f64> = graph
        .node_indices()
        .map(|node| {
            let afferent = graph
                .neighbors_directed(node, petgraph::Direction::Incoming)
                .count();
            let efferent = graph
                .neighbors_directed(node, petgraph::Direction::Outgoing)
                .count();
            let total = afferent + efferent;
            if total == 0 {
                0.5
            } else {
                efferent as f64 / total as f64
            }
        })
        .collect();
    normalized_variance(&instabilities)
}

fn normalized_variance(values: &[f64]) -> f64 {
    if values.len() <= 1 {
        return 1.0;
    }
    let mean = values.iter().sum::<f64>() / values.len() as f64;
    let variance = values
        .iter()
        .map(|value| (value - mean).powi(2))
        .sum::<f64>()
        / values.len() as f64;
    (variance / 0.25).min(1.0)
}
