"""
AGQ Enhanced Metrics — product-ready extensions to base AGQ.

Addresses limitations discovered in 235-repo cross-language benchmark:
  1. AGQ-z          : language-normalized score (z-score per language)
  2. Fingerprint    : architectural pattern classification
  3. CycleSeverity  : % of nodes in cycles (not just binary acy < 1)
  4. ChurnRisk      : composite predictor for uneven change distribution
  5. AGQ-adj        : size-adjusted score (normalized to 500-node baseline)

New in perplexity/experiment_total (iter 1-2, 14-repo Python OSS pilot):
  6. GraphDensityScore : 1 - min(1, density/0.020)  r=+0.881 vs bug_lead_time
  7. SCCEntropyScore   : H_SCC / log2(n)             r=-0.640 vs hotspot_ratio
  8. HubScore          : 1 - hub_ratio               r=+0.609 vs hotspot_ratio
  9. AGQ-process       : composite of 6+7+8, weighted by empirical correlations

All derived from base AGQ metrics or graph structure — no git history required.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Language baselines (computed from 235-repo benchmark)
# ---------------------------------------------------------------------------

LANGUAGE_BASELINES: Dict[str, Dict[str, float]] = {
    "Python": {"mean": 0.7494, "std": 0.0619,
               "p10": 0.67, "p25": 0.71, "p50": 0.75, "p75": 0.79, "p90": 0.82},
    "Java":   {"mean": 0.6224, "std": 0.0938,
               "p10": 0.52, "p25": 0.56, "p50": 0.62, "p75": 0.68, "p90": 0.73},
    "Go":     {"mean": 0.8166, "std": 0.0627,
               "p10": 0.74, "p25": 0.78, "p50": 0.82, "p75": 0.86, "p90": 0.88},
}

# Size quartile baselines (nodes) for size-adjusted scoring
SIZE_QUARTILES = {
    "Python": {"q1": 80, "q2": 350, "q3": 1300},
    "Java":   {"q1": 350, "q2": 1400, "q3": 5000},
    "Go":     {"q1": 100, "q2": 500, "q3": 2000},
}


# ---------------------------------------------------------------------------
# 1. AGQ-z — Language-normalized score
# ---------------------------------------------------------------------------

def compute_agq_z(agq: float, language: str) -> Optional[float]:
    """Z-score of AGQ relative to language distribution.

    AGQ-z = (AGQ - mean_lang) / std_lang

    AGQ-z = 0.0  → exactly average for this language
    AGQ-z = +2.0 → top 2.3% for this language
    AGQ-z = -2.0 → bottom 2.3% for this language

    Allows fair comparison: kubernetes (Go, z=-2.54) is the WORST
    in its language class despite absolute AGQ=0.657.
    """
    baseline = LANGUAGE_BASELINES.get(language)
    if not baseline:
        return None
    return (agq - baseline["mean"]) / baseline["std"]


def compute_agq_percentile(agq: float, language: str) -> Optional[float]:
    """Approximate percentile of AGQ within language (0-100)."""
    baseline = LANGUAGE_BASELINES.get(language)
    if not baseline:
        return None
    z = compute_agq_z(agq, language)
    if z is None:
        return None
    # Approximate CDF using erf
    p = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return round(p * 100, 1)


# ---------------------------------------------------------------------------
# 2. Architectural Fingerprint
# ---------------------------------------------------------------------------

FINGERPRINT_DESCRIPTIONS = {
    "CLEAN":        "Structurally pure — no cycles, high cohesion, clear layers. "
                    "Named for mathematical graph properties, NOT Uncle Bob's Clean Architecture. "
                    "Dominant in Go (enforced by language/ecosystem conventions).",
    "LAYERED":      "Layered architecture — good stability and acyclicity, medium cohesion",
    "MODERATE":     "Moderate architecture — no strong pathologies, room for improvement",
    "LOW_COHESION": "Low cohesion — classes do too many things, consider splitting (Java OOP)",
    "FLAT":         "Flat architecture — no clear layering, all modules on same level",
    "TANGLED":      "Tangled — low cohesion AND cycles (Java monolith smell)",
    "CYCLIC":       "Cyclic dependencies — acyclicity critical, refactoring needed",
    "UNKNOWN":      "Unknown pattern",
}

FINGERPRINT_PRIORITY = {
    "CLEAN": 0, "LAYERED": 1, "MODERATE": 2,
    "FLAT": 3, "LOW_COHESION": 4, "CYCLIC": 5, "TANGLED": 6, "UNKNOWN": 7,
}


def compute_fingerprint(modularity: float, acyclicity: float,
                        stability: float, cohesion: float) -> str:
    """Classify architectural pattern from AGQ components.

    Rules derived from clustering 235 repos:
      CLEAN:        acy=1, coh=1, stab>0.8        (Go-style, interfaces)
      LAYERED:      acy=1, stab>0.7, coh>0.5      (Python/Spring well-structured)
      TANGLED:      acy<0.95, coh<0.3             (Java OOP monolith with cycles)
      CYCLIC:       acy<0.95, coh>=0.3            (has cycles, not fully tangled)
      LOW_COHESION: acy>=0.95, coh<0.4            (Java without cycles but fat classes)
      FLAT:         acy>=0.95, stab<0.3, coh>=0.4 (no clear layers)
      LAYERED:      acy>=0.95, stab>0.7, coh>=0.4
      MODERATE:     everything else
    """
    if acyclicity == 1.0 and cohesion >= 0.95 and stability > 0.80:
        return "CLEAN"
    if acyclicity < 0.95 and cohesion < 0.30:
        return "TANGLED"
    if acyclicity < 0.95:
        return "CYCLIC"
    if cohesion < 0.40:
        return "LOW_COHESION"
    if stability < 0.30:
        return "FLAT"
    if stability > 0.70 and cohesion >= 0.50:
        return "LAYERED"
    return "MODERATE"


def fingerprint_description(fp: str) -> str:
    return FINGERPRINT_DESCRIPTIONS.get(fp, "Unknown pattern")


# ---------------------------------------------------------------------------
# 3. Cycle Severity Index
# ---------------------------------------------------------------------------

def compute_cycle_severity(acyclicity: float) -> Dict[str, object]:
    """Detailed cycle severity from acyclicity score.

    acyclicity = 1 - (largest_SCC_size / total_nodes)
    → severity = 1 - acyclicity = fraction of nodes in largest cycle

    Returns dict with:
      severity_ratio: float  — fraction of nodes in cycles [0,1]
      severity_level: str    — NONE/LOW/MEDIUM/HIGH/CRITICAL
      message:        str    — human-readable description
    """
    sev = max(0.0, 1.0 - acyclicity)

    if sev == 0.0:
        level = "NONE"
        msg = "No cyclic dependencies detected."
    elif sev < 0.01:
        level = "LOW"
        msg = f"Minor cycles: <1% of modules involved. Easy to fix."
    elif sev < 0.05:
        level = "MEDIUM"
        msg = f"Moderate cycles: {sev*100:.1f}% of modules involved. Schedule refactoring."
    elif sev < 0.15:
        level = "HIGH"
        msg = f"Significant cycles: {sev*100:.1f}% of modules involved. Prioritize fix."
    else:
        level = "CRITICAL"
        msg = f"Critical cycles: {sev*100:.1f}% of modules involved. Architectural redesign needed."

    return {
        "severity_ratio": round(sev, 4),
        "severity_pct": round(sev * 100, 1),
        "severity_level": level,
        "message": msg,
    }


# ---------------------------------------------------------------------------
# 4. Churn Risk Score
# ---------------------------------------------------------------------------

def compute_churn_risk(acyclicity: float, stability: float,
                       modularity: float) -> Dict[str, object]:
    """Predict likelihood of uneven code churn distribution.

    UPDATED in perplexity/experiment_total iter-2:
    Pilot study (n=14 Python OSS repos) identified stronger structural
    predictors via graph-level analysis:
      - GraphDensity: r=+0.815 vs hotspot_ratio (p=0.0004)
      - HubRatio:     r=+0.609 vs hotspot_ratio (p=0.021)
      - SCCEntropy:   r=-0.640 vs hotspot_ratio (p=0.014)

    churn_risk = 0.50*(1-acy) + 0.30*(1-stab) + 0.20*(1-mod)
    [graph-level predictors available via compute_process_risk_score()]

    Validated: r_pearson=+0.078 with churn_gini (original 235-repo).
    For stronger prediction use ProcessRisk which includes graph-level metrics.
    """
    score = 1.0 - (0.5 * acyclicity + 0.3 * stability + 0.2 * modularity)
    score = max(0.0, min(1.0, score))

    if score < 0.10:
        level = "LOW"
        msg = "Low architectural risk of churn hotspots."
    elif score < 0.20:
        level = "MEDIUM"
        msg = "Moderate risk of uneven change distribution."
    elif score < 0.30:
        level = "HIGH"
        msg = "High risk: architectural issues likely causing hotspot files."
    else:
        level = "CRITICAL"
        msg = "Critical: architecture structure strongly predicts churn hotspots."

    return {
        "churn_risk_score": round(score, 4),
        "churn_risk_level": level,
        "message": msg,
    }


# ---------------------------------------------------------------------------
# 5. Size-adjusted AGQ
# ---------------------------------------------------------------------------

_LOG_BASELINE = math.log(500)  # normalize to 500-node reference project


def compute_agq_size_adjusted(agq: float, n_nodes: int) -> float:
    """Size-adjusted AGQ — removes bias where larger repos score lower.

    Uses log-normalization to 500-node baseline:
      AGQ_adj = AGQ * log(500) / log(n_nodes)   [capped at 1.0]

    Interpretation:
      AGQ_adj > AGQ  → small project, adjusted up to 500-node equivalent
      AGQ_adj < AGQ  → large project, adjusted down
      AGQ_adj = AGQ  → exactly 500-node project

    Note: use with caution — very small projects (<20 nodes) get
    unrealistically high adjusted scores. Recommended range: 50-10000 nodes.
    """
    if n_nodes < 10:
        return agq
    log_n = math.log(max(n_nodes, 2))
    adj = agq * _LOG_BASELINE / log_n
    return round(min(1.0, max(0.0, adj)), 4)


# ---------------------------------------------------------------------------
# Composite enhanced report
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 6-8. Graph-level process risk predictors
#      Validated: perplexity/experiment_total pilot, 14 Python OSS repos
# ---------------------------------------------------------------------------

# Calibration constants (perplexity pilot iter-2, Python OSS n=14)
DENSITY_REFERENCE     = 0.020   # p90 of pilot — above = high risk
SCC_ENTROPY_WEIGHT    = 0.3005  # ∝ |r_s|=0.640 vs hotspot_ratio
GRAPH_DENSITY_WEIGHT  = 0.4136  # ∝ |r_s|=0.881 vs bug_lead_time
HUB_RATIO_WEIGHT      = 0.2859  # ∝ |r_s|=0.609 vs hotspot_ratio


def compute_graph_density_score(graph_density: float) -> float:
    """Normalize graph density to [0,1] quality score.

    density_score = 1 - min(1, density / 0.020)
    → 1.0 = sparse graph (best), 0.0 = very dense (worst)

    Reference threshold 0.020 = p90 of 14-repo Python pilot.
    Empirical: r=+0.881 vs bug_mean_days, r=+0.815 vs hotspot_ratio.
    """
    return round(max(0.0, 1.0 - min(1.0, graph_density / DENSITY_REFERENCE)), 4)


def compute_scc_entropy_score(scc_entropy: float, n_nodes: int) -> float:
    """Normalize SCC entropy to [0,1] quality score.

    scc_entropy_score = min(1, H_SCC / log2(n_nodes))
    → 1.0 = maximally modular (each node own SCC, DAG)
    → 0.0 = one giant SCC (everything tangled)

    Empirical: r=-0.640 vs hotspot_ratio (negative = higher entropy → fewer hotspots).
    """
    import math
    if n_nodes <= 1:
        return 1.0
    max_h = math.log2(max(n_nodes, 2))
    if max_h <= 0:
        return 1.0
    return round(min(1.0, max(0.0, scc_entropy / max_h)), 4)


def compute_hub_score(hub_ratio: float) -> float:
    """Normalize hub_ratio to [0,1] quality score.

    hub_score = 1 - hub_ratio
    → 1.0 = no hubs (best), 0.0 = all nodes are hubs (worst)

    hub_ratio = fraction of nodes with in_degree > 2 * mean_in_degree.
    Empirical: r=+0.609 vs hotspot_ratio.
    """
    return round(max(0.0, 1.0 - min(1.0, hub_ratio)), 4)


def compute_process_risk_score(
    graph_density: float,
    scc_entropy: float,
    hub_ratio: float,
    n_nodes: int,
) -> Dict[str, object]:
    """Composite process risk score from graph-level structural metrics.

    Validated in perplexity/experiment_total pilot (iter 1-2):
      14 Python OSS repos, Spearman correlations vs hotspot_ratio/bug_lead_time

    process_risk = 1 - (
        w_density * density_score
      + w_scc     * scc_entropy_score
      + w_hub     * hub_score
    )

    Weights calibrated proportional to |r_s|:
      w_density = 0.4136  (r_s=0.881)
      w_scc     = 0.3005  (r_s=0.640)
      w_hub     = 0.2859  (r_s=0.609)

    Returns:
      process_risk_score : float [0,1] — 0=low risk, 1=high risk
      process_risk_level : str   — LOW/MEDIUM/HIGH/CRITICAL
      density_score      : float [0,1]
      scc_entropy_score  : float [0,1]
      hub_score          : float [0,1]
      message            : str
    """
    ds  = compute_graph_density_score(graph_density)
    ses = compute_scc_entropy_score(scc_entropy, n_nodes)
    hs  = compute_hub_score(hub_ratio)

    quality = (
        GRAPH_DENSITY_WEIGHT * ds
        + SCC_ENTROPY_WEIGHT * ses
        + HUB_RATIO_WEIGHT   * hs
    )
    risk = round(1.0 - quality, 4)

    if risk < 0.15:
        level = "LOW"
        msg   = "Low process risk: sparse graph, modular SCCs, few hubs."
    elif risk < 0.35:
        level = "MEDIUM"
        msg   = "Moderate risk: some structural coupling detected."
    elif risk < 0.55:
        level = "HIGH"
        msg   = "High risk: dense graph or dominant hubs — likely hotspots."
    else:
        level = "CRITICAL"
        msg   = "Critical: graph structure strongly predicts maintenance issues."

    return {
        "process_risk_score": risk,
        "process_risk_level": level,
        "density_score":      ds,
        "scc_entropy_score":  ses,
        "hub_score":          hs,
        "message":            msg,
    }


@dataclass
class AGQEnhanced:
    """Full enhanced AGQ report for a single repository."""
    # Base metrics
    agq_score: float
    modularity: float
    acyclicity: float
    stability: float
    cohesion: float
    nodes: int
    language: str

    # Enhanced (original)
    agq_z: Optional[float]             # language-normalized
    agq_percentile: Optional[float]    # percentile within language
    agq_size_adjusted: float           # size-normalized
    fingerprint: str                   # architectural pattern
    fingerprint_description: str
    cycle_severity: Dict               # detailed cycle analysis
    churn_risk: Dict                   # churn hotspot risk

    # New — graph-level process risk (perplexity/experiment_total iter 1-2)
    process_risk: Optional[Dict]       # graph density + SCC entropy + hub ratio

    def summary(self) -> str:
        lines = [
            f"AGQ: {self.agq_score:.4f}  "
            f"({self.language} percentile: {self.agq_percentile or '?'}%,  "
            f"z={self.agq_z:+.2f})" if self.agq_z else "",
            f"Pattern: {self.fingerprint} — {self.fingerprint_description}",
            f"Cycles: {self.cycle_severity['severity_level']} "
            f"({self.cycle_severity['severity_pct']}% nodes) — "
            f"{self.cycle_severity['message']}",
            f"Churn risk: {self.churn_risk['churn_risk_level']} "
            f"(score={self.churn_risk['churn_risk_score']:.3f}) — "
            f"{self.churn_risk['message']}",
        ]
        return "\n".join(l for l in lines if l)

    def to_dict(self) -> dict:
        d = {
            "agq_score": self.agq_score,
            "agq_z": round(self.agq_z, 4) if self.agq_z is not None else None,
            "agq_percentile": self.agq_percentile,
            "agq_size_adjusted": self.agq_size_adjusted,
            "fingerprint": self.fingerprint,
            "cycle_severity": self.cycle_severity,
            "churn_risk": self.churn_risk,
            "language": self.language,
            "nodes": self.nodes,
        }
        if self.process_risk is not None:
            d["process_risk"] = self.process_risk
        return d


def compute_agq_enhanced(
    agq: float, modularity: float, acyclicity: float,
    stability: float, cohesion: float,
    nodes: int, language: str = "Python",
    # New graph-level metrics (optional — backward compatible)
    graph_density: Optional[float] = None,
    scc_entropy: Optional[float] = None,
    hub_ratio: Optional[float] = None,
) -> AGQEnhanced:
    """Compute all enhanced metrics from base AGQ components.

    graph_density, scc_entropy, hub_ratio are optional new metrics
    validated in perplexity/experiment_total pilot (iter 1-2).
    If not provided, process_risk is None (backward compatible).
    """
    fp = compute_fingerprint(modularity, acyclicity, stability, cohesion)

    pr = None
    if graph_density is not None and scc_entropy is not None and hub_ratio is not None:
        pr = compute_process_risk_score(graph_density, scc_entropy, hub_ratio, nodes)

    return AGQEnhanced(
        agq_score=agq, modularity=modularity, acyclicity=acyclicity,
        stability=stability, cohesion=cohesion, nodes=nodes, language=language,
        agq_z=compute_agq_z(agq, language),
        agq_percentile=compute_agq_percentile(agq, language),
        agq_size_adjusted=compute_agq_size_adjusted(agq, nodes),
        fingerprint=fp,
        fingerprint_description=fingerprint_description(fp),
        cycle_severity=compute_cycle_severity(acyclicity),
        churn_risk=compute_churn_risk(acyclicity, stability, modularity),
        process_risk=pr,
    )
