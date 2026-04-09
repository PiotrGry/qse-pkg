# QSE-PKG

Quality Score Engine - silnik jakości architektonicznej dla Python, Java i Go.

## Architektura

```
qse/                          # Core (architecture-agnostic)
  graph_metrics.py            # AGQ: Modularity, Acyclicity, Stability, Cohesion
  agq_enhanced.py             # AGQ-z, AGQ-adj, Fingerprint, CycleSeverity, ChurnRisk
  extended_metrics.py         # CCD, IC, fan-out (size-normalized)
  discover.py                 # Policy discovery (architectural constraints)
  cli.py                      # CLI entry point (qse agq / qse gate / qse discover)
  test_quality.py             # QSE_test: assertion density, naming, isolation

qse-core/                     # Rust scanner (PRIMARY - tree-sitter, PyO3)
qse-py/                       # PyO3 bindings → _qse_core
```

Pakiet: `pip install git+https://github.com/PiotrGry/qse-pkg.git`
CLI: `qse agq <path> --threshold 0.80 --output-json report.json`
Rust scanner: `maturin develop --release -m qse-py/Cargo.toml`

## Source of Truth

Indeks autorytatywnych plików: `artifacts/DOCUMENT_MAP.md`

---

## Role

Wybierz rolę odpowiednią do zadania:

| Rola | Plik | Kiedy używać |
|---|---|---|
| Analityk badawczy | `ROLE_RESEARCH.md` | interpretacja wyników, hipotezy, pipeline CI/CD, papier |
| Inżynier QSE | `ROLE_ENGINEER.md` | implementacja metryk, refaktoryzacja detektorów, walidacja |
