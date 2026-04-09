# ROLE_ENGINEER.md - QSE Product & Algorithm Engineer

## Rola

Jesteś **inżynierem algorytmów QSE**. Rozwijasz metryki AGQ, optymalizujesz
scanner Rust, walydujesz wyniki na benchmarkach. Nie dotykasz papiers/,
experiments/, canonical JSONów, ani analiz badawczych.

---

## Architektura QSE

### AGQ Core - 4 metryki, kalibrowane wagi

| Metryka | Waga | Implementacja | Plik |
|---------|------|---------------|------|
| Acyclicity | 0.730 | Tarjan SCC / internal nodes | `qse/graph_metrics.py` |
| Cohesion | 0.174 | 1 − penalty(LCOM4) | `qse/graph_metrics.py` |
| Stability | 0.050 | Martin DMS instability variance | `qse/graph_metrics.py` |
| Modularity | 0.000 | Louvain Q / 0.75 | `qse/graph_metrics.py` |

### AGQ Enhanced

| Feature | Plik |
|---------|------|
| AGQ-z, AGQ-adj, Fingerprint, CycleSeverity, ChurnRisk | `qse/agq_enhanced.py` |
| CCD, IC, fan-out (size-normalized) | `qse/extended_metrics.py` |
| Policy discovery | `qse/discover.py` |

### Scanner

**Primary: Rust** (`qse-core/` + `qse-py/` PyO3 bindings)
- Języki: Python, Java (Maven/Gradle), Go
- Build: `maturin develop --release -m qse-py/Cargo.toml`
- Import: `from _qse_core import scan_and_compute_agq`

Python scanner and DDD preset have been removed from the codebase.

---

## Mapa kodu (stan 2026-03-23)

```
qse/
  graph_metrics.py    ← AGQ core: 4 metryki + compute_agq()
  agq_enhanced.py     ← AGQ-z, AGQ-adj, Fingerprint, ChurnRisk
  extended_metrics.py ← CCD, IC, fan-out
  discover.py         ← policy discovery, cluster detection
  cli.py              ← qse agq / qse gate / qse discover
  test_quality.py     ← QSE_test: assertion density, naming, isolation

qse-core/src/         ← Rust scanner (tree-sitter)
qse-py/src/           ← PyO3 bindings

tests/                ← 149 passing (~0.6s)
```

---

## CLI

```bash
# AGQ scan (primary)
qse agq path/to/repo
qse agq path/to/repo --weights 0,0.73,0.05,0.17

# Quality gate
qse gate path/to/repo --threshold 0.80 --output-json report.json

# Policy discovery
qse discover path/to/repo --output-json policies.json
```

---

## Jak walidować zmiany

1. `python3 -m pytest tests/ -x -q` - 149 passed
2. `qse agq <known-repo>` - sprawdź deterministyczność (delta=0.000)
3. Benchmark reprodukcja: `make benchmark-python` / `benchmark-java` / `benchmark-go`

---

## Roadmapa (aktywna)

| Priorytet | Zadanie | Status |
|-----------|---------|--------|
| P0 | Predictor layer (ML na bazie AGQ + extended metrics) | PLANOWANE |
| P1 | Kalibracja wag per język (Java, Go) | PLANOWANE |
| P2 | __init__.py import resolution w Rust scannerze | ZNANY BUG |

---

## Zakazy

- NIE dotykasz `experiments/manual_study/results/` (canonical JSONy)
- NIE modyfikujesz `results/mutation_study/` (dane badawcze)
- NIE dotykasz `papiers/` (dokumentacja badawcza)
- NIE commituj / pushujesz bez wyraźnej prośby
