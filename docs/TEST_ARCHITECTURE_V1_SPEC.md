# Test Architecture v1 Specification — AGQ Scoring System

**Version:** 1.0 (April 2026)
**Branch:** `perplexity` (`PiotrGry/qse-pkg`)
**Status:** Ready for CLI implementation

---

## 1. Scope

### 1.1 Supported Languages

| Language | Scanner | Formula Variant |
|----------|---------|-----------------|
| Java     | `qse/java_scanner.py` (tree-sitter-java, file-level) | AGQ\_v3c (equal-weight) |
| Python   | `qse/scanner.py` (tree-sitter) | AGQ\_v3c + flat\_score |

TypeScript is **not supported**. The Rust scanner (`_qse_core`) is not available in the current environment.

### 1.2 Repository Eligibility Requirements

A repository must satisfy **all** of the following to receive a scored output:

| Requirement | Rule |
|-------------|------|
| **Node count** | `nodes ≥ 100` |
| **Project structure** | Single-module only (no multi-module builds) |
| **Language filter** | Java or Python; TypeScript repos are rejected |
| **Ground truth exclusion** | BLT must not be used as a ground-truth (GT) positive |

Repositories that fail eligibility return an `INELIGIBLE` status with a rejection reason; no AGQ score is emitted.

### 1.3 Pipeline

```
repo
 └─► QSE scanner
      └─► dependency graph
           └─► component metrics: M, A, S, C, CD
                                  (+ flat_score for Python)
                └─► AGQ_v3c score
                     └─► status (green / amber / red)
                          └─► textual insights / flags
```

**Component definitions:**

| Symbol | Meaning |
|--------|---------|
| `M` | Modularity |
| `A` | Abstraction |
| `S` | Stability |
| `C` | Cohesion |
| `CD` | Coupling / Dependency health |
| `flat_score` | Flat-structure penalty (Python only) |

All component scores are normalised to **[0, 1]** before formula application.

---

## 2. Formulas

### 2.1 Java — AGQ\_v3c

\[
\text{AGQ\_v3c} = 0.20 \cdot M + 0.20 \cdot A + 0.20 \cdot S + 0.20 \cdot C + 0.20 \cdot CD
\]

Equal weights across all five components. This variant was selected as the defensible winner across the strict GT (n=38, partial\_r=0.507, 95% CI=[0.286, 0.712]); C-boost (wC=0.30) produced a marginally higher point estimate but confidence intervals overlap, so v3c is retained for simplicity and robustness.

### 2.2 Python — AGQ\_v3c

\[
\text{AGQ\_v3c} = 0.15 \cdot M + 0.05 \cdot A + 0.20 \cdot S + 0.10 \cdot C + 0.15 \cdot CD + 0.35 \cdot \text{flat\_score}
\]

`flat_score` carries 35% weight because it is the strongest discriminator on the Python GT (n=30, partial\_r=0.484, p=0.007). `A` is down-weighted to 0.05 because its discriminative power is weak in the Python corpus.

> **Note:** Both formulas produce a scalar in approximately [0, 1]. Values outside this range indicate a scanner normalisation error and should be flagged as `INVALID`.

---

## 3. Status Thresholds

Thresholds use a **quantile-based approach** calibrated against the OSS distribution (iter6, n=357 filtered repos). Quantile anchors are derived from the strict GT positive (POS) subset.

> **Caveat (EV-01):** Thresholds were calibrated on top-starred OSS repositories. Enterprise codebases may follow different distributions; recalibration against internal data is recommended after the pilot.

### 3.1 Java

| Status | Condition | Basis |
|--------|-----------|-------|
| **GREEN** | AGQ ≥ 0.55 | ≥ Q50 of strict GT POS (POS mean = 0.563) |
| **AMBER** | 0.45 ≤ AGQ < 0.55 | Q25–Q50 interquartile zone |
| **RED** | AGQ < 0.45 | < Q25, below NEG mean (NEG mean = 0.468) |

### 3.2 Python

| Status | Condition | Basis |
|--------|-----------|-------|
| **GREEN** | AGQ ≥ 0.55 | ≥ Q50 of strict GT POS |
| **AMBER** | 0.42 ≤ AGQ < 0.55 | Q25–Q50 interquartile zone |
| **RED** | AGQ < 0.42 | < Q25, below NEG mean |

### 3.3 Absolute Floor (Q10)

| Language | Q10 threshold |
|----------|--------------|
| Java     | AGQ ≈ 0.40 |
| Python   | AGQ ≈ 0.35 |

Repos at or below Q10 are assigned **RED\*** regardless of other conditions. The asterisk indicates OSS-calibration bias (see FF2 and Section 6).

---

## 4. Fitness Functions

Fitness functions are evaluated **after** the base AGQ score and applied in order. They can only elevate severity (RED overrides AMBER overrides GREEN), never lower it.

---

### FF1 — Regression Guard

**Purpose:** Protect against architectural regression during active development.

**Trigger condition:**

```
AGQ_current - AGQ_main > 0.05   (drop)
AND
CD_current - CD_main   > 0.05   (drop)
```

**Effect:** If triggered, status is elevated to **AMBER** (or remains RED if already RED).

**Requires:** A `main`-branch scan result to compare against. If no baseline is available, FF1 is skipped and noted as `"ff1": "skipped (no baseline)"` in the output.

**Rationale:** A simultaneous drop in both overall score and coupling health is a reliable regression signal; single-metric drops are noisy.

---

### FF2 — Absolute Floor

**Purpose:** Catch severely degraded architectures regardless of relative position.

**Trigger condition:**

```
AGQ < Q10_threshold
```

(Java: AGQ < 0.40 | Python: AGQ < 0.35)

**Effect:** Status = **RED\*** (the asterisk is surfaced in both JSON and Markdown output).

**Rationale:** Below Q10 the gap from any POS exemplar is large enough that no relative comparison is needed.

**Caveat:** Q10 anchors carry OSS calibration bias (EV-01). Enterprise repos should expect recalibration.

---

### FF3 — Structural Risk Flags

**Purpose:** Surface actionable insights. These are **textual observations only** — they do not change the numeric score or gate the status.

| Flag | Language | Condition | Severity |
|------|----------|-----------|----------|
| `high_coupling` | Java + Python | CD < 0.20 | Warning |
| `flat_structure` | Python only | flat\_score < 0.30 | Warning |
| `low_cohesion` | Java + Python | C < 0.15 | Warning |
| `god_module_risk` | Python only | god\_class\_ratio > 0.15 | Experimental |

`god_module_risk` is marked **experimental**: the metric is directionally correct on the GT (partial\_r=−0.217) but is not individually statistically significant (p=0.249). It must not be used as a standalone quality gate.

Multiple flags may fire simultaneously and are all reported.

---

## 5. Output Format

### 5.1 JSON Schema (machine consumption)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AGQ_v3c Result",
  "type": "object",
  "required": ["repo", "language", "agq_score", "status", "components", "flags", "metadata"],
  "properties": {
    "repo":     { "type": "string", "description": "Repository name or path" },
    "language": { "type": "string", "enum": ["java", "python"] },
    "agq_score": {
      "type": "number",
      "minimum": 0, "maximum": 1,
      "description": "AGQ_v3c score"
    },
    "status": {
      "type": "string",
      "enum": ["green", "amber", "red", "red*", "ineligible", "invalid"],
      "description": "red* = absolute floor (FF2) triggered"
    },
    "components": {
      "type": "object",
      "properties": {
        "M":          { "type": "number" },
        "A":          { "type": "number" },
        "S":          { "type": "number" },
        "C":          { "type": "number" },
        "CD":         { "type": "number" },
        "flat_score": { "type": ["number", "null"], "description": "Python only; null for Java" }
      },
      "required": ["M", "A", "S", "C", "CD", "flat_score"]
    },
    "flags": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id":          { "type": "string" },
          "label":       { "type": "string" },
          "experimental":{ "type": "boolean" }
        }
      }
    },
    "baseline_comparison": {
      "type": ["object", "null"],
      "description": "Present when main-branch baseline is available",
      "properties": {
        "main_agq":   { "type": "number" },
        "main_cd":    { "type": "number" },
        "delta_agq":  { "type": "number" },
        "delta_cd":   { "type": "number" },
        "ff1_triggered": { "type": "boolean" }
      }
    },
    "ff1": {
      "type": "string",
      "description": "skipped (no baseline) | triggered | not triggered"
    },
    "metadata": {
      "type": "object",
      "properties": {
        "nodes":         { "type": "integer" },
        "spec_version":  { "type": "string", "const": "v1" },
        "scanner":       { "type": "string" },
        "timestamp_utc": { "type": "string", "format": "date-time" }
      }
    }
  }
}
```

### 5.2 Markdown Report Template (human-readable)

```markdown
# AGQ Report — {repo}

| Field        | Value                          |
|--------------|-------------------------------|
| Language     | {language}                     |
| AGQ Score    | {agq_score:.3f}                |
| Status       | **{STATUS}**                   |
| Nodes        | {nodes}                        |
| Spec Version | v1                             |
| Scanned At   | {timestamp_utc}                |

## Component Breakdown

| Component  | Score  | Weight ({language}) |
|------------|--------|---------------------|
| M          | {M:.3f}  | {w_M}             |
| A          | {A:.3f}  | {w_A}             |
| S          | {S:.3f}  | {w_S}             |
| C          | {C:.3f}  | {w_C}             |
| CD         | {CD:.3f} | {w_CD}            |
| flat_score | {flat_score:.3f} | {w_flat} *(Python only)* |

## Status Thresholds ({language})

GREEN ≥ 0.55 | AMBER 0.42–0.55 | RED < 0.42  *(Python values shown)*

## Flags

{flags_table_or_"No flags raised."}

## Baseline Comparison (vs main branch)

{baseline_section_or_"No baseline available — FF1 skipped."}

## Notes

- Thresholds calibrated on OSS repos (EV-01). Enterprise distributions may differ.
- `god_module_risk` flag is experimental (not individually significant).
```

---

## 6. Limitations

| Reference | Limitation |
|-----------|-----------|
| **EV-01** | OSS bias: GT and threshold calibration used top-starred GitHub repos. Enterprise, internal-tooling, or low-visibility repos may score differently. Recalibrate thresholds after pilot using ≥ 20 labelled internal repos. |
| **CV-02** | DDD bias: The GT over-represents domain-driven design patterns. Repositories following alternative architectural styles (layered monoliths, pipeline-oriented code) may be penalised unfairly. |
| **EV-04** | Type E blind spot: "Type E" repos (flat but intentionally simple, e.g. build tools, CLI utilities) produce high `flat_score` despite being genuinely well-designed. `buildbot` is a confirmed false negative (flat\_score=0.946). Apply domain context before acting on a GREEN status in this category. |
| — | **v1 thresholds are provisional.** They are subject to recalibration after the pilot phase. Do not use as contractual SLAs until v2. |
| — | **god\_module\_risk is experimental.** Directionally correct on GT (partial\_r=−0.217) but not individually significant (p=0.249). Must not be used as a standalone gate. |
| — | **No multi-module support.** Composite projects must be scored per module; aggregation strategy is undefined in v1. |
| — | **Rust scanner unavailable.** `_qse_core` is not available in the current environment; all scanning runs through Python-based scanners, which may differ in performance on very large repos (nodes > 5000). |

---

## Appendix: CLI Invocation Reference

```
qse score \
  --repo <path|url> \
  --lang <java|python> \
  [--baseline-branch main] \
  [--output <json|markdown|both>] \
  [--out-file <path>]
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | GREEN |
| 1 | AMBER |
| 2 | RED or RED\* |
| 3 | INELIGIBLE |
| 4 | INVALID / scanner error |

Exit codes enable use as a CI/CD gate: `exit 2` on RED can block a merge.

---

*Spec version v1 — subject to revision post-pilot. See EV-01, CV-02, EV-04 for known calibration risks.*
