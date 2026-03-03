# QSE — Quality Score Engine

Automatic DDD architecture quality validator for Python codebases.
Detects structural defects in Domain-Driven Design code and computes a composite quality score.

## What it measures

| Metric | Description | Range |
|--------|-------------|-------|
| **QSE4** | Composite architecture score (S + T_ddd + G + E) | [0, 1] |
| **QSE_test** | Test suite quality score | [0, 1] |
| **QSE_combined** | 0.7 × QSE4 + 0.3 × QSE_test | [0, 1] |

### Sub-metrics

| Symbol | Name | What it measures |
|--------|------|-----------------|
| S | Structure | Ratio of non-anemic domain entities |
| T_ddd | DDD Conformance | Layer compliance + zombie detection + naming |
| G | Graph Coupling | Import graph density (lower = better) |
| E | Excess Complexity | Absence of fat services |

### Defect detectors

| Detector | Method | F1 (mutation study, n=900) |
|----------|--------|---------------------------|
| Anemic Entity | AST: class with only `__init__`, no domain methods | **1.000** |
| Fat Service | Sigmoid: service with excessive method count | **1.000** |
| Zombie Entity | AST symbol-map + transitive closure (v2) | **0.964** |
| Layer Violation | Import graph: presentation → domain direct import | **0.615** |

## Installation

```bash
pip install git+https://github.com/PiotrGry/qse.git
```

## Usage

### Scan a repository (report only)

```bash
qse scan path/to/repo
qse scan path/to/repo --format json
qse scan path/to/repo --format json --output-json report.json
```

### Quality gate (exits non-zero on failure)

```bash
# Fail if QSE4 < 0.80 or any anemic/zombie/layer defects found
qse gate path/to/repo \
  --threshold 0.80 \
  --fail-on-defects anemic_entity,zombie_entity,layer_violation \
  --output-json gate_report.json
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--threshold N` | 0.80 | Minimum QSE4 score |
| `--fail-on-defects LIST` | — | Comma-separated defect types that must be zero |
| `--output-json FILE` | — | Write JSON report to file |
| `--no-trace` | off | Skip dynamic tracing (faster, static only) |
| `--format table\|json` | table | Output format (scan command) |

## GitHub Actions integration

Three pipelines available in `.github/workflows/`:

- **pipeline-qse.yml** — QSE gate only
- **pipeline-analyzers.yml** — Static + dynamic analyzers (ruff, mypy, bandit, radon, pylint, pytest-cov)
- **pipeline-full.yml** — QSE + all analyzers combined

Example for QSE gate in your workflow:

```yaml
- name: Install QSE
  run: pip install git+https://github.com/PiotrGry/qse.git

- name: QSE gate
  run: |
    qse gate src/ \
      --threshold 0.80 \
      --fail-on-defects anemic_entity,zombie_entity,layer_violation \
      --output-json qse_report.json \
      --no-trace
```

## Expected repository structure

QSE detects layers from directory names:

```
your_project/
  domain/        ← domain entities, value objects, aggregates
  application/   ← services, use cases, commands/queries
  infrastructure/← repositories, external APIs, DB adapters
  presentation/  ← controllers, CLI, API handlers
```

## Empirical validation

Validated on a mutation study (900 runs, 4 defect types × 6 doses × 30 seeds):

- Monotonicity: Spearman ρ = -0.986, p < 10⁻¹⁴⁰
- Discrimination: Mann-Whitney U = 900 (max), p < 10⁻¹¹
- Effect size: Cohen's d = 6.8–129.2

## License

MIT
