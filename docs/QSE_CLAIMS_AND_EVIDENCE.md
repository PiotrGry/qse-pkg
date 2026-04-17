# QSE — Claims and Evidence Traceability Matrix

Version: 3.0  
Last reviewed: April 2026  
Source of truth: AGQ Researcher skill v3.0, AGQ Data Scientist skill v3.0

---

## How to Read This Document

Each entry documents a specific empirical claim made about the QSE system, along with the full evidence chain. Confidence levels:
- **HIGH** — n≥30, p<0.01, external validation
- **MEDIUM** — n≥20, p<0.05, single dataset
- **LOW** — n<20 or p<0.10 or single direction tested
- **NONE** — methodological flaw invalidates the claim

---

## Claim 1: AGQ_v3c discriminates architecturally good from bad Java repositories

| Field | Value |
|-------|-------|
| Claim | AGQ_v3c produces significantly higher scores for POS than NEG Java repositories in the expert panel GT. |
| Evidence type | Statistical (Mann-Whitney U-test, partial Spearman correlation, bootstrap CI) |
| Data source | GT panel — Java GT (iter6 benchmark subset) |
| Sample size | n=59 total GT (pos=31, neg=28) using panel ≥ 6.0 threshold; n=38 strict protocol-compliant GT (pos=20, neg=18) using panel ≥ 7.0 / ≤ 3.5 |
| Effect size | Strict GT (n=38): partial Spearman r=+0.507** (controlling for nodes). Bootstrap 95% CI: [0.286, 0.712]. POS mean AGQ=0.563, NEG mean=0.468, gap=0.095. |
| p-value | MW U=296, p=0.000367*** (strict GT n=38); Spearman ρ=0.416, p=0.009** (strict GT n=38) |
| Confidence level | HIGH (n=59 total; n=38 strict protocol; p<0.001 on strict GT) |
| Known caveats | 19 repos fall in MID zone (3.5 < panel < 7.0) — excluded by strict protocol but included in loose n=59 GT. Results differ depending on GT threshold used (see IV-06). Effect size is reduced compared to earlier n=29 run (r=+0.543) — expected shrinkage with expanded sample. Java DDD bias persists: AGQ undersells top DDD repos. 3 repos have nodes < 100 and 3 have nodes > 5000. |
| Link to artifact | artifacts/gt_panel_v4.json; commits b336496 (P0 GT expansion), 5566912 (P4) |

---

## Claim 2: AGQ has external validity — Jolak et al. dataset

| Field | Value |
|-------|-------|
| Claim | AGQ (v2 formula) negatively correlates with dependency level (DL) in the Jolak et al. dataset, where low DL indicates better architecture (PC classification). |
| Evidence type | External validation (independent dataset, different GT definition) |
| Data source | Jolak et al. (external, Java, PC/DL ground truth) |
| Sample size | n=82 snapshots across 8 projects |
| Effect size | Pearson r=−0.751*** (higher AGQ → lower dependency level = better) |
| p-value | p<0.001*** |
| Confidence level | HIGH (external GT, LOOCV 6/7 projects correctly classified) |
| Known caveats | Jolak GT uses a different quality definition (PC/DL) than the expert panel. Cross-validation only 6/7 projects — one project misclassified. AGQ_v3c cross-validation on Jolak not yet completed. |
| Link to artifact | Jolak et al. published dataset; LOOCV results in session notes |

---

## Claim 3: AGQ_v2 snapshot is more predictive than AGQ trajectory (dAGQ/dt)

| Field | Value |
|-------|-------|
| Claim | Current AGQ score (AGQ_now) predicts Jolak DL better than change in AGQ over time (dAGQ/dt). |
| Evidence type | Comparative statistical (Spearman correlation) |
| Data source | Jolak et al. (8 projects, temporal snapshots) |
| Sample size | n=8 projects |
| Effect size | AGQ_now: r=−0.824***; dAGQ/dt: not significant |
| p-value | AGQ_now p<0.001***; dAGQ/dt: ns |
| Confidence level | MEDIUM (n=8 projects only, but strong effect) |
| Known caveats | Very small n=8 project-level observations. Single dataset. |
| Link to artifact | Session notes — W8 validation |

---

## Claim 4: flat_score predicts Python architectural quality

| Field | Value |
|-------|-------|
| Claim | flat_score (= 1 − flat_ratio) is a significant predictor of expert panel score for Python repositories. |
| Evidence type | Statistical (partial Spearman correlation) |
| Data source | GT panel — Python GT |
| Sample size | n=30 certain GT (pos=13, neg=17) — target reached |
| Effect size | Partial Spearman r=+0.484 (controlling for nodes) |
| p-value | p=0.007** |
| Confidence level | MEDIUM (n=30 target reached; p=0.007) |
| Known caveats | Only detects Type 1 (Flat Spaghetti — e.g. youtube-dl, faker). Does NOT detect Type 2 (Legacy Monolith — e.g. buildbot, Medusa) where flat_score ≈ 0.9 despite Panel Score <3.5. buildbot false negative confirmed: flat_score=0.946 (see EV-04, Claim 14). |
| Link to artifact | artifacts/gt_python_final_v2.json; qse/flat_metrics.py |

---

## Claim 5: AGQ_v3c (Java, n=38 strict GT) discriminates POS from NEG

| Field | Value |
|-------|-------|
| Claim | AGQ_v3c with equal weights (0.20 × M + 0.20 × A + 0.20 × S + 0.20 × C + 0.20 × CD) produces a significant discriminative signal on the strict protocol-compliant Java GT (panel ≥ 7.0 / ≤ 3.5). |
| Evidence type | Statistical (partial Spearman, Mann-Whitney U, bootstrap CI) |
| Data source | GT panel — Java GT strict (n=38, pos=20, neg=18) |
| Sample size | n=38 strict protocol-compliant GT |
| Effect size | Partial Spearman r=+0.507, Bootstrap 95% CI: [0.286, 0.712] |
| p-value | p=0.001*** (partial Spearman); MW U=296, p=0.000367*** |
| Confidence level | HIGH (n=38 strict; p<0.001; CI does not cross zero) |
| Known caveats | Strict GT excludes 19 MID-zone repos — effective n is reduced compared to loose n=59 GT. CI width of 0.43 ([0.286, 0.712]) limits precision. Java and Python formulas use different coefficients — do not apply cross-language. |
| Link to artifact | artifacts/gt_panel_v4_strict.json; commit b336496 |

---

## Claim 6: BLT is not a valid ground truth for AGQ

| Field | Value |
|-------|-------|
| Claim | BLT (Bug Lead Time) does not correlate with AGQ after cleaning artefacts, and therefore cannot be used as a ground truth proxy. |
| Evidence type | Statistical (Pearson correlation after data cleaning) |
| Data source | iter6 benchmark (n=357 after mandatory filters) |
| Sample size | n=357 filtered repos |
| Effect size | r=−0.125 (was −0.217* before cleaning; spurious signal from BLT=0 repos) |
| p-value | ns (not significant) |
| Confidence level | HIGH — claim of invalidity is robust. Removing 53 BLT=0 repos eliminates the signal entirely. |
| Known caveats | This is a negative result — absence of correlation. It does not mean BLT has zero relationship with code quality; it means BLT is not a reliable AGQ proxy at this sample composition. |
| Link to artifact | artifacts/correlation_matrix_v1.json; iter6 data with BLT=0 flags |

---

## Claim 7: S (Stability) explains 72.6% of AGQ_v2 variance — tautological

| Field | Value |
|-------|-------|
| Claim | Stability (S) alone explains 72.6% of AGQ_v2 variance (r²=0.726), indicating that AGQ_v2 is largely a rescaled version of S. |
| Evidence type | Statistical (Pearson correlation matrix) |
| Data source | iter6 benchmark n=357 |
| Sample size | n=357 |
| Effect size | Pearson r(S, AGQ_v2) = +0.852 → r²=0.726 |
| p-value | p<0.001*** |
| Confidence level | HIGH — this is a structural property of the formula, not a sampling result |
| Known caveats | This is a tautology: S has weight 0.35 in AGQ_v2 and S is the largest single component. High S→AGQ_v2 correlation is partially by construction. Does not imply S is a valid GT predictor. **NEW (P4):** S monotonicity is BROKEN on the loose n=59 GT — S shows an inverted-U curve with peak at S=0.20 rather than monotone increase. Monotonicity is PRESERVED on the strict n=38 GT (partial_r=0.410, p=0.011). This indicates that the S–quality relationship is non-monotone in MID-zone repos (panel 3.5–7.0). See Claim 13. |
| Link to artifact | artifacts/correlation_matrix_v1.json; P4 experiment results (commit 5566912) |

---

## Claim 8: CD (Coupling Density) is not individually significant on strict Java GT

| Field | Value |
|-------|-------|
| Claim | CD dimension is not a significant individual predictor of Java quality on the strict protocol-compliant GT (panel ≥ 7.0 / ≤ 3.5), though it contributes positively within the composite formula. |
| Evidence type | Statistical (partial Spearman) |
| Data source | GT panel — Java GT strict (n=38) |
| Sample size | n=38 strict protocol-compliant GT |
| Effect size | Partial Spearman r=+0.168 (strict GT n=38) |
| p-value | ns (not significant) on strict GT |
| Confidence level | LOW — effect is in the correct direction but not individually significant at n=38 |
| Known caveats | Earlier result at n=29 showed partial_r=+0.508, p=0.020* — this was on a different (less strict) sample. Shrinkage to r=+0.168 ns on strict GT indicates CD's individual discriminative power is limited. CD direction is OPPOSITE for Python (CD negatively associated with quality for Python). Do not apply Java CD interpretation to Python. CD still contributes to composite AGQ_v3c signal. |
| Link to artifact | E2 implementation; qse/graph_metrics.py; strict GT analysis (commit b336496) |

---

## Claim 9: NS_depth is a significant Java quality predictor

| Field | Value |
|-------|-------|
| Claim | NS_depth (namespace depth metric) is a significant predictor of expert panel score for Java repositories. |
| Evidence type | Statistical (partial Spearman) |
| Data source | GT panel — Java GT (E5) |
| Sample size | UNKNOWN (E5 partial) |
| Effect size | Partial Spearman r=+0.698** (Java) |
| p-value | p<0.01** |
| Confidence level | MEDIUM — strong effect but n<30 and Python direction not confirmed |
| Known caveats | Python: direction is correct but not significant (ns). E5 status is PARTIAL. Recomputation with expanded strict GT (n=38) is pending. |
| Link to artifact | qse/namespace_metrics.py; E5 session notes |

---

## Claim 10: S_hierarchy (Stability Hierarchy Score) does not distinguish POS from NEG

| Field | Value |
|-------|-------|
| Claim | S_hierarchy assigns identical scores to CRUD package-by-layer and DDD repositories, making it useless as a discriminator. |
| Evidence type | Statistical (Mann-Whitney U-test) |
| Data source | GT panel — Java GT |
| Sample size | UNKNOWN exact n (E1 session) |
| Effect size | Δ(pos-neg) ≈ 0 |
| p-value | p=0.806 ns |
| Confidence level | HIGH — null result is robust; effect size is negligible |
| Known caveats | CRUD repos with controller/service/repository naming achieve S_h=1.0, the same as DDD repos, because the metric only checks for layer naming patterns. |
| Link to artifact | E1 closure notes |

---

## Claim 11: C (Cohesion) is the strongest individual discriminator for Java

| Field | Value |
|-------|-------|
| Claim | C (Cohesion) has the highest individual partial Spearman correlation with expert panel score among all five AGQ dimensions on the strict Java GT. |
| Evidence type | Statistical (partial Spearman, controlling for nodes) |
| Data source | GT panel — Java GT strict (n=38, pos=20, neg=18) |
| Sample size | n=38 strict protocol-compliant GT |
| Effect size | Partial Spearman r=+0.571*** (strongest among M, A, S, C, CD) |
| p-value | p=0.0002*** |
| Confidence level | HIGH (n=38; p=0.0002; strongest among all five dimensions) |
| Known caveats | Per-component ranking on strict GT: C (+0.571***) > S (+0.410*) > CD (+0.168 ns) > A (+0.242 ns) > M (+0.052 ns). C is dominant but Java DDD bias applies — DDD repos deliberately have low cohesion by design (Bounded Context isolation), so C may penalise the best DDD architectures. Do not use C alone as a quality gate; use within composite AGQ_v3c. |
| Link to artifact | artifacts/gt_panel_v4_strict.json; per-component analysis (commit b336496) |

---

## Claim 12: Equal weights (v3c) are robust — no variant significantly beats v3c across GT sizes

| Field | Value |
|-------|-------|
| Claim | AGQ_v3c (equal weights 0.20×M + 0.20×A + 0.20×S + 0.20×C + 0.20×CD) remains the defensible winner: no weight variant produces a statistically distinguishable improvement on either the loose n=59 or the strict n=38 Java GT. |
| Evidence type | Statistical (partial Spearman + bootstrap CI comparison across weight variants) |
| Data source | GT panel — Java GT (P4 experiment, both n=59 loose and n=38 strict) |
| Sample size | n=59 (loose) and n=38 (strict) |
| Effect size | v3c baseline: partial_r=0.507, CI=[0.286, 0.712]. Best variant (C_boost, wC=0.30): partial_r=0.560, CI=[0.350, 0.748]. S=0 variant: partial_r=0.393, CI=[0.080, 0.640]. All CIs overlap with v3c CI. |
| p-value | No variant achieves a statistically significant improvement over v3c (all CIs overlap) |
| Confidence level | MEDIUM — conclusion is "cannot reject v3c" not "v3c is optimal." CI width of ~0.43 prevents discrimination between close variants. |
| Known caveats | C_boost (wC=0.30) is numerically better (partial_r=0.560 vs 0.507) but CI overlap means the difference is not significant given n=38. The inability to discriminate is a power problem (see SC-07), not evidence that all weights are equivalent. S-peak alignment: the inverted-U S curve on loose GT peaks at S=0.20 — the same weight assigned in v3c — which is coincidental alignment, not causal. Weight optimisation is CLOSED as of P4; reopen only with n≥60 strict GT. |
| Link to artifact | P4 experiment results (commit 5566912); bootstrap CI tables |

---

## Claim 13: S monotonicity breaks at n>38 — inverted-U curve with peak at S=0.20

| Field | Value |
|-------|-------|
| Claim | The relationship between S (DMS Stability) and expert panel quality score is monotone positive on the strict n=38 GT, but breaks into an inverted-U curve (non-monotone) when the loose n=59 GT is used, with the peak occurring near S=0.20. |
| Evidence type | Statistical (P4 sensitivity analysis — S weight sweep on both GT sizes) |
| Data source | GT panel — Java GT (both n=59 loose and n=38 strict), P4 experiment |
| Sample size | n=59 (loose GT); n=38 (strict GT) |
| Effect size | Strict GT (n=38): S partial_r=+0.410, p=0.011* (monotone positive). Loose GT (n=59): S shows inverted-U, peak performance near S=0.20; removing S entirely (S=0 variant) gives partial_r=0.393 vs v3c 0.507 — both lower and different shape. |
| p-value | Strict GT: p=0.011*. Loose GT: S relationship is non-monotone (specific p-values for curve segments not reported). |
| Confidence level | MEDIUM — finding is based on a single P4 sweep; requires replication with additional GT data |
| Known caveats | The inverted-U pattern on loose GT is driven by the 19 MID-zone repos (panel 3.5–7.0). These repos have ambiguous S–quality relationships that create non-monotone aggregated behaviour. The strict GT excludes MID-zone repos and recovers monotonicity. This finding motivates the strict protocol threshold (panel ≥ 7.0 / ≤ 3.5) as the correct GT definition. Do not interpret the S=0.20 peak on loose GT as an optimal weight recommendation. |
| Link to artifact | P4 experiment results (commit 5566912); S-sweep plots |

---

## Claim 14: God-module metrics do not individually predict Python quality

| Field | Value |
|-------|-------|
| Claim | Individual god-module metrics (god_class_ratio, max_methods) are all in the correct direction for predicting Python architectural quality but none reaches statistical significance. |
| Evidence type | Statistical (partial Spearman correlation) |
| Data source | GT panel — Python GT (n=30, pos=13, neg=17) |
| Sample size | n=30 |
| Effect size | god_class_ratio: partial_r=−0.217 (higher ratio → worse quality — correct direction). max_methods: partial_r=−0.262 (higher max methods → worse quality — correct direction). max_depth: partial_r=+0.381 (significant). shallow_ratio: partial_r=−0.352 (borderline). |
| p-value | god_class_ratio: p=0.249 ns. max_methods: p=0.162 ns. max_depth: p=0.038*. shallow_ratio: p=0.057 (borderline). |
| Confidence level | LOW — no individual god-module metric is significant; direction is correct; Type 2 detection problem not yet solved |
| Known caveats | buildbot false negative CONFIRMED: buildbot flat_score=0.946 yet Panel Score <3.5 — classic Type E Legacy Monolith blind spot. God-module metrics are in the correct direction (negative partial_r as expected) but n=30 is insufficient power to detect the effect. Composite god-module index not yet tested. max_depth (partial_r=0.381, p=0.038) is the most promising individual signal but measures a different construct (hierarchy depth, not god-module concentration). P3 priority to develop a composite god-module metric. |
| Link to artifact | Python GT analysis; god_metrics.py; EV-04 threat documentation |
