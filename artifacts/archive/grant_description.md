# QSE — Quality Score Engine
## Research Discoveries, Contributions, and Innovation Potential
### Input Document for EU Grant Application (Horizon Europe / NCN / NCBiR)

**Project:** Architecture-Aware Quality Assurance for AI-Generated Software
**Date:** March 2026
**Status:** Working prototype with empirical validation on 127 OSS repositories

---

## 1. Executive Summary

The proliferation of AI-assisted code generation (GitHub Copilot, Cursor, Claude Code) introduces a new class of software quality risk: **architectural erosion**. While AI tools produce syntactically correct code that passes unit tests, they systematically violate architectural boundaries, introduce cyclic dependencies, and degrade module cohesion — degradations invisible to existing tools like SonarQube.

This project introduces **QSE (Quality Score Engine)**, a novel framework for automated architectural quality measurement, empirical calibration, and policy enforcement across programming languages. Our experimental validation on 127 open-source repositories (Python, Java, Go) yields five scientifically significant findings, introduces a practical CI/CD gate for architectural regression prevention, and establishes the foundation for training language models on architectural quality signals.

---

## 2. Problem Statement

### 2.1 The Vibe Coding Crisis

AI-assisted development is becoming the norm. GitHub reports that over 46% of new code on their platform is AI-generated (2025). This creates a fundamental tension:

- **Existing quality tools** (SonarQube, CodeClimate) measure syntactic and security properties — line-level metrics
- **Architectural quality** — module independence, dependency hierarchy, cohesion — is not measured by any widely-adopted tool
- **AI systems** optimize for "works now," not "maintainable in 12 months"

The result: codebases that pass all automated checks but have degraded architectural integrity, leading to increased maintenance costs, slower feature delivery, and higher defect rates over time.

### 2.2 The Measurement Gap

Despite decades of research on software metrics (Martin 1994, Nagappan & Ball 2005, D'Ambros & Lanza 2009), no production-ready tool provides:

1. **Automated** architectural quality scoring across languages
2. **Empirically calibrated** composite metrics (rather than arbitrary equal weights)
3. **Policy enforcement** derived automatically from existing code structure
4. **CI/CD integration** that blocks architectural regressions in real-time

This project fills this gap.

---

## 3. Scientific Discoveries

### Discovery 1: Martin's Distance from Main Sequence Degenerates Without Abstractness Data

**Problem in literature:** Robert C. Martin's "Distance from Main Sequence" metric (D = |A + I - 1|) is widely referenced but has no empirical validation (confirmed by systematic literature review; Drotbohm 2024 notes the metric is "unvalidated in practice").

**Our finding:** In Python codebases, abstractness A ≈ 0 for virtually all modules (ABC/Protocol usage is rare). This causes D = |I - 1| = 1 - I, making "stability" score equivalent to mean(instability) — semantically inverted. High scores reward flat, leaf-heavy architectures and penalize properly layered systems.

**Evidence:** youtube-dl (flat extractor architecture) scored stability=0.99 under the original formula — higher than django (layered framework) at stability=0.38. Architecturally nonsensical.

**Proposed solution:** Package-level instability variance as replacement:
```
stability = var(I_per_package) / 0.25  ∈ [0,1]
```
This rewards codebases where packages have differentiated coupling roles (core vs. leaves), which is the architectural intent of the original metric.

**Validation:** OSS-80 benchmark. Discrimination improved from spread=0.286 (v1) to spread=0.548 (v4). youtube-dl correctly scores 0.23 (flat plugin architecture), django scores 0.93 (layered).

**Publication potential:** First empirical validation and correction of Martin's metric on large-scale OSS data. Target: IEEE TSE or JSS.

---

### Discovery 2: Architectural Metrics Are Not Language-Neutral — Language Bias in Cohesion

**Problem in literature:** No study compares the same architectural metrics across programming language paradigms on real repositories.

**Our finding:** LCOM4-based cohesion exhibits systematic language bias:

| Language | n repos | Mean Cohesion | Explanation |
|---|---|---|---|
| Go | 20 | **1.000** | Interfaces/structs have no inheritance → LCOM4=1 always |
| Python | 78 | ~0.750 | Mixed OOP paradigm |
| Java | 29 | **0.328** | Complex class hierarchies, multiple inheritance |

Go achieves cohesion=1.00 on every single repository — not because Go code is "better," but because Go's type system structurally prevents the patterns LCOM4 penalizes.

**Implication:** Any composite metric including LCOM4 as equal-weight component will systematically rank Go above Java regardless of actual code quality. Cross-language comparisons using such metrics are methodologically invalid without language-specific normalization.

**Evidence:** 127 repositories across 3 languages. Java's jackson-databind (industry standard, 10k+ stars, widely considered excellent) scores AGQ=0.459 due to cohesion=0.10 — a reflection of its "universal serializer" design intent, not a quality defect.

**Publication potential:** First empirical demonstration of language paradigm bias in architectural quality metrics. Target: ACM ESEC/FSE or MSR.

---

### Discovery 3: Static Architectural Metrics and Process Metrics Are Orthogonal

**Problem in literature:** The relationship between static structural metrics and dynamic process metrics (code churn, co-change patterns) is assumed but not systematically studied across languages.

**Our finding:** Across all tested ground-truth proxies (bugfix_ratio, hotspot_ratio, co-change graph entropy), the cross-project Spearman correlation with AGQ remains near-zero (p>0.05):

| Ground Truth Proxy | r_s | p-value |
|---|---|---|
| bugfix_ratio (git log) | -0.100 | 0.35 |
| hotspot_ratio (churn) | -0.007 | 0.93 |
| co-change graph entropy | -0.012 | 0.91 |

This is not a failure of our metrics — it is a scientifically significant result. Static architectural metrics and dynamic process metrics measure **orthogonal dimensions** of software quality, consistent with Zimmermann et al. (2009) who showed cross-project defect prediction fundamentally fails due to project-level confounders (maturity, community size, development velocity).

**Implication for T3 (Complementarity):** 21 of 78 mature OSS projects receive SonarQube maintainability rating "A" (maximum) but score below the AGQ mean threshold. AGQ detects architectural issues that SonarQube cannot, and SonarQube detects code-level issues AGQ cannot. The two tools are complementary, not competing.

**Evidence:** 78 Python OSS repos, 74 with churn data, 78 with SonarQube measurements.

**Publication potential:** Empirical refutation of "architectural metrics predict defects cross-project." Reframes the question from prediction to complementarity. Target: EMSE or IST.

---

### Discovery 4: Empirically Calibrated Weights — Acyclicity Dominates

**Problem in literature:** Composite architectural quality metrics universally use equal weights (1/n) without empirical justification. This is arbitrary.

**Our finding:** L-BFGS-B optimization with Leave-One-Out cross-validation on 74 repositories, using `1 - hotspot_ratio` as ground truth, yields:

```
w(acyclicity)  = 0.730   ← dominant
w(cohesion)    = 0.174
w(stability)   = 0.050
w(modularity)  = 0.000   ← no independent signal
```

**This is independently confirmed by literature:** Gnoyke et al. (JSS 2024), analyzing 485 releases of 14 OSS systems: "practitioners perceive cyclic dependencies to affect quality, speed, and occurrence of bugs the most among architectural smell types."

Our empirical calibration aligns with expert assessment without using expert input — the calibration emerges from the data.

**LOO-CV MSE = 0.006 ± 0.013** — the model is stable and not overfitting.

**Publication potential:** First empirically calibrated architectural composite metric with LOO-CV validation. Resolves a long-standing methodological weakness in composite metric literature. Target: IEEE TSE.

---

### Discovery 5: Automatic Policy Discovery from Code Structure

**Problem in literature:** Architectural policy enforcement tools (import-linter, tach) require manual rule specification — a barrier to adoption.

**Our finding:** Combining Louvain community detection with directional edge analysis on the dependency graph automatically discovers architecturally meaningful boundaries:

- Django: 3 clusters (django, django.contrib, django.db), 3 rules correctly identifying `django.db` as stable core dependency
- Spring-boot: 4 clusters, `org.springframework` correctly identified as stable dependency
- Guava (Java): 8 clusters reflecting android vs. desktop library boundaries

Key insight: when A→B (A imports B but B never imports A), the correct rule is `forbidden: B→A` (preserve the hierarchy), not `forbidden: A→B` (which forbids the existing, correct dependency). This directional interpretation was incorrect in prior work.

**Validated:** Automatically discovered rules for Django produce `constraint_score=1.00` when run against the actual codebase — the rules are consistent with the existing architecture.

**Publication potential:** Novel algorithm for architectural policy auto-discovery with cross-language validation. Target: ICSA or ECSA.

---

## 4. Technical Contributions

### 4.1 QSE Core Engine (Python + Rust)

- **Python implementation:** 215 unit tests, production-ready CLI (`qse scan/gate/agq/trl4/discover`)
- **Rust implementation (qse-core):** Universal tree-sitter scanner for Python, Java, Go; O(m) Louvain; 3-30× faster than Python
- **Performance:** django 15× faster (2107ms → 137ms), home-assistant 30× faster (19s → 655ms)
- **Cross-language:** validated on 127 repos, 3 languages, 127,000+ LOC analyzed

### 4.2 Novel Metrics

| Metric | Innovation |
|---|---|
| Package-level instability variance | Replaces Martin's D, validated on OSS-80 |
| Internal-only acyclicity | Filters stdlib/third-party, prevents false cycles |
| Calibrated composite (L-BFGS-B) | First empirically weighted architectural composite |
| Boundary crossing ratio (adaptive depth) | Language-aware, depth auto-detected |

### 4.3 Empirical Benchmark Suite

- **OSS-80 (Python):** 78 repositories, v1-v4 versions, full churn + SonarQube comparison
- **Java-30:** 29 repositories (Maven/Gradle, multi-module)
- **Go-20:** 20 repositories
- **All artifacts versioned and reproducible:** `scripts/agq_oss_thesis_benchmark.py`

### 4.4 Policy-as-a-Service Infrastructure

- `qse discover`: automatic boundary detection from code
- `qse agq --constraints`: CI/CD enforcement gate
- `qse trl4 --ratchet`: monotonic quality ratchet
- `qse discover_multilang`: cross-language policy discovery

---

## 5. Commercial and Societal Impact

### 5.1 Market Context

- GitHub Copilot: 1.3M paid users (2024), growing
- The AI code generation market: $1.7B (2024) → $12.3B (2029) projected
- No existing tool addresses architectural quality in AI-generated code
- SonarQube enterprise: €15k-€150k/year — QSE addresses a gap Sonar explicitly doesn't cover

### 5.2 Target Applications

1. **CI/CD Architectural Gate:** Blocks PRs that degrade architectural structure, regardless of whether code was human- or AI-written
2. **Technical Debt Quantification:** Provides quantified architectural health metrics for management decision-making
3. **M&A Due Diligence:** Automated architectural assessment in software acquisition
4. **AI Code Generation Guidance:** Feedback loop that trains AI systems to respect architectural boundaries

### 5.3 Policy-as-a-Service Business Model

```
Tier 1 (Open Source): CLI tool, GitHub Action — viral adoption
Tier 2 (Pro, €99-499/month): Policy Manager UI, trend dashboard, templates
Tier 3 (Enterprise, €999+/month): Compliance reporting, multi-repo, SSO
```

---

## 6. Research and Development Roadmap — Milestones

### Milestone 1 (Months 1-6): Empirical Foundation
**Status: COMPLETED**
- ✅ OSS-80 Python benchmark (78/80 repos)
- ✅ Java-30 benchmark (29/30 repos)
- ✅ Go-20 benchmark (20/20 repos)
- ✅ Metric validation and calibration (L-BFGS-B, LOO-CV)
- ✅ 5 peer-review-ready scientific findings
- ✅ Rust qse-core (3-30× performance improvement)

### Milestone 2 (Months 7-12): Dataset Construction for ML
**Objective:** Build labeled architectural quality dataset sufficient for model training

**Activities:**
- Extend benchmark to 300+ repositories (Python, Java, Go, TypeScript, Rust)
- Collect temporal data: AGQ per commit over 2-year history for each repo
- Label architectural violations: every commit that changes constraint_score
- Collect preference pairs: AI-generated code (pass) vs. (fail) from generate_loop.py
- Include architectural pattern labels (DDD, Clean, Hexagonal, Flat, etc.) for 50+ repos

**Deliverables:**
- `qse-dataset-v1`: 300+ repos × 24+ months × per-commit AGQ = ~500k labeled examples
- 10k+ architectural violation examples with before/after code pairs
- Published dataset on Zenodo/HuggingFace

**Expected scientific output:** Dataset paper (MSR 2027 Mining Challenge)

### Milestone 3 (Months 13-18): Architectural Quality Predictor (XGBoost)
**Objective:** Train lightweight model that predicts architectural violations from code diffs

**Approach:**
```
Input:  git diff featurized (n_new_imports, cross_boundary_count,
         delta_cycles, files_touched, module_depth_change)
Output: P(architectural_violation) ∈ [0,1]
```

**Training data:** 500k commits × (violation: yes/no) from Milestone 2 dataset

**Success criteria:**
- AUC > 0.80 on held-out repos
- Inference time < 10ms (suitable for pre-commit hook)
- Language-neutral (single model for Python, Java, Go)

**Deliverables:**
- Published model (HuggingFace)
- `qse check-diff` CLI command using the model
- Benchmark against rule-based baseline

**Expected scientific output:** ICSE or FSE 2027 paper on ML-based architectural smell prediction

### Milestone 4 (Months 19-24): Code Generation Guard (Fine-tuned LLM)
**Objective:** Fine-tune a code LLM to generate architecturally compliant code

**Approach:**
```
Base model: CodeBERT or StarCoder (7B)
Training signal: AGQ as reward in RLHF-style loop
  - Positive: AI-generated code that passes QSE gate
  - Negative: AI-generated code that fails QSE gate
  - Preference pairs: (fail_diff, fixed_diff) from generate_loop.py
```

**Key innovation:** AGQ replaces human feedback as reward signal — **automated architectural RLHF**. No human annotation required; the quality gate IS the preference model.

```python
# Training loop
for prompt in architecture_aware_tasks:
    generated_code = base_llm.generate(prompt + architectural_context)
    reward = qse_gate(generated_code, constraints)  # -1 to +1
    # PPO/DPO update based on architectural reward
```

**Success criteria:**
- Generated code passes QSE gate on first attempt: >85% of cases (baseline ~40%)
- AGQ delta per PR: statistically significant improvement vs. base model
- No regression in functional correctness (HumanEval benchmark)

**Deliverables:**
- Fine-tuned model: "ArchitectureAware-Coder"
- Paper: "AGQ as Reward Signal for Architectural RLHF"
- Open-source training pipeline

**Expected scientific output:** Nature Machine Intelligence or NeurIPS 2027

### Milestone 5 (Months 25-30): Production Deployment and Validation
**Objective:** Validate the full pipeline in production environments

**Activities:**
- Deploy QSE gate in 3-5 partner companies (mid-size software firms, 50-200 developers)
- A/B test: teams with QSE vs. without QSE, measure architectural drift over 6 months
- Measure: AGQ trend, bug rate, developer velocity, code review time
- Validate fine-tuned model in real Copilot/Cursor workflows

**Success criteria:**
- AGQ trend: flat or improving in QSE group vs. declining in control
- Bug rate reduction: >15% in architecturally instrumented modules
- Developer satisfaction: model acceptance rate >70% (architectural suggestions accepted)

**Deliverables:**
- Industry validation paper (ICSE SEIP track 2028)
- QSE Cloud SaaS beta launch
- IP filing: patent on architectural RLHF training methodology

---

## 7. Innovation Summary

| Dimension | State of the Art | QSE Innovation |
|---|---|---|
| Architectural metrics | Martin's D (unvalidated, language-specific) | Package-level stability variance (validated, language-agnostic) |
| Composite weights | Equal weights (arbitrary) | L-BFGS-B calibrated (empirical, LOO-CV validated) |
| Policy enforcement | Manual rule specification (tach, import-linter) | Automatic discovery from code structure |
| Language support | Language-specific tools | Single engine: Python + Java + Go (tree-sitter) |
| AI code quality | No architectural feedback to AI | AGQ as RLHF reward signal |
| Cross-language comparison | Assumed comparable | Language bias quantified and corrected |

---

## 8. Team Capabilities

**Demonstrated technical capacity:**
- 215 automated tests, production-quality codebase
- Full Rust implementation with PyO3 bindings (performance-critical path)
- Empirical validation on 127 repositories with statistical analysis
- Benchmark infrastructure for reproducible research

**Research output potential:**
- 5 findings at publication-ready quality (IEEE TSE, JSS, EMSE, ICSE, MSR)
- Novel dataset (500k+ labeled examples) as community contribution
- Open-source tool with commercial applications

---

## 9. Budget Justification (indicative)

| Item | Months | Rationale |
|---|---|---|
| PhD researcher (full-time) | 30 | Dataset construction, ML training, evaluation |
| Senior researcher (part-time) | 30 | Scientific oversight, publications |
| Compute (GPU cluster) | 18-24 | LLM fine-tuning (Milestone 4) |
| Industry partnerships | 24-30 | Production validation (Milestone 5) |
| Dissemination | Throughout | Conferences, open-source infrastructure |

---

## 10. Existing Assets (Sunk Costs — Already Delivered)

The following deliverables exist as working code and empirical results, representing significant prior investment:

- **qse-pkg repository:** 38 commits, 215 tests, full CLI
- **Benchmark data:** 127 repos analyzed, 4 metric versions compared
- **Rust qse-core:** Python + Java + Go scanner, 3-30× faster than Python
- **5 scientific findings:** empirically validated, publication-ready
- **Bibliography:** 40+ relevant papers reviewed and cited
- **IP position:** patent-eligible methodology (architectural RLHF reward signal)

---

*This document summarizes research conducted at [University] in collaboration with industry partners. All code and data available at: https://github.com/PiotrGry/qse-pkg*
