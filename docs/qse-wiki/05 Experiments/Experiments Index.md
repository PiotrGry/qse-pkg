---
type: index
language: pl
---

# Indeks Eksperymentów

## Prostymi słowami

Każdy eksperyment to jedna konkretna próba odpowiedzi na pytanie: „czy ta metryka faktycznie odróżnia dobrą architekturę od złej?" Eksperymenty prowadzono na zbiorach danych Java i Python z ocenami ekspertów jako punktem odniesienia.

## Szczegółowy opis

Eksperymenty QSE mają ściśle określony protokół: maksymalnie 5 iteracji, stop po 2 iteracjach bez poprawy, bez modeli nieliniowych, bez brute-force, każda zmiana musi przeżyć falsyfikację. Pełny opis protokołu: [[How to Read Experiments]].

### Tabela eksperymentów

| ID | Tytuł | Status | Kluczowy wynik | Hipotezy |
|---|---|---|---|---|
| [[E1 Stability Hierarchy\|E1]] | Stability Hierarchy | **obalony** | r=−0.093 p=0.762 ns — S_hierarchy nie odróżnia DDD od CRUD | [[W7 Stability Hierarchy Score\|W7]] |
| [[E2 Coupling Density\|E2]] | Coupling Density (edges/nodes) | **potwierdzony** | r=−0.787 p=0.007, partial r=−0.697 — najsilniejszy pojedynczy predyktor; wchodzi do AGQ v2 jako CD | [[W4 AGQv2 Beats AGQv1 on Java GT\|W4]] |
| E3 | Package Layer Classifier | **wstrzymany** | Wymaga FQN węzłów (re-skan); GT=BLT zepsuty; ścieżka A (GT n=13) możliwa, ale nie przeprowadzona | — |
| E4 | Rozszerzenie GT panelu do n≥30 | **zakończony** | n=14 Java, AGQ v2 partial r=+0.675 p=0.008 — pierwsza liczba oparta na solidnych danych | [[W4 AGQv2 Beats AGQv1 on Java GT\|W4]] |
| [[E5 Namespace Metrics\|E5]] | NSdepth i NSgini | **częściowy** | NSdepth partial r=+0.698 p=0.008 dla Javy (silny), dla Pythona r=+0.433 ns (słaby); NSgini = brak sygnału | [[O4 Namespace Metrics for Python\|O4]] |
| [[E6 flatscore\|E6]] | flatscore dla Pythona | **potwierdzony** | partial r=+0.670 p<0.01, MW p=0.004; wchodzi do AGQ v3c Python z wagą 0.35 | [[W10 flatscore Predicts Python Quality\|W10]] |
| [[PCA Weights\|PCA]] | Wagi PCA (równe eigenvalues) | **zakończony** | Wszystkie eigenvalues prawie równe → uniform 0.20; brak naturalnej hierarchii wymiarów | — |
| [[E7 P4 Java-S Expanded\|E7]] | **P4 Java-S na expanded GT** | **zakończony** | v3c POTWIERDZONE na n=59. S monotonicity ZŁAMANA (ρ=0.00). Krajobraz płaski. Zamknięta optymalizacja wag. | — |
| [[Pilot OSS\|Pilot-1]] | **Pilot Before/After refactoring** | **zakończony** | AGQ delta=+0.002 (szum). S=0.19 niezmienione. Blind spot (GREEN vs NEG) nierozwiązany. CI/CD działa. | — |
| [[Pilot Multi-Repo Scan\|Pilot-2]] | **Multi-repo scan (15 repos)** | **zakończony** | **KRYTYCZNE**: AGQ odwrócone — BAD repos (kolekcje) dostały wyższe AGQ niż GOOD repos (frameworki). 5/5 blind spots. "Efekt archipelagu." | — |

### Chronologia

```mermaid
timeline
    title Eksperymenty QSE — chronologia
    Turn 15-17 : E2 Coupling Density — odkrycie
    Turn 17-19 : E2 walidacja, oczyszczanie GT
    Turn 22-24 : E2 wdrożenie do AGQ v2
    Turn 28 : E1 Stability Hierarchy — obalony
    Turn 31 : E4 GT n=14 — AGQ v2 p=0.008
    Turn 35-36 : E5 NSdepth / NSgini
    Turn 39 : E6 flatscore — odkrycie dla Pythona
    Turn 38-41 : PCA weights — equal 0.20
    2026-04 : E7 P4 Java-S — v3c confirmed, S monotonicity broken
    2026-04 : Pilot-1 Before/After — delta +0.002 (szum), blind spot nierozwiązany
    2026-04 : Pilot-2 Multi-repo — AGQ odwrócone, efekt archipelagu
```

### Związki między eksperymentami

```mermaid
graph TD
    E2["E2: Coupling Density\n(edges/nodes)"] --> AGQv2["AGQ v2\n(CD z wagą 0.20)"]
    E1["E1: Stability Hierarchy\n(OBALONY)"] --> W7["W7: obalona"]
    E5["E5: NSdepth / NSgini"] --> AGQv3b["AGQ v3b (NSdepth zamiast A)"]
    E6["E6: flatscore"] --> AGQv3c["AGQ v3c Python\n(flat_score × 0.35)"]
    PCA["PCA Weights\n(equal 0.20)"] --> AGQv3a["AGQ v3a = v3c Java\n(równe wagi)"]
    E4["E4: GT panel n=14"] --> W4["W4: AGQv2 > AGQv1"]
    E7["E7: P4 Java-S\n(v3c CONFIRMED)"] --> v3cFinal["v3c Java ★\n(wagi zamrożone)"]
    PCA --> v3cFinal
    E4 --> v3cFinal
```

## Definicja formalna

Protokół falsyfikacji eksperymentów QSE:
- **Maksimum iteracji:** 5 per eksperyment
- **Kryterium stopu:** 2 kolejne iteracje bez poprawy partial r lub MW p-value
- **Wymagane minimum próby:** n≥10 (statystyki minimalne), n≥30 (wiarygodne wnioski)
- **GT:** panel ekspertów (σ<2.0), nie BLT (obalony jako GT — zob. [[W1 BLT Correlation]])
- **Testy:** Mann-Whitney U (separacja kategorii), Spearman partial (kontrola rozmiaru)

## Zobacz też

- [[How to Read Experiments]] — protokół badawczy QSE
- [[W1 BLT Correlation]] — dlaczego BLT jest złym GT
- [[W4 AGQv2 Beats AGQv1 on Java GT]] — główny wynik potwierdzony
- [[Hypotheses Register]] — powiązane hipotezy
- [[E7 P4 Java-S Expanded]] — najnowszy eksperyment
- [[Pilot OSS]] — pilotaż before/after refactoring
- [[Pilot Multi-Repo Scan]] — multi-repo scan (15 repos, krytyczne wyniki)
