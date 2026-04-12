# Experiments

## Java-S Experiment

**Goal**: Find optimal AGQ weight configuration for Java repos.

**Protocol constraints**:
- Max 5 iterations, stop after 2 consecutive no-improvement
- No non-linear models, no brute-force optimization
- No new metrics without justification
- Stop if overfit/tautology/instability detected

**Status**: P4 — blocked on GT expansion (now complete at n=59). Next step is to re-run on expanded GT.

**Winner (from original n=29 GT)**: v3c with equal 0.20 weights. Reserve variant: v2 (0.30/0.20/0.15/0.15/0.20).

## Python Deep-Dive

- 30 Python repos scanned
- Python-specific weights with flat_score component
- Results in `artifacts/python_deepdive_results.json`

## Jolak Cross-Validation (P1)

**Goal**: Validate Java scanner against 8 repos from Jolak et al. (2025) study.

**Results**:
- 8/8 repos scanned successfully
- Mean AGQ v3c = 0.535 (between GT-POS and GT-NEG — expected)
- S varies widely [0.065–0.954]
- 4/5 Jolak findings CONFIRMED, 1 PLAUSIBLE

**Key finding**: CD gap (Jolak repos CD=0.316 < GT-NEG CD=0.380) suggests GT may under-represent enterprise middleware.

## Java GT Expansion (P0) ✅

**Goal**: Expand Java GT from n=29 to n≥50.

**Results** (April 2026):
- 30 new repos scanned, panel-rated, merged
- Expanded GT: n=59 (31 POS, 28 NEG)
- MW p=0.000221, Spearman ρ=0.380, partial_r=0.447, AUC=0.767
- Gap narrowed 0.115→0.085 (expected with more diversity)
- All significance tests remain p<0.01
- Commit: b336496
