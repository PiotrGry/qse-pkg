# Phase 3b — Weight Optimization (LORO Cross-Validation)

**Pairs:** 124 from ['black', 'pip', 'pre-commit', 'scrapy', 'streamlit']

## Per-component reverse-drop signal

On reverse direction: did metric DROP when going merge→parent?
(i.e. metric was better at merge state, worse after undoing).

| Metric | archfix-rev rate | control-rev rate | diff | perm p |
|---|---|---|---|---|
| ΔModularity | 42% | 12% | +30.11% | 0.0005 |
| ΔAcyclicity | 16% | 0% | +16.13% | 0.0020 |
| ΔStability | 42% | 16% | +25.81% | 0.0065 |
| ΔCohesion | 23% | 6% | +16.13% | 0.0120 |
| ΔAGQ | 45% | 13% | +32.26% | 0.0000 |

## Current default weights — LORO performance

Weights: M=0.20 A=0.20 S=0.55 C=0.05
- avg held-out archfix detect rate: **29%**
- avg held-out control fail rate:   **5%**
- avg held-out diff:                **+24%**

## Grid-search optimal weights (LORO CV, step=0.1)

| Held-out | M | A | S | C | train Δ | held-out Δ | af-rate | ct-rate |
|---|---|---|---|---|---|---|---|---|
| black | 0.10 | 0.20 | 0.20 | 0.50 | +37% | +50% | 50% | 0% |
| pip | 0.00 | 0.20 | 0.80 | 0.00 | +48% | -4% | 12% | 17% |
| pre-commit | 0.10 | 0.20 | 0.20 | 0.50 | +42% | +13% | 20% | 7% |
| scrapy | 0.10 | 0.00 | 0.10 | 0.80 | +38% | -12% | 12% | 25% |
| streamlit | 0.10 | 0.20 | 0.20 | 0.50 | +38% | +38% | 38% | 0% |

- **avg held-out archfix detect**: **26%** (default: 29%)
- **avg held-out control fail**:   **10%** (default: 5%)
- **avg held-out diff**:           **+17%** (default: +24%)

## Verdict

❌ No improvement (-7%). Default weights are competitive with grid-searched optima.