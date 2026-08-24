//! LCOM4-based cohesion for class-oriented languages.

use crate::scanner::{ClassInfo, Language};
use petgraph::algo::connected_components;
use petgraph::graph::UnGraph;
use std::collections::HashMap;

fn lcom4(method_attrs: &[(String, std::collections::HashSet<String>)]) -> usize {
    if method_attrs.len() <= 1 {
        return 1;
    }

    let mut graph: UnGraph<(), ()> = UnGraph::new_undirected();
    let nodes: Vec<_> = method_attrs.iter().map(|_| graph.add_node(())).collect();
    for i in 0..method_attrs.len() {
        for j in (i + 1)..method_attrs.len() {
            if !method_attrs[i].1.is_disjoint(&method_attrs[j].1) {
                graph.add_edge(nodes[i], nodes[j], ());
            }
        }
    }
    connected_components(&graph)
}

/// Returns `None` when cohesion is not measurable for this language or scan.
pub fn compute(classes: &HashMap<String, ClassInfo>, language: Language) -> Option<f64> {
    if language == Language::Go {
        return None;
    }

    let penalties: Vec<f64> = classes
        .values()
        // Interfaces and abstract contracts are not concrete state-sharing units.
        .filter(|class| !class.is_abstract && class.method_attrs.len() >= 2)
        .map(|class| {
            let excess = lcom4(&class.method_attrs).saturating_sub(1);
            (excess as f64 / 4.0).min(1.0)
        })
        .collect();

    if penalties.is_empty() {
        return None;
    }
    Some(1.0 - penalties.iter().sum::<f64>() / penalties.len() as f64)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    fn attrs(values: &[&str]) -> HashSet<String> {
        values.iter().map(|value| (*value).to_string()).collect()
    }

    #[test]
    fn method_calls_connect_components() {
        let methods = vec![
            (
                "save".to_string(),
                attrs(&["method:save", "method:validate"]),
            ),
            ("validate".to_string(), attrs(&["method:validate"])),
        ];
        assert_eq!(lcom4(&methods), 1);
    }

    #[test]
    fn independent_methods_form_islands() {
        let methods = vec![
            ("left".to_string(), attrs(&["method:left", "field:x"])),
            ("right".to_string(), attrs(&["method:right", "field:y"])),
        ];
        assert_eq!(lcom4(&methods), 2);
    }
}
