/// LCOM4-based cohesion — language-aware.
///
/// FIX 1: Languages without classes (Go, TypeScript structs) previously
/// returned 1.0 unconditionally when classes.is_empty(). This is correct
/// for Go (no classes, all functions are package-level → fully cohesive by
/// definition) but misleading when compared across languages.
///
/// New behavior:
///   - Go:   cohesion = 1.0 (structs have no methods in Go → neutral/perfect)
///   - Java/Python: LCOM4 as before
///   - classes.is_empty() AND language is Go → 1.0 (unchanged, correct)
///   - classes.is_empty() AND language is Python/Java → 0.75 (neutral, not perfect)
///     because empty class list means scanner found no classes to analyze —
///     likely a scanning failure, not genuinely cohesive code.
///
/// FIX 2: Classes with 0 or 1 method had LCOM4=1 by definition (single
/// connected component). Previously included in penalty calculation with
/// penalty=0. Now EXCLUDED from cohesion calculation entirely — a class
/// with 0 methods has no meaningful cohesion to measure.
use crate::scanner::{ClassInfo, Language};
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

pub fn compute(classes: &HashMap<String, ClassInfo>, language: &Language) -> f64 {
    // Go: structs have receiver methods but no instance fields shared between
    // methods in the Java/Python sense. LCOM4 is undefined → return neutral 1.0.
    // This is consistent with Python compute_cohesion([]) → 1.0.
    match language {
        Language::Go => return 1.0,
        _ => {}
    }

    if classes.is_empty() {
        // Python/Java with no classes detected = scanner issue or empty repo
        // Return neutral 0.75 instead of perfect 1.0 to signal uncertainty.
        return 0.75;
    }

    let penalties: Vec<f64> = classes.values()
        // FIX 2: exclude trivial classes (0 or 1 method — LCOM4 always 1)
        .filter(|c| c.method_attrs.len() >= 2)
        .map(|c| {
            let lcom = lcom4(&c.method_attrs);
            let excess = lcom.saturating_sub(1);
            (excess as f64 / 4.0).min(1.0)
        })
        .collect();

    // If all classes had < 2 methods, no meaningful cohesion data
    if penalties.is_empty() { return 1.0; }

    1.0 - penalties.iter().sum::<f64>() / penalties.len() as f64
}
