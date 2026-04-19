# AI-Drift Firewall — Architecture Audit

**Repository:** `base`  
**Generated:** 2026-04-19T21:05:24+00:00  
**Scan:** 14 modules, 10 dependencies

## Executive summary

- **Health score:** **95.0/100** (🟢 Healthy)
- **Violations:** 1 across 1 rule(s)
- **Breakdown:** BOUNDARY_LEAK: 1
- **Prioritized risks:** P1=0  P2=0  P3=2  (top 10 shown below)

## Recommendations

- **P3 — Backlog:** 2 low-risk components under observation — track trend, address if they grow.

## Top at-risk components

| Priority | Risk | Module | Rules | Reason |
|---|---|---|---|---|
| **P3** | 10 | `payments_api.gateway` | BOUNDARY_LEAK | Flagged by BOUNDARY_LEAK. |
| **P3** | 10 | `src.infrastructure.payments_core` | BOUNDARY_LEAK | Flagged by BOUNDARY_LEAK. |

## Raw violations

<details><summary>Expand full list</summary>

- **[BOUNDARY_LEAK]** `payments_api.gateway` → `src.infrastructure.payments_core`  
  - *Detail:* Caller payments_api.gateway is not in allowed_callers for protected src.infrastructure.payments_core*  
  - *Axiom:* encapsulation (MDL: protected partition compressed through its API surface only; flow: external callers must go through named entry points)  
  - *Fix:* Call the public API of src.infrastructure.payments_core* instead, or add payments_api.gateway to allowed_callers if this access is intentional.

</details>

---

*Scoring:* risk = pressure × 80 + 20 for SCC membership, where pressure = min(1, Σ severity / max(20, 0.2 × edges)) and severity weights are CYCLE_NEW=3, LAYER_VIOLATION=2, BOUNDARY_LEAK=2.5. Priority P1 at score ≥ 60 or any SCC membership; P2 at 30–59; P3 below. Health = (1 − min(1, violations / max(20, 0.2 × edges))) × 100; fewer than 5 violations are capped at yellow (70) unless they exceed half the edges.