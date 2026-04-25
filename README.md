# QSE — Quality Score Engine

**Algorithmic harness for AI-generated code.** A deterministic, vendor-neutral gate
that detects architectural regressions in Python codebases — before they reach
the repo. No AI in the enforcement path. Pure graph mathematics.

## Why this exists

AI coding agents (Cursor, Copilot, Claude Code, raw API scripts) generate code
at scale. The code is locally correct but globally damaging:
- closes dependency cycles humans would notice while reading
- creates god-files via lazy imports
- floods codebases with isolated/dead modules

QSE sits between AI output and the codebase. Math-based. Vendor-neutral. Blocks
structural regressions deterministically.

## What QSE measures

QSE provides **architectural structural visibility** — not quality prediction.
Metrics are deterministic, fast (46× faster than SonarQube on the same scan),
and language-aware. Predictive validity against bug rates is under empirical
investigation; current evidence supports structural visibility, not causal
quality prediction.

| Metric | What it measures | Algorithm |
|--------|------------------|-----------|
| **Propagation Cost (PC)** | What fraction of code a random change ripples through | CCD/n² via condensation + bitset propagation, O(n²/64) |
| **Relative Cyclicity (RC)** | Severity of cyclic dependency groups | 100×√(Σsize²)/n |
| **hub_score** | God-file detector: high fan-in AND fan-out | fan_in × fan_out per node |
| **SCC count** | Cycle group count (Tarjan) | strongly connected components ≥2 |
| **isolated_pct** | Archipelago detector: dead/disconnected modules | nodes with degree 0 |

Source: von Zitzewitz (2022), *Software Architecture Metrics* — thresholds derived from 300+ architectural assessments.

## Primary product: `qse gate-diff`

Delta-based architectural CI gate. Compares dependency graphs at two git refs.

```bash
qse gate-diff --base origin/main --head HEAD
# exit 0 = PASS, exit 1 = FAIL (violations printed), exit 2 = infra error
```

Detects:
- New cycles (zero tolerance)
- Propagation Cost crossing threshold
- Relative Cyclicity exceeding threshold
- Hub-score spikes (god-file emergence)
- Archipelago drift (isolated modules accumulating)

All checks are **delta-based** — flags regressions, not pre-existing baseline state.
Pre-existing cycles in your codebase are tolerated; new ones are blocked.

## Installation

```bash
pip install git+https://github.com/PiotrGry/qse-pkg.git
```

## Usage

### CI gate (recommended primary use)

```bash
# In your GitHub Actions / GitLab CI
qse gate-diff --base origin/main --head HEAD --output-json gate.json
```

### Inspect current architecture (advisory)

```bash
qse agq path/to/repo
```

Reports current AGQ score (modularity, acyclicity, stability, cohesion).
Note: absolute AGQ values do not predict bug rates in current evidence.
Use deltas via `gate-diff` for actionable signal.

### Architectural boundary discovery

```bash
qse discover path/to/repo
```

Detects natural module clusters and proposes constraints.

### Architectural hotspots (the moat)

```bash
qse hotspot path/to/repo --since "1 year ago" --top 10
```

Hybrid metric: **git churn × structural centrality**. Files high on both
axes are where bugs happen and refactors hurt. Score is the product
(both normalized to [0,1]) so files high on only one axis score low —
only the overlap matters.

| Tool | Behavioral signal | Structural signal |
|---|---|---|
| SonarQube | ✗ | ✓ (size, complexity) |
| CodeScene (Tornhill) | ✓ (churn × LOC) | ✗ |
| **QSE hotspot** | **✓** | **✓ (graph centrality)** |

Output ranks files by combined score and explains the math. Wire into
`qse health --include-hotspots` to cross-reference with the structural
fingerprint (TANGLED + hotspot → "untangle FIRST", LOW_COHESION + hotspot
→ "split by responsibility", etc.). Wire into `qse gate-diff
--check-hotspots` so PRs that touch hotspots AND introduce architectural
violations get an elevated-risk banner in CI.

### Long-running refactors

```bash
qse gate-diff --base origin/main --head HEAD \
              --migration-baseline <commit-where-refactor-started>
```

Three-reference policy: HEAD evaluated vs `main` AND vs the migration
start. Tolerates "in-migration" intermediate states (HEAD worse than
main but better than migration baseline → PASS) without losing strict
mode for true regressions (HEAD worse than both → FAIL).

## Empirical validation status

| Claim | Evidence | Status |
|-------|----------|--------|
| Deterministic (max_score_delta < 1e-9) | `agq_thesis_oss80_v4.json` T1 | **Validated** |
| 46× faster than SonarQube | `agq_thesis_oss80_v4.json` T4 | **Validated** |
| Score spread = 0.548 | `agq_thesis_oss80_v4.json` T5 | **Validated** |
| Predicts code churn hotspots | `agq_thesis_oss80_v4.json` T2 | **Falsified in v4 — under investigation** |
| Per-language thresholds calibrated | 240-repo benchmark (Python-80, Java-79, Go-81) | **Distribution measured; predictive validity pending** |

See `docs/QSE_CLAIMS_AND_EVIDENCE.md` for the full claim audit.

## Architecture

```
qse/
  graph_metrics.py          # PC, RC, AGQ components
  scanner.py                # AST → networkx.DiGraph
  gate/
    gate_check.py           # delta-based gate API
    hook_runner.py          # Claude Code PreToolUse hook (vendor-specific)
  cli.py                    # `qse gate-diff`, `qse agq`, `qse discover`
```

Rust core (`qse-core/`) provides 7-46× faster scanning for Python, Java, Go.

## License

MIT
