# Phase 3b — Weight Optimization (LORO Cross-Validation)

**Pairs:** 124 from ['black', 'pip', 'pre-commit', 'scrapy', 'streamlit']

## Per-component reverse-drop signal

On reverse direction: did metric DROP when going merge→parent?
(i.e. metric was better at merge state, worse after undoing).

| Metric | archfix-rev rate | control-rev rate | diff | perm p |
|---|---|---|---|---|
| ΔModularity | 42% | 12% | +30.11% | 0.0000 |
| ΔAcyclicity | 16% | 0% | +16.13% | 0.0010 |
| ΔStability | 42% | 16% | +25.81% | 0.0025 |
| ΔCohesion | 0% | 0% | +0.00% | 1.0000 |
| ΔAGQ | 42% | 13% | +29.03% | 0.0000 |

## Current default weights — LORO performance

Weights: M=0.20 A=0.20 S=0.55 C=0.05
- avg held-out archfix detect rate: **29%**
- avg held-out control fail rate:   **6%**
- avg held-out diff:                **+24%**

## Grid-search optimal weights (LORO CV, step=0.1)

| Held-out | M | A | S | C | train Δ | held-out Δ | af-rate | ct-rate |
|---|---|---|---|---|---|---|---|---|
| black | 0.10 | 0.30 | 0.30 | 0.30 | +23% | +50% | 50% | 0% |
| pip | 0.00 | 0.10 | 0.10 | 0.80 | +48% | -4% | 12% | 17% |
| pre-commit | 0.00 | 0.10 | 0.10 | 0.80 | +27% | +7% | 20% | 13% |
| scrapy | 0.20 | 0.00 | 0.50 | 0.30 | +23% | +25% | 25% | 0% |
| streamlit | 0.10 | 0.30 | 0.00 | 0.60 | +29% | -8% | 0% | 8% |

- **avg held-out archfix detect**: **22%** (default: 29%)
- **avg held-out control fail**:   **8%** (default: 6%)
- **avg held-out diff**:           **+14%** (default: +24%)

## Verdict

❌ No improvement (-10%). Default weights are competitive with grid-searched optima.