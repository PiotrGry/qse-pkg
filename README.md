# QSE — Quality Score Engine

Automatic architecture quality validator for Python codebases.
Two-layer design: **Core AGQ** (architecture-agnostic graph metrics) + optional **DDD preset** (domain-specific detectors).

## Architecture

### Level 1: Core AGQ (zero-config)

Graph-based metrics computed on any Python project — no assumptions about architecture style.

| Metric | Algorithm | Range |
|--------|-----------|-------|
| **Modularity** | Louvain community detection | [0, 1] |
| **Acyclicity** | 1 − (SCC nodes / total nodes), Tarjan | [0, 1] |
| **Stability** | Martin DMS + abstractness detection | [0, 1] |
| **Cohesion** | 1 − penalty(LCOM4), absolute scale | [0, 1] |
| **Coupling variance** | Instability distribution uniformity | [0, 1] |

### Level 2: DDD Preset (opt-in via `layer_map`)

DDD-specific detectors activated when `layer_map` is configured or `domain/` directory exists.

| Detector | Method | F1 (mutation study, n=900) |
|----------|--------|---------------------------|
| Anemic Entity | AST: class with only `__init__`, no domain methods | **1.000** |
| Fat Service | Sigmoid: service with excessive method count | **1.000** |
| Zombie Entity | AST symbol-map + transitive closure (v2) | **0.964** |
| Layer Violation | Import graph: presentation → domain direct import | **0.615** |

## Installation

```bash
pip install git+https://github.com/PiotrGry/qse-pkg.git
```

## Usage

### Quality gate (exits non-zero on failure)

```bash
qse gate path/to/repo --threshold 0.80 --output-json report.json

# With DDD defect checks
qse gate path/to/repo \
  --threshold 0.80 \
  --fail-on-defects anemic_entity,zombie_entity,layer_violation \
  --output-json gate_report.json

# TRL4 gate (QSE + constraints + ratchet)
qse trl4 path/to/repo \
  --config scripts/trl4_weekend_config.json \
  --output-json trl4_gate_report.json \
  --no-trace
```

### Scan (report only)

```bash
qse scan path/to/repo
qse scan path/to/repo --format json --output-json report.json
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--threshold N` | 0.80 | Minimum QSE4 score |
| `--fail-on-defects LIST` | — | Comma-separated defect types that must be zero |
| `--output-json FILE` | — | Write JSON report to file |
| `--no-trace` | off | Skip dynamic tracing (faster, static only) |
| `--config FILE` | — | JSON config with weights, layer_map, thresholds |

## TRL4 Weekend Pack

Integrated validation suite (constraints detection, ratchet regression block, reproducibility, benchmark snapshot):

```bash
python3 scripts/trl4_weekend_validation.py \
  --config scripts/trl4_weekend_config.json \
  --output-json artifacts/trl4/validation.json \
  --output-md artifacts/trl4/validation.md
```

Heavy benchmark (comparable legacy vs exp4 baseline):

```bash
python3 scripts/trl4_heavy_benchmark.py \
  --output-json artifacts/trl4/heavy_benchmark.json \
  --output-md artifacts/trl4/heavy_benchmark.md
```

## GitHub Actions

```yaml
- name: Install QSE
  run: pip install git+https://github.com/PiotrGry/qse-pkg.git

- name: QSE gate
  run: qse gate src/ --threshold 0.80 --output-json qse_report.json --no-trace
```

## Empirical validation (TRL 3)

- **EXP1**: Smoke test on 5 OSS repos (httpx, fastapi, black, flask, pyjwt) — all produce valid AGQ scores
- **EXP2**: Mutation testing — 4/4 mutations detected (cycle, cross-module, god class, spaghetti)
- **EXP3**: Sensitivity analysis — 10 synthetic repos, monotonic AGQ degradation (std 0.11–0.43)
- **EXP4**: Constraints engine — forbidden edges with glob matching, 4/4 scenarios pass

## License

MIT
