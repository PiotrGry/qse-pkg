# QSE — Threats to Validity

Version: 3.0  
Last reviewed: April 2026  
Source of truth: AGQ Researcher skill v3.0, AGQ Data Scientist skill v3.0

Organised following the standard validity framework: Internal, External, Construct, and Statistical Conclusion validity.

Severity scale:
- **HIGH** — materially affects conclusions; must be mitigated before reporting
- **MEDIUM** — limits generalisability or introduces uncertainty; must be acknowledged
- **LOW** — minor; note in limitations section

---

## 1. Internal Validity

*Threats to the conclusion that AGQ causes or correctly captures observed differences in quality.*

---

### IV-01 — BLT refuted as GT

| Field | Value |
|-------|-------|
| ID | IV-01 |
| Description | Bug Lead Time (BLT) was used as the ground truth proxy for architectural quality in early calibration of AGQ weights. BLT is now refuted as GT (r=−0.125 ns). All weights calibrated on BLT (including AGQ_v1's S=0.55 and the per-language Java S=0.95) are invalidated. |
| Severity | HIGH |
| Current Mitigation | BLT is explicitly excluded from all current GT computation. Expert panel (σ<2.0) is the sole accepted GT. Mandatory pre-analysis filter: exclude BLT=0 and BLT>365 repos. W1 status set to REFUTED. |
| Residual Risk | Legacy analyses performed before BLT refutation may have influenced experimental design choices (e.g. which repos were selected for the panel). Selection contamination cannot be fully ruled out. |

---

### IV-02 — S tautology (Stability dominates AGQ_v2)

| Field | Value |
|-------|-------|
| ID | IV-02 |
| Description | Stability (S) explains 72.6% of AGQ_v2 variance (Pearson r=+0.852, n=357). AGQ_v2 is largely a rescaled version of S. Any correlation between AGQ_v2 and a third variable may be driven entirely by S. |
| Severity | HIGH |
| Current Mitigation | AGQ_v3c reduces S weight to 0.20 (equal to other components). Partial correlations on individual sub-dimensions are reported separately. The tautology is acknowledged in all reporting (Claim 7). |
| Residual Risk | **NEW (P4):** S monotonicity is BROKEN on the loose n=59 GT — analysis reveals an inverted-U curve with peak discriminative power near S=0.20 rather than monotone increase. This means adding more S weight beyond 0.20 *hurts* performance on the loose GT. Monotonicity is PRESERVED on the strict n=38 GT (partial_r=+0.410, p=0.011), indicating the non-monotone behaviour is introduced by the 19 MID-zone repos (panel 3.5–7.0). The S tautology threat is therefore exacerbated when using loose GT thresholds: S behaves differently depending on which repos are included. See also IV-06 and Claim 13. |

---

### IV-03 — Circular reasoning for W6 (FLAT fingerprint = AI-generated)

| Field | Value |
|-------|-------|
| ID | IV-03 |
| Description | The claim that the FLAT fingerprint indicates AI-generated code is based on circular reasoning: the fingerprint is defined using AGQ components, which are then used to detect the pattern that was used to define the fingerprint. No independent label of "AI-generated" was validated. |
| Severity | MEDIUM |
| Current Mitigation | W6 classified as DOUBTFUL. The FLAT claim is not used in any statistical analysis or GT labelling. |
| Residual Risk | If FLAT fingerprint leaks into GT repo selection, it could bias which repos are labelled NEG. Currently no evidence of this but the risk exists. |

---

### IV-04 — Multi-module repository aggregation

| Field | Value |
|-------|-------|
| ID | IV-04 |
| Description | Multi-module repositories (e.g. spring-boot-examples with 87 pom.xml files) produce dependency graphs that are aggregates of many independent small projects. AGQ for such repos is not interpretable as a single architectural score. |
| Severity | HIGH |
| Current Mitigation | Multi-module repos are excluded from GT by mandatory filter. Flag `multi_module` in issues list triggers automatic exclusion. |
| Residual Risk | Automatic detection of multi-module repos may miss edge cases (e.g. monorepos with a single root pom). Manual inspection required for repos with unusually high node counts. |

---

### IV-05 — TypeScript parser artefacts (nodes=0)

| Field | Value |
|-------|-------|
| ID | IV-05 |
| Description | 73% of TypeScript repos in iter6 produce nodes=0 in the scanner. This means the dependency graph is empty — AGQ computation is undefined or trivially 0. Including TypeScript repos in analysis would introduce systematic noise. |
| Severity | HIGH |
| Current Mitigation | TypeScript is explicitly excluded from all analyses via mandatory filter `lang != TypeScript`. |
| Residual Risk | Mixed-language repos (e.g. Java+TypeScript frontend) may still have their Java layer analysed — no known issue, but requires confirmation. |

---

### IV-06 — Loose vs strict GT threshold discrepancy

| Field | Value |
|-------|-------|
| ID | IV-06 |
| Description | The original expanded GT (n=59) was constructed using panel ≥ 6.0 as POS and panel ≤ 3.5 as NEG. The benchmark protocol specifies panel ≥ 7.0 as POS and panel ≤ 3.5 as NEG. This creates 19 repos in the MID zone (3.5 < panel < 7.0) that are classified as POS under the loose threshold but are excluded by the strict protocol. Results differ materially depending on which threshold is used: (a) the S monotonicity property breaks on n=59 loose GT but is preserved on n=38 strict GT; (b) per-component partial_r values differ (e.g. S: loose GT not monotone, strict GT partial_r=+0.410, p=0.011). |
| Severity | HIGH |
| Current Mitigation | The strict n=38 GT (panel ≥ 7.0 / ≤ 3.5) is the protocol-compliant definition and is the primary reporting basis for all claims from P4 onwards. The loose n=59 GT is retained for sensitivity analysis and exploratory work only. All reports must state which GT threshold was used. |
| Residual Risk | Earlier results (e.g. Claim 1 at n=29, Claim 8 at n=29) used intermediate GT definitions that are neither the loose n=59 nor the strict n=38. Trend comparisons across GT versions are confounded by both sample size and threshold changes simultaneously. The 19 MID-zone repos are genuinely ambiguous quality cases — it is unknown whether excluding them improves or degrades GT quality. |

---

## 2. External Validity

*Threats to the generalisability of QSE findings to other populations or contexts.*

---

### EV-01 — Selection bias (GitHub stars, n≥20k median)

| Field | Value |
|-------|-------|
| ID | EV-01 |
| Description | The iter6 benchmark is drawn from highly-starred GitHub repositories (median ≈ 20k stars — top 1% of GitHub). This is not representative of typical corporate or enterprise codebases. QSE has not been validated on internal, non-public, or low-visibility code. |
| Severity | HIGH |
| Current Mitigation | Jolak et al. external validation uses a different dataset, providing some triangulation. Jolak result (W5) is CREDIBLE. |
| Residual Risk | If architecture quality correlates with repo popularity (well-maintained repos tend to be better architected), the benchmark may systematically exclude the worst real-world architectures. AGQ thresholds calibrated on this population may not transfer to enterprise code. |

---

### EV-02 — Go ground truth is zero

| Field | Value |
|-------|-------|
| ID | EV-02 |
| Description | No Go repositories have been evaluated by the expert panel (Go GT n=0). Any claim about AGQ performance for Go repositories has zero empirical support. |
| Severity | HIGH |
| Current Mitigation | Go is not reported as validated. P2 priority: collect first 20 Go GT repos. |
| Residual Risk | Applying AGQ_v3c (Java or Python) weights to Go would be entirely unjustified. Go has different idiomatic packaging conventions (flat by convention) that may invert all current signals. |

---

### EV-03 — Language bias (Java/Python formulas not cross-applicable)

| Field | Value |
|-------|-------|
| ID | EV-03 |
| Description | AGQ_v2 has OPPOSITE directional effect for Python vs Java. CD direction is also opposite. Applying Java-calibrated weights to Python produces wrong results. |
| Severity | HIGH |
| Current Mitigation | Language-specific formulas (AGQ_v3c Java ≠ AGQ_v3c Python) introduced. Language is a mandatory stratification variable in all analyses. |
| Residual Risk | Root cause of language divergence (especially CD direction reversal) is not yet understood. Python formula now validated on n=30. |

---

### EV-04 — Type 2 Legacy Monolith blind spot

| Field | Value |
|-------|-------|
| ID | EV-04 |
| Description | Legacy Monolith with hierarchy (Type E repos: buildbot, Medusa, SickChill) are not detected by any current QSE metric. flat_score ≈ 0.9 for these repos despite Panel Score <3.5. This is a known false-negative category. **Updated (P4):** god-module analysis on Python GT (n=30) confirms the blind spot quantitatively: buildbot false negative is confirmed with flat_score=0.946 despite Panel Score <3.5. God-module metrics (god_class_ratio, max_methods) are all in the correct direction (negative partial_r as expected) but NONE achieves individual statistical significance — god_class_ratio: partial_r=−0.217 (p=0.249 ns); max_methods: partial_r=−0.262 (p=0.162 ns). max_depth is the most promising signal (partial_r=+0.381, p=0.038*) but measures hierarchy depth, not god-module concentration. Composite god-module index not yet tested. |
| Severity | HIGH |
| Current Mitigation | Documented as known blind spot. P3 priority: develop composite god-module metric (max_file_lines, fan-out top-5 nodes, god_class_ratio). Individual metrics show correct directional signal, providing weak evidence that a composite may reach significance. |
| Residual Risk | Until a significant composite god-module metric is validated, QSE will misclassify or fail to flag Type E repos. The current god-module signal is directionally correct but individually too weak. n=30 Python GT may be insufficient power to detect a moderate effect — this is partially a sample size problem (see SC-07). |

---

### EV-05 — Single primary external dataset (Jolak et al.)

| Field | Value |
|-------|-------|
| ID | EV-05 |
| Description | The strongest external validation (W5) is based on a single external dataset (Jolak et al., n=82 snapshots, Java only). LOOCV 6/7 correct — one project is misclassified. |
| Severity | MEDIUM |
| Current Mitigation | External validation is treated as corroborating evidence only, not primary validation. |
| Residual Risk | A single external dataset with a different GT definition (PC/DL vs Panel Score) cannot fully validate QSE's construct. AGQ_v3c cross-validation on Jolak is planned. |

---

## 3. Construct Validity

*Threats to whether QSE measures what it claims to measure (architectural quality).*

---

### CV-01 — Expert panel GT subjectivity and consistency

| Field | Value |
|-------|-------|
| ID | CV-01 |
| Description | PANEL_SCORE is the average of 4 individual expert scores. Different experts emphasise different architectural values (Robert: Clean Architecture; Vaughn: DDD; Martin: Evolvability; Mark: Patterns). σ<2.0 threshold filters out disagreements but does not eliminate systematic biases shared among experts. |
| Severity | MEDIUM |
| Current Mitigation | σ<2.0 filter. Panel is calibrated on known examples. Type A–G classification framework provides anchor points. |
| Residual Risk | All 4 experts may share biases (e.g. against non-OOP paradigms, or in favour of DDD). The panel may not represent the diversity of real-world architecture evaluation. |

---

### CV-02 — Java DDD bias (AGQ_v2 undersells DDD repos)

| Field | Value |
|-------|-------|
| ID | CV-02 |
| Description | Java DDD repositories (Type A) receive AGQ_v2 = 0.44–0.50 despite PANEL_SCORE ≥ 8.0. DDD's deliberate Bounded Context isolation results in a LOW_COH fingerprint. AGQ_v2 penalises the intentional design of DDD as if it were poor cohesion. |
| Severity | MEDIUM |
| Current Mitigation | Java DDD bias is documented. AGQ_v3c reduces C and S weights. DDD repos must not be excluded as false negatives when AGQ<0.55. |
| Residual Risk | Until a DDD-aware C metric is developed, AGQ will systematically undervalue the best DDD Java architectures. This introduces construct invalidity for the DDD subpopulation. |

---

### CV-03 — Stability (S) measures graph topology, not real stability

| Field | Value |
|-------|-------|
| ID | CV-03 |
| Description | "Stability" in QSE is DMS instability (fan-in/fan-out ratio), not empirically measured code stability (change frequency, survival time). A package can be "stable" in the DMS sense while being frequently changed or vice versa. |
| Severity | MEDIUM |
| Current Mitigation | Terminology documented. W8 confirms that dAGQ/dt (temporal change) does not predict quality, which is consistent with this construct limitation. |
| Residual Risk | End users may conflate DMS stability with actual code change stability. Reporting must clarify the distinction. |

---

### CV-04 — flat_score conflates depth with quality

| Field | Value |
|-------|-------|
| ID | CV-04 |
| Description | flat_score assumes that deeper hierarchy = better architecture. This is true for Type D (Flat Spaghetti) but false for Type E (Legacy Monolith) where deep hierarchy coexists with poor quality. flat_score is a partial signal, not a general depth-quality claim. |
| Severity | MEDIUM |
| Current Mitigation | flat_score is used only in the Python formula. Type E limitation is documented (IV-03, EV-04). |
| Residual Risk | Users may over-interpret flat_score as a universal depth quality signal. |

---

## 4. Statistical Conclusion Validity

*Threats to whether statistical inferences drawn from QSE data are valid.*

---

### SC-01 — Small samples — Java GT n=59 / n=38 strict, Python GT n=30

| Field | Value |
|-------|-------|
| ID | SC-01 |
| Description | Java GT has been expanded to n=59 total (loose, panel ≥ 6.0) and n=38 strict protocol-compliant (panel ≥ 7.0 / ≤ 3.5). Python GT has n=30 (target reached). The strict protocol filtering reduces the effective Java GT from n=59 to n=38, introducing a trade-off: protocol compliance vs statistical power. Effect sizes shrank when expanding from n=14 to n=29 (W4: r=+0.675 → r=+0.543) and again at the strict n=38 definition (partial_r=0.507). Go GT has n=0. |
| Severity | HIGH |
| Current Mitigation | All results are reported with bootstrap 95% CI alongside p-values. Strict GT (n=38) is the primary reporting basis. Both loose and strict results are reported for sensitivity. CREDIBLE* classification used for p<0.05 results. |
| Residual Risk | n=38 strict GT yields CI width of 0.43 ([0.286, 0.712]) — too wide to discriminate between weight variants (see SC-07). Effect size may shrink further with additional repos. Python marginal p-values (p=0.007 for flat_score) may not survive multiple testing correction (SC-03). Go has zero GT data. |

---

### SC-02 — Size confound not always controlled

| Field | Value |
|-------|-------|
| ID | SC-02 |
| Description | Repository size (nodes) is correlated with AGQ values. Larger repositories may systematically score differently from smaller ones regardless of quality. Raw correlation without size control inflates apparent AGQ-quality associations. |
| Severity | HIGH |
| Current Mitigation | Partial Spearman (| nodes) is the mandatory analysis method. Raw Pearson/Spearman is reported as informational only. Size outliers (e.g. OsmAnd n=6831, OpenMetadata n=5017) are excluded from GT. |
| Residual Risk | The choice of "nodes" as the size control variable is itself a design decision. Other size proxies (lines of code, number of files) are not controlled. |

---

### SC-03 — Multiple testing without correction

| Field | Value |
|-------|-------|
| ID | SC-03 |
| Description | Multiple sub-dimension correlations (M, A, S, C, CD, flat_score, NS_depth, NS_gini) are tested against GT in the same dataset. Without Bonferroni or FDR correction, the probability of at least one false positive increases. |
| Severity | MEDIUM |
| Current Mitigation | Effect sizes and partial r values are reported alongside p-values. Results at p<0.05 with small effect size are treated with caution. |
| Residual Risk | No formal multiple testing correction has been applied to the reported results. Some of the CREDIBLE* findings (e.g. NS_depth, flat_score) may not survive correction. With 5 dimensions tested against GT, the Bonferroni-corrected threshold would be p<0.01 — C (p=0.0002) survives, S (p=0.011) is borderline. |

---

### SC-04 — BLT=0 artefacts inflate spurious correlations

| Field | Value |
|-------|-------|
| ID | SC-04 |
| Description | 53 repos have BLT=0 (instant issue closures). Including these inflates the apparent negative correlation between AGQ and BLT to r=−0.217* (from true r=−0.125 ns). This artefact was the basis for early AGQ weight calibration. |
| Severity | HIGH |
| Current Mitigation | BLT=0 repos are excluded by mandatory filter (`blt > 0`). BLT>365 also excluded. |
| Residual Risk | The artefact contaminated early weight estimates before being discovered. AGQ_v1 weights (especially S=0.55) are a legacy of this contamination. |

---

### SC-05 — nodes=0 repositories

| Field | Value |
|-------|-------|
| ID | SC-05 |
| Description | Repositories with nodes=0 produce undefined or trivially zero AGQ values. Including them in correlation analyses would introduce a degenerate cluster at AGQ=0. |
| Severity | HIGH |
| Current Mitigation | Mandatory filter: nodes≥20. All analyses use this threshold. |
| Residual Risk | The threshold of 20 nodes is somewhat arbitrary. Repos with 20–50 nodes may still have insufficient graph structure for meaningful AGQ computation. |

---

### SC-06 — Multicollinearity between dimensions

| Field | Value |
|-------|-------|
| ID | SC-06 |
| Description | AGQ sub-dimensions are not fully independent. Known correlations (n=357): M↔S: r=−0.20***, M↔C: r=−0.25***, A↔CD: r=+0.27***. If A and CD both measure absence of coupling, they may be partially redundant. VIF for AGQ_v2 is undefined (perfect multicollinearity by construction). |
| Severity | MEDIUM |
| Current Mitigation | PCA experiment closed with finding that eigenvalues are approximately equal — no dominant collinear direction. Individual dimension correlations reported separately from composite AGQ. |
| Residual Risk | If two dimensions are redundant, the composite formula double-counts that signal. The A+CD overlap is the primary risk. |

---

### SC-07 — CI too wide for weight discrimination

| Field | Value |
|-------|-------|
| ID | SC-07 |
| Description | At n=38 strict GT, the bootstrap 95% CI for AGQ_v3c partial_r is [0.286, 0.712] — a width of 0.43. At n=59 loose GT, the CI width is approximately 0.33. These CI widths are too large to distinguish between weight variants that differ by 0.05–0.10 in partial_r. Concretely: the best tested variant (C_boost, wC=0.30) achieves partial_r=0.560 vs v3c's 0.507 — a difference of 0.053 — which is far smaller than the CI width. No weight variant can be declared significantly better than v3c at current sample sizes. |
| Severity | MEDIUM |
| Current Mitigation | Weight optimisation is CLOSED as of P4. v3c equal weights (0.20 each) are retained as the default. The conclusion is "cannot reject v3c" — any weight change is speculative until n≥60 strict GT is reached. |
| Residual Risk | The inability to discriminate weights is a statistical power limitation, not evidence that all weights are equivalent. The true optimal weights may differ substantially from equal weights. C is the strongest individual predictor (partial_r=0.571) — a C-boosted formula may be genuinely better but requires larger n to confirm. CI width decreases approximately as 1/√n; reaching n=80 strict GT would reduce width to approximately 0.32, which may enable weight discrimination. |
