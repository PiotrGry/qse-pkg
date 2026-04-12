# Ground Truth

## Java GT

### Expanded GT (n=59) — `gt_java_expanded.json`

| Property | Value |
|----------|-------|
| Total repos | 59 |
| POS | 31 |
| NEG | 28 |
| POS mean AGQ | 0.571 |
| NEG mean AGQ | 0.486 |
| Gap | 0.085 |
| MW p-value | 0.000221 |
| Spearman ρ | 0.380 (p=0.003) |
| Partial r | 0.447 (p=0.0004) |
| AUC-ROC | 0.767 |

Composed of:
- **Original GT (n=29)**: 15 POS, 14 NEG — `gt_java_final_fixed.json`
- **Expansion batch (n=30)**: 16 POS, 14 NEG — added April 2026

### Panel Methodology

- 4 simulated expert reviewers (architecture purist, pragmatist, metrics-aware, industry practitioner)
- Each rates 1–10
- Panel score = mean of 4 ratings
- σ (disagreement) must be ≤ 2.0
- Label: panel ≥ 6.0 → POS, else NEG

### Per-Component Discrimination (expanded GT)

| Component | POS mean | NEG mean | Δ | MW p | Sig |
|-----------|----------|----------|---|------|-----|
| Modularity (M) | 0.668 | 0.648 | +0.021 | 0.226 | ns |
| Acyclicity (A) | 0.994 | 0.974 | +0.020 | 0.030 | * |
| Stability (S) | 0.344 | 0.238 | +0.106 | 0.016 | * |
| Cohesion (C) | 0.393 | 0.269 | +0.124 | 0.0002 | *** |
| Coupling Density (CD) | 0.454 | 0.299 | +0.155 | 0.004 | ** |

**Key insight**: C and CD are the strongest individual discriminators. M alone is not significant.

### Known Caveats

- **Utility libraries** (Guava, commons-lang, commons-collections): Score low AGQ despite being well-designed. Flat package structure → low CD. Need category-aware normalization.
- **Small NEG repos** (shopping-cart, training-monolith): Simple structure inflates M/CD. Expert panel catches this, metrics alone would not.

## Python GT

- `python_deepdive_results.json`: n=30 (13 POS, 17 NEG)
- Uses Python-specific v3c weights with flat_score component

## Jolak Cross-Validation

- 8 repos from Jolak et al. (2025)
- Scanned with pure-Python Java scanner
- Mean v3c = 0.535 (between GT-POS=0.585 and GT-NEG=0.470)
- 4/5 findings CONFIRMED, 1 PLAUSIBLE
- S varies widely [0.065–0.954]: Sentinel(0.065), motan(0.111), sofa-rpc(0.116)
