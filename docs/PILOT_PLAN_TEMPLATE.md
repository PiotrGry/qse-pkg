# QSE Architecture Test — Pilot Plan

Version: 1.0
Date: April 2026

---

## Pilot 1 — Open Source Repository

### Setup

| Field | Value |
|-------|-------|
| Repository | [TBD — select Java or Python OSS repo meeting criteria] |
| Language | Java / Python |
| Criteria | nodes ≥ 100, no multi-module, no TypeScript, active development |
| Duration | 4–6 weeks |
| Mode | Non-blocking (advisory only) |
| Contact | [Maintainer name] |

### Integration

1. Add `qse-archtest` GitHub Action to CI pipeline
2. Configure to run on every PR (non-blocking)
3. Output: JSON artifact + Markdown comment on PR

### Configuration

```yaml
# .github/workflows/archtest.yml
thresholds:
  java:
    green: 0.55
    amber: 0.45
    red: 0.40
  python:
    green: 0.55
    amber: 0.42
    red: 0.35
fitness_functions:
  ff1_regression_delta: 0.05
  ff1_cd_delta: 0.05
  ff2_floor_java: 0.40
  ff2_floor_python: 0.35
```

### Data Collection

- [ ] Number of test runs
- [ ] Distribution of statuses (green / amber / red)
- [ ] Number of PRs where amber/red triggered additional review
- [ ] Number of PRs where amber/red led to refactoring
- [ ] Number of false positives (amber/red for clearly good PRs)
- [ ] Number of blind spots (green for clearly bad changes)

### Feedback Survey (Week 4–6)

1. Which signals were most useful? (high coupling, flat structure, cohesion warning, regression guard)
2. Which signals were misleading or noisy?
3. Did any PR get amber/red and cause a real action (refactor, module split, additional review)?
4. Would you want this as a soft gate (blocking red)?
5. What threshold adjustments would you suggest?

---

## Pilot 2 — Internal Project

### Setup

| Field | Value |
|-------|-------|
| Project | [TBD — internal Java/Python project with active development] |
| Language | Java / Python |
| Team size | [N developers] |
| Duration | 4–6 weeks |
| Mode | Non-blocking (reports to architect/tech lead) |
| Contact | [Tech lead name] |

### Integration

Same as Pilot 1, adapted for internal CI (GitHub Actions, GitLab CI, or Jenkins).

### Additional Data Points

- Architecture decision records (ADRs) influenced by test results
- Module split / refactoring decisions triggered by amber/red
- Developer satisfaction with signal quality

### Interviews (Week 4–6)

Conduct 20-minute interviews with:
- [ ] Tech lead / architect
- [ ] 2–3 senior developers
- [ ] 1 junior developer (for clarity of messaging)

Questions:
1. Did the test help in any architecture decision?
2. Give a specific example of a useful signal.
3. Give a specific example of a misleading signal.
4. Would you keep this in CI after the pilot?

---

## Post-Pilot Summary Template

### 1. Scope

| Field | Value |
|-------|-------|
| Projects | [OSS repo], [Internal project] |
| Languages | Java / Python |
| Period | [start date] – [end date] |
| Configuration | green/amber/red thresholds, FF1–FF3, non-blocking |

### 2. Quantitative Results

| Metric | OSS Pilot | Internal Pilot |
|--------|-----------|----------------|
| Total test runs | | |
| Green | | |
| Amber | | |
| Red | | |
| Amber/red → additional review | | |
| Amber/red → refactoring | | |
| Amber/red → PR rejected | | |
| False positives | | |
| Blind spots | | |

### 3. Qualitative Feedback

**Most valuable signals:**
- [e.g., coupling regression detection, flat structure warning]

**Noise / unhelpful signals:**
- [e.g., sensitivity to small changes, unclear messages]

**Reported blind spots:**
- [e.g., Type E legacy monolith not detected]

### 4. Impact Cases

**Case 1: PR #___ — [title]**
- Signal: [AGQ drop + CD increase]
- Action: [Module split / additional review / none]
- Outcome: [description]

**Case 2: PR #___ — [title]**
- Signal: [...]
- Action: [...]
- Outcome: [...]

### 5. Recommendations

**Threshold adjustments:**
- [e.g., raise amber from 0.45 to 0.50 for Java]

**Message improvements:**
- [e.g., add "expected for utility libraries" note when CD is low]

**Formula changes:**
- [e.g., reduce S weight, add god-module flag]

**Product decision:**
- [ ] Keep as advisory (non-blocking)
- [ ] Promote to soft gate (block red only)
- [ ] Expand to more projects
- [ ] Pause for further calibration

### 6. Next Steps

1. Apply threshold/message adjustments
2. Expand to N additional projects
3. Develop interpretive guide ("Q&A / Understanding Your Results")
4. Prepare for v2 with [improvements from pilot]
