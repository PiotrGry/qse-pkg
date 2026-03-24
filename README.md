# QSE — Quality Score Engine

Automatic architecture quality scoring for Python, Java, and Go codebases.
Computes **AGQ** (Architecture Graph Quality) — a calibrated composite of four graph-based metrics.

## Architecture

### AGQ Core (zero-config)

Graph-based metrics computed on any project's import/dependency graph.

| Metric | Algorithm | Calibrated Weight |
|--------|-----------|-------------------|
| **Acyclicity** | 1 − (SCC nodes / internal nodes), Tarjan | 0.730 |
| **Cohesion** | 1 − penalty(LCOM4), absolute scale | 0.174 |
| **Stability** | Martin DMS instability variance | 0.050 |
| **Modularity** | Louvain community detection | 0.000 |

Weights calibrated via L-BFGS-B + LOO-CV on 240 OSS repositories.

### AGQ Enhanced

| Feature | Description |
|---------|-------------|
| **AGQ-z** | Language-normalized z-score |
| **AGQ-adj** | Size-adjusted score (log n) |
| **Fingerprint** | Topology archetype: CLEAN, LAYERED, MODERATE, FLAT, LOW_COHESION, TANGLED, CYCLIC, UNKNOWN |
| **CycleSeverity** | Weighted cycle impact |
| **ChurnRisk** | Maintenance cost proxy |

### Scanner

Primary scanner is written in **Rust** (tree-sitter) with PyO3 bindings — 7-46× faster than the legacy Python scanner.

```bash
# Build Rust scanner
maturin develop --release -m qse-py/Cargo.toml
```

Supported languages: Python, Java (Maven/Gradle), Go.

## Installation

```bash
pip install git+https://github.com/PiotrGry/qse-pkg.git
```

## Usage

### AGQ scan

```bash
qse agq path/to/repo
qse agq path/to/repo --weights 0,0.73,0.05,0.17
qse agq path/to/repo --format json --output-json report.json
```

### Policy discovery

```bash
qse discover path/to/repo --output-json policies.json
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--threshold N` | 0.70 | Minimum AGQ score |
| `--output-json FILE` | — | Write JSON report to file |
| `--no-trace` | off | Skip dynamic tracing (faster, static only) |
| `--config FILE` | — | JSON config with weights, thresholds |

## GitHub Actions

```yaml
- name: Install QSE
  run: pip install git+https://github.com/PiotrGry/qse-pkg.git

- name: QSE gate
  run: qse gate src/ --threshold 0.80 --output-json qse_report.json --no-trace
```

## Empirical validation

- **240 OSS repos** (Python-80, Java-79, Go-81), pinned commits, deterministic (delta=0.000)
- **Known-good vs known-bad**: p<0.001, Cohen's d=3.22
- **Churn correlation**: AGQ-adj vs hotspot_ratio r=0.236, p<0.001 (n=234)
- **SonarQube orthogonality**: stability↔bugs/KLOC r=-0.32, p=0.003 (n=79)
- **Dai et al. agreement**: 4/4 Java projects, rank rho=1.0
- **Emerge comparison**: Louvain Q alone r=0.06 vs AGQ — composite outperforms single metric

See `artifacts/DOCUMENT_MAP.md` for full evidence index.

## License

MIT
