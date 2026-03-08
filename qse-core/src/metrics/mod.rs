mod modularity;
mod acyclicity;
mod stability;
mod cohesion;

use crate::scanner::ScanResult;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AGQMetrics {
    pub modularity:  f64,
    pub acyclicity:  f64,
    pub stability:   f64,
    pub cohesion:    f64,
    pub agq_score:   f64,
    pub nodes:       usize,
    pub edges:       usize,
}

pub fn compute_agq(result: &ScanResult) -> AGQMetrics {
    let g = &result.graph;
    let n = g.node_count();
    let e = g.edge_count();

    let mod_score  = modularity::compute(g);
    let acy_score  = acyclicity::compute(g);
    let stab_score = stability::compute(g);
    let coh_score  = cohesion::compute(&result.classes);

    let agq = (mod_score + acy_score + stab_score + coh_score) / 4.0;

    AGQMetrics {
        modularity:  mod_score,
        acyclicity:  acy_score,
        stability:   stab_score,
        cohesion:    coh_score,
        agq_score:   agq,
        nodes: n,
        edges: e,
    }
}
