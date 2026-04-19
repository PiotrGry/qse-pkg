# AI-Drift Firewall — Architecture Audit

**Repository:** `sample-ai-drift-demo (Δ vs clean base)`  
**Generated:** 2026-04-19T20:11:35+00:00  
**Scan:** 10 modules, 10 dependencies

## Executive summary

- **Health score:** **90.0/100** (🟢 Healthy)
- **Violations:** 2 across 2 rule(s)
- **Breakdown:** CYCLE_NEW: 1, LAYER_VIOLATION: 1
- **Prioritized risks:** P1=2  P2=0  P3=0  (top 10 shown below)
- **Δ vs base:** 2 new, 0 existing, 0 resolved (renewal signal = new count trend)

## Recommendations

- **P1 — Break cycles:** extract shared interfaces to eliminate the SCC involving src.application.order_service, src.domain.order.

## Top at-risk components

| Priority | Risk | Δ | Module | Rules | Reason |
|---|---|---|---|---|---|
| **P1** | 40 | 🆕 new | `src.domain.order` | CYCLE_NEW, LAYER_VIOLATION | Participates in a cycle; also flagged by CYCLE_NEW, LAYER_VIOLATION. |
| **P1** | 40 | 🆕 new | `src.application.order_service` | CYCLE_NEW, LAYER_VIOLATION | Participates in a cycle; also flagged by CYCLE_NEW, LAYER_VIOLATION. |

## Raw violations

<details><summary>Expand full list</summary>

- **[CYCLE_NEW]** `src.domain.order` → `src.application.order_service`  
  - *Detail:* Cycle among 2 modules: src.application.order_service → src.domain.order  
  - *Axiom:* acyclicity (MDL: cycle increases graph description length; flow: bidirectional information transport blurs module boundaries)  
  - *Fix:* Extract a shared interface to break the cycle, or invert one dependency via dependency injection.
- **[LAYER_VIOLATION]** `src.domain.order` → `src.application.order_service`  
  - *Detail:* Edge src.domain.order (domain) → src.application.order_service (application) violates forbidden layering domain→application  
  - *Axiom:* layering (MDL: high-level layer compressed independently of low-level; flow: information must not flow inward to core)  
  - *Fix:* Define a port/interface in domain that application implements. Depend on the port, not the concrete.

</details>

---

*Scoring:* risk = normalized weighted violations (CYCLE_NEW=3, LAYER_VIOLATION=2, BOUNDARY_LEAK=2.5) + 20 for SCC membership. Priority P1 at score ≥ 60 or any SCC membership; P2 at 30–59; P3 below. Health score = 100 − (violations / (0.1 × edges)) × 100, clipped to [0, 100].