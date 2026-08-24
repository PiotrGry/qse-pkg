mod acyclicity;
mod cohesion;
mod modularity;
mod stability;

use crate::scanner::ScanResult;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AGQMetrics {
    pub modularity: f64,
    pub acyclicity: f64,
    pub stability: f64,
    /// None when the language/scan has no valid class-cohesion measurement.
    pub cohesion: Option<f64>,
    pub agq_score: f64,
    pub nodes: usize,
    pub edges: usize,
}

pub fn compute_agq(result: &ScanResult) -> AGQMetrics {
    // `internal_graph` is an induced graph containing scanned nodes only.
    let g = &result.internal_graph;
    let n = g.node_count();
    let e = g.edge_count();

    let mod_score = modularity::compute(g);
    let acy_score = acyclicity::compute(g);
    let stab_score = stability::compute(g, result.language);
    let coh_score = cohesion::compute(&result.classes, result.language);

    const W_MOD: f64 = 0.20;
    const W_ACY: f64 = 0.20;
    const W_STA: f64 = 0.55;
    const W_COH: f64 = 0.05;

    let mut weighted = W_MOD * mod_score + W_ACY * acy_score + W_STA * stab_score;
    let mut measured_weight = W_MOD + W_ACY + W_STA;
    if let Some(cohesion) = coh_score {
        weighted += W_COH * cohesion;
        measured_weight += W_COH;
    }
    // Missing components never receive a perfect-value substitution.
    let agq = weighted / measured_weight;

    AGQMetrics {
        modularity: mod_score,
        acyclicity: acy_score,
        stability: stab_score,
        cohesion: coh_score,
        agq_score: agq,
        nodes: n,
        edges: e,
    }
}
