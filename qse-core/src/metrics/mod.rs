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
    // Use internal_graph — excludes stdlib/third-party nodes
    let g = &result.internal_graph;
    let n = g.node_count();
    let e = g.edge_count();

    let mod_score  = modularity::compute(g);
    let acy_score  = acyclicity::compute(g, &result.internal_nodes);
    let stab_score = stability::compute(g);
    let coh_score  = cohesion::compute(&result.classes, &result.language);

    // Empirically calibrated weights (n=279 OSS repos, bug_lead_time ≤14d ground truth)
    // CV improvement vs equal weights: +17% (mean r: -0.143 → -0.167)
    //   Stability   = 0.55  dominant predictor, ΔCV=-0.048 when removed
    //   Modularity  = 0.20  important signal,   ΔCV=-0.021 when removed
    //   Acyclicity  = 0.20  best pair with S,   neutral alone
    //   Cohesion    = 0.05  redundant,          ΔCV=+0.022 without it
    const W_MOD: f64 = 0.20;
    const W_ACY: f64 = 0.20;
    const W_STA: f64 = 0.55;
    const W_COH: f64 = 0.05;

    let agq = W_MOD * mod_score
            + W_ACY * acy_score
            + W_STA * stab_score
            + W_COH * coh_score;

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
