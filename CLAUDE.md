# QSE-PKG

Quality Score Engine — dwuwarstwowy silnik jakości architektonicznej dla Pythona.

## Architektura

```
qse/                          # Core (architecture-agnostic)
  scanner.py                  # AST parser: klasy, importy, abstrakcyjność
  graph_metrics.py            # AGQ: Modularity, Acyclicity, Stability, Cohesion
  hybrid_graph.py             # Merge static + dynamic edges
  tracer.py                   # Dynamic tracing via sys.settrace
  test_quality.py             # QSE_test: assertion density, naming, isolation
  cli.py                      # CLI entry point (qse scan / qse gate)

qse/presets/ddd/              # DDD Extension (opt-in via layer_map)
  detectors.py                # anemic, fat, zombie, layer violation
  symbol_map.py               # Zombie v2 (AST symbol map, F1=0.964)
  metrics.py                  # S, T_ddd, G, E, Risk
  aggregator.py               # QSE_total weighted sum
  calibrator.py               # Weight calibration (L-BFGS-B + LOO-CV)
  pipeline.py                 # scan → trace → graph → metrics → defects
  gate.py                     # Quality gate with feedback prompts
  config.py                   # QSEConfig with layer_map
  report.py                   # JSON/table formatters
  generate_loop.py            # LLM code generation loop with gate
```

Pakiet: `pip install git+https://github.com/PiotrGry/qse-pkg.git`
CLI: `qse gate <path> --threshold 0.80 --config qse.json --output-json report.json`

---

## Role

Wybierz rolę odpowiednią do zadania:

| Rola | Plik | Kiedy używać |
|---|---|---|
| Analityk badawczy | `ROLE_RESEARCH.md` | interpretacja wyników, hipotezy, pipeline CI/CD, papier |
| Inżynier QSE | `ROLE_ENGINEER.md` | implementacja metryk, refaktoryzacja detektorów, walidacja |
