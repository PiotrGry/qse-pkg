# Experiments

## Java-S Experiment

**Goal**: Find optimal AGQ weight configuration for Java repos.

**Protocol constraints**:
- Max 5 iterations, stop after 2 consecutive no-improvement
- No non-linear models, no brute-force optimization
- No new metrics without justification
- Stop if overfit/tautology/instability detected

### Original run (n=29)

- 3 iterations, 13 variants tested
- **Winner**: v3c (0.20/0.20/0.20/0.20/0.20)
- **Reserve**: S15_C25_CD20 (0.20/0.20/0.15/0.25/0.20)
- Stopped: improvement within uncertainty (all CIs overlap)
- S monotonicity: ρ=1.00 (more S = better) — later shown to be artifact

### P4 Re-run (n=59) ✅

- 1 iteration (of 5 allowed), 18 variants tested (13 original + 5 new)
- **Winner CONFIRMED**: v3c (0.20/0.20/0.20/0.20/0.20)
- **Reserve**: S15_C25_CD20 (unchanged)
- partial_r = 0.447, bootstrap 95% CI = [0.278, 0.610]
- CI narrowed 40% vs n=29 run, but still too wide for variant discrimination
- **S monotonicity BROKEN**: ρ=0.00 on n=59 (was 1.00 on n=29). Inverted-U curve, peak at S=0.20
- Split-half: ALL variants unstable (Δ>0.15) — landscape is flat [0.40, 0.49]
- **Conclusion**: v3c wins by parsimony + S-peak alignment. Weight optimization closed.

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

## P4: Re-run Java-S on Expanded GT ✅

**Goal**: Test if v3c remains the best weight configuration on larger dataset.

**Results** (April 2026):
- 18 variants tested (13 original + 5 new explorations)
- v3c CONFIRMED as winner — no variant beats it outside bootstrap CI
- Key discovery: S-weight monotonicity broken (inverted-U, peak at S=0.20)
- Split-half instability: all variants Δ>0.15 between halves
- Recommendation: close weight optimization, focus on GT expansion or new components
- Commit: (P4 results committed)

## E13e: Shopizer QSE-Track Pilot ✅

**Goal**: Validate QSE-Track by refactoring Shopizer (1204 classes, 336 packages) until metrics show measurable change.

**Results** (April 2026):
- 9 iterations, ~480 structural changes (cycle-breaking, package consolidation, god class analysis)
- PCA: 0.948 → 1.000 (Δ+0.052) — **target >0.03 met**
- SCC: 17 → 0 — **target <10 met**
- SH: 0.974 → 1.000 (perfect structural health)
- Panel: 4.0 → 4.8/10 (+0.8)
- **M removed from QSE-Track**: Louvain variance (σ=0.005, range=0.028) > refactoring signal (mean Δ=+0.007)
- Commit: f71b8ff

## E13f: Pilot 2 — QSE Fix + Panel (in progress)

**Goal**: Find a structurally weak Java project, fix it, measure QSE-Track response + architect panel delta.
