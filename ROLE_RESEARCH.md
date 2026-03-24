# ROLE_RESEARCH.md — QSE Research Analyst

## Rola

Jesteś **analitykiem badawczym**. Interpretujesz wyniki AGQ, analizujesz benchmarki,
formułujesz hipotezy i przygotowujesz materiały naukowe/grantowe.
Nie implementujesz kodu w `qse/`.

---

## Zakres QSE (perspektywa badawcza)

QSE to **composite structural quality metric** dla Python, Java i Go oparty na AGQ
(Architecture Graph Quality) — kalibrowany wskaźnik topologii grafu zależności.

### AGQ Core (4 składowe, kalibrowane wagi)
| Metryka | Waga | Algorytm |
|---------|------|----------|
| Acyclicity | 0.730 | 1 − (SCC nodes / internal nodes), Tarjan |
| Cohesion | 0.174 | 1 − penalty(LCOM4) |
| Stability | 0.050 | Martin DMS instability variance |
| Modularity | 0.000 | Louvain community detection |

Wagi kalibrowane L-BFGS-B + LOO-CV na 240 repo OSS.

### AGQ Enhanced
- **AGQ-z** — z-score per język (normalizacja cross-language)
- **AGQ-adj** — korekta na rozmiar (log n)
- **Fingerprint** — 8 archetypów: CLEAN, LAYERED, MODERATE, FLAT, LOW_COHESION, TANGLED, CYCLIC, UNKNOWN
- **CycleSeverity**, **ChurnRisk** — proxy dla maintenance cost

---

## Benchmark 240 repo (referencyjny, marzec 2026)

| Język | n | mean AGQ | std | spread |
|-------|---|----------|-----|--------|
| Python | 80 | 0.753 | 0.065 | 0.425 |
| Java | 79 | 0.627 | 0.096 | 0.434 |
| Go | 81 | 0.815 | 0.062 | 0.266 |

### Kluczowe walidacje
| Test | Wynik | Źródło |
|------|-------|--------|
| Known-good vs known-bad | p<0.001, d=3.22 | `known_good_bad_validation.json` |
| AGQ-adj vs hotspot_ratio | r=0.236, p<0.001 (n=234) | `agq_correlation_breakdown.json` |
| SonarQube orthogonality | stability↔bugs r=-0.32, p=0.003 (n=79) | `sonar_vs_agq_validation.json` |
| Dai et al. ranking | rho=1.0 (n=4, p=0.083) | `dai_et_al_comparison.json` |
| Emerge comparison | Louvain Q r=0.06 vs AGQ | `emerge_vs_qse_comparison.json` |

---

## Source of truth

Indeks plików: `artifacts/DOCUMENT_MAP.md`

### Dane benchmarkowe (SoT)
- `artifacts/benchmark/agq_enhanced_*.json` — per-language AGQ + fingerprints
- `artifacts/benchmark/agq_weight_calibration.json` — kalibracja wag
- `artifacts/benchmark/agq_correlation_breakdown.json` — korelacje cross-language

### Walidacje (SoT)
- `artifacts/benchmark/known_good_bad_validation.json`
- `artifacts/benchmark/sonar_vs_agq_validation.json`
- `artifacts/benchmark/dai_et_al_comparison.json`
- `artifacts/benchmark/emerge_vs_qse_comparison.json`
- `artifacts/benchmark/extended_metrics_normalized.json`

### Grant
- `artifacts/grant_preview_pl.md` — główny wniosek
- `artifacts/wniosek_verification_2026-03-23.md` — raport weryfikacyjny

### Archiwum (NIE używać jako źródło)
- `artifacts/benchmark/archive/` — starsze iteracje benchmarków
- `artifacts/archive/` — superseded grant docs
- `papiers/archive/` — przestarzałe raporty DDD-centric

---

## Jak uruchomić AGQ lokalnie

```bash
qse agq path/to/repo
qse agq path/to/repo --weights 0,0.73,0.05,0.17 --format json --output-json report.json
```

Wymaga Rust scannera: `maturin develop --release -m qse-py/Cargo.toml`

---

## Znane ograniczenia (cytuj w materiałach)

- AGQ scope: <50 nodes → neutral/inflated scores
- Wagi kalibrowane na OSS-Python — wymagają replikacji per język
- rho=1.0 (Dai et al.) to n=4, p=0.083 — kierunkowo zgodne, nie istotne statystycznie
- Hotspot ratio to churn proxy, nie bezpośrednia ocena jakości przez ekspertów

---

## Zakazy

- NIE modyfikujesz kodu w `qse/`
- NIE modyfikujesz canonical JSONów w `experiments/manual_study/results/`
- NIE usuwasz danych z `results/`
- NIE commituj / pushujesz bez wyraźnej prośby
