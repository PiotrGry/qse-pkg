---
type: explainer
audience: beginner
language: pl
---

# Aktualny stan prostymi słowami

## Prostymi słowami

QSE to nie tylko pomysł. Ma już działające formuły, przetestowane hipotezy i udowodnione wyniki na 558 repozytoriach. Niektóre pytania są już rozstrzygnięte z solidnymi danymi. Inne są nadal otwarte i czekają na kolejne eksperymenty. Ta strona mówi wprost, co jest gdzie.

---

## Szczegółowy opis

### Co działa i jest gotowe do użycia

| Komponent | Status | Lokalizacja |
|---|---|---|
| AGQ Core (metryki M, A, S, C, CD) | ✅ Zaimplementowany, 149 testów | `qse/graph_metrics.py` |
| AGQ Enhanced (AGQ-z, Fingerprint, CycleSeverity, ChurnRisk, AGQ-adj) | ✅ Zaimplementowany | `qse/agq_enhanced.py` |
| Skaner Rust (Python, Java, Go) | ✅ Działający, 7–46× szybszy | `qse-core/` |
| Skaner Python/Java (czysty Python, tree-sitter) | ✅ Działający | `qse/scanner.py`, `qse/java_scanner.py` |
| CLI: `qse agq`, `qse discover` | ✅ Działają | `qse/cli.py` |
| QSE_test (metryki jakości testów) | ✅ Zaimplementowany | `qse/test_quality.py` |
| Pre-commit / CI/CD integracja | ✅ Dostępna przez CLI | — |
| flat_score dla Pythona | ✅ Zaimplementowany | `qse/flat_metrics.py` |

### Co zostało udowodnione empirycznie

#### Java Ground Truth (n=59) — KLUCZOWY WYNIK

```
Java GT — expanded (n=59, 31 POS / 28 NEG)
  POS mean AGQ = 0.571
  NEG mean AGQ = 0.486
  Gap = 0.085

  Mann-Whitney U p = 0.000221  ← wysoce istotny
  Spearman ρ     = 0.380 (p=0.003)
  Partial r      = 0.447 (p=0.0004)
  AUC-ROC        = 0.767
```

Metodologia: 4 symulowanych ekspertów ocenia repozytoria w skali 1–10. Panel score = średnia 4 ocen. σ ≤ 2.0 (wymóg zgodności). Label: panel ≥ 6.0 → POS.

#### Jolak cross-validation (8 repozytoriów)

8 repozytoriów z badania Jolak et al. (2025) przeskanowanych skanerem Java QSE:
- Średnia AGQ v3c = 0.535 (pomiędzy GT-POS=0.585 a GT-NEG=0.470 — zgodnie z oczekiwaniem)
- **4/5 wyników POTWIERDZONE, 1 PRAWDOPODOBNE**

#### Benchmark OSS (558 repozytoriów)

- Brak korelacji AGQ z SonarQube (n=78, wszystkie p>0.10) → komplementarne narzędzia
- Korelacja AGQ-adj z hotspot_ratio: r=+0.236, p<0.001
- Korelacja AGQ-adj z churn_gini: r=−0.154, p=0.018
- Language bias: Go cohesion=1.0 zawsze (strukturalne), Java cohesion=0.38 średnio
- Go: 0% projektów z cyklami; Java: 71% projektów z cyklami; Python: 4%

### Aktualne priorytety — tabela P0–P4

| ID | Zadanie | Status | Szczegóły |
|---|---|---|---|
| **P0** | Rozszerzenie Java GT do n≥50 | ✅ ZROBIONE | n=59, commit b336496 |
| **P1** | Jolak cross-validation | ✅ ZROBIONE | 4/5 POTWIERDZONE |
| **P2** | Badanie god_class_ratio | ✅ ZROBIONE | Nie dodajemy do formuły |
| **P3** | Analiza false-negative Django | ✅ ZROBIONE | Potrzeba lepszego wykrywania |
| **P4** | Re-run Java-S na rozszerzonym GT | ⏳ NASTĘPNY KROK | Odblokowany przez P0 |

### Co jest planowane badawczo (jeszcze nie istnieje)

| Plan | Dlaczego nie teraz |
|---|---|
| Kalibracja wag per język (Java, Go osobno) | Obecna kalibracja tylko na OSS-Python |
| Warstwa Predictor (ML, predykcja ryzyka) | Wymaga osobnego datasetu z etykietami procesowymi |
| Walidacja na projektach przemysłowych | Cały benchmark to open-source |
| Expert labeling z prawdziwymi architektami | Pilotaż w planie |
| Temporal AGQ (analiza driftu przez git) | Wymaga analizy historii commitów |

> 🔴 **Warstwa Predictor nie istnieje w obecnej wersji systemu.** AGQ jest narzędziem *diagnostycznym*, nie predykcyjnym. To planowany kierunek badawczy, nie zaplanowana funkcja do wdrożenia w konkretnym terminie.

---

## Definicja formalna — wyniki per-komponent (Java GT n=59)

Tabela dyskryminacji per komponent — które składowe AGQ najlepiej oddzielają POS od NEG:

| Składowa | Śr. POS | Śr. NEG | Δ | MW p | Istotność |
|---|---|---|---|---|---|
| Modularity (M) | 0.668 | 0.648 | +0.021 | 0.226 | ns |
| Acyclicity (A) | 0.994 | 0.974 | +0.020 | 0.030 | * |
| Stability (S) | 0.344 | 0.238 | +0.106 | 0.016 | * |
| Cohesion (C) | 0.393 | 0.269 | +0.124 | 0.0002 | *** |
| Coupling Density (CD) | 0.454 | 0.299 | +0.155 | 0.004 | ** |

**Kluczowy wniosek:** C i CD to najsilniejsze indywidualne dyskryminatory. M samo w sobie nie jest istotne statystycznie.

### Znane ograniczenia

1. **Utility libraries** (Guava, commons-lang, commons-collections): Dostają niski AGQ mimo dobrego projektu. Płaska struktura pakietów → niskie CD. Potrzeba normalizacji uwzględniającej kategorię projektu.
2. **Małe NEG repos** (shopping-cart, training-monolith): Prosta struktura zawyża M/CD. Panel ekspertów to wykrywa, metryki same nie.
3. **Django false-negative**: Django dostaje NEG mimo dobrej architektury. Przyczyna: skaner wymaga lepszego wykrywania wewnątrz-pakietowego.

---

## Stan aktualny w jednym zdaniu

> QSE ma działające narzędzia, empirycznie zwalidowany Ground Truth dla Javy (n=59, p<0.001) i potwierdzenie przez Jolak cross-validation (4/5). Następnym krokiem jest P4: re-run eksperymentu Java-S na rozszerzonym GT.

---

## Zobacz też
[[Current Priorities]] · [[Ground Truth]] · [[Hypotheses Register]] · [[Experiments Index]] · [[Roadmap]]
