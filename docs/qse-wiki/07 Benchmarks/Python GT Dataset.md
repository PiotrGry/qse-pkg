---
type: benchmark-data
language: pl
---

# Python GT Dataset — Zbiór walidacyjny Python

> **Appendix** — surowe dane zbioru walidacyjnego Python GT. Uwaga: zbiór ma znany problem odwróconego kierunku — szczegóły poniżej.

## Parametry ogólne

| Parametr | Wartość |
|---|---|
| Plik źródłowy | `python_deepdive_results.json` |
| Łączna liczba repo | **30** |
| POS (dobra architektura) | **13** |
| NEG (słaba architektura) | **17** |
| Formuła AGQ | v3c Python-specific (z `flat_score`) |
| Status | ⚠️ Problem kierunku — badany |

---

## Formuła AGQ dla Pythona

Python używa zmodyfikowanej formuły z dodatkowym komponentem `flat_score`:

```
AGQ_v3c (Python) = 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score
```

Waga `flat_score` = 0.35 jest największą wagą — odzwierciedla empiryczne odkrycie, że projekty Python o płaskiej strukturze (jeden duży moduł) mają odmienne charakterystyki niż hierarchiczne projekty Java.

Definicja: [[flatscore|flat_score]]

---

## Problem odwróconego kierunku

W zbiorze Python GT zaobserwowano anomalię: metryki AGQ wykazują tendencję do **odwróconej** korelacji z oceną panelową w porównaniu z oczekiwaniami.

**Hipotezy wyjaśniające (trwa dochodzenie):**

1. **Specyfika ekosystemu Python** — projekty Python mają typowo płaską strukturę pakietów (jeden plik, jeden moduł), co sprawia, że metryki skalkulowane dla Java-like hierarchii nie przenoszą się bezpośrednio
2. **Selektywność próbki** — 30 repo Python GT może nie reprezentować dobrze różnorodności ekosystemu
3. **`flat_score` jako próba naprawy** — dodanie `flat_score` z wagą 0.35 jest właśnie odpowiedzią na ten problem, ale wymaga dalszej kalibracji na szerszym zbiorze
4. **Różne wzorce modularyzacji** — Python preferuje modularyzację przez pliki/moduły, a nie przez pakiety, co wpływa na obliczenie Stability (Martin's Stability)

**Aktualny stan:** Problem odnotowany jako ograniczenie (W9). Nie blokuje badań Java, ale wymaga osobnej kalibracji dla Pythona.

---

## Wyniki per repozytorium (podzbiór)

### Repozytoria POS (n=13)

| Repozytorium | AGQ v3c | Węzły | Stability | Cohesion | flat_score |
|---|---:|---:|---:|---:|---:|
| attrs | 1.0000 | 10 | 1.000 | 1.000 | — |
| pytest | 0.8750 | 2 | 1.000 | 1.000 | — |
| prefect | 0.8503 | 1251 | 0.982 | 0.729 | — |
| sphinx | 0.8040 | 500 | 0.981 | 0.680 | — |
| django | 0.7883 | 1229 | 0.973 | 0.679 | — |
| fastapi | 0.7633 | 145 | 0.837 | 0.788 | — |
| scikit-learn | 0.7793 | 1176 | 0.816 | 0.704 | — |

### Repozytoria NEG (n=17, podzbiór)

| Repozytorium | AGQ v3c | Węzły | Stability | Cohesion | Uwagi |
|---|---:|---:|---:|---:|---|
| flask | 0.7146 | 79 | 0.737 | 0.578 | Niska S — brak hierarchii |
| click | 0.7254 | 59 | 0.764 | 0.685 | Utility library |
| home-assistant | 0.5807 | 17595 | 0.078 | 0.711 | Bardzo niska S — monolith |
| airflow | 0.6995 | 8017 | 0.464 | 0.605 | Złożona struktura |
| ansible | 0.6103 | 2155 | 0.223 | 0.691 | Plug-in heavy |

---

## Metryki statystyczne per komponent (Python GT)

| Komponent | POS mean | NEG mean | Δ | Kierunek |
|---|---:|---:|---:|---|
| Acyclicity (A) | ~1.000 | ~0.999 | ~0.001 | Prawidłowy, ale brak różnicowania |
| Modularity (M) | ~0.52 | ~0.53 | −0.01 | ⚠️ Odwrócony |
| Stability (S) | wyższy | niższy | + | Prawidłowy |
| Cohesion (C) | wyższy | niższy | + | Prawidłowy |
| flat_score | niższy | wyższy | − | ⚠️ Projekt Pythona = płaski = NEG |

**Uwaga:** Acyclicity w zbiorze Python jest bliskie 1.000 dla prawie wszystkich projektów — brak cykli jest normą w Python OSS, więc metryka nie różnicuje.

---

## Kalibracja na OSS-Python (n=74)

Do kalibracji wag AGQ v3c Python użyto szerszego zbioru 74 (lub 80) repozytoriów Python (OSS-30 to podzbiór). Wyniki kalibracji:

| Metoda | Wagi M/A/S/C/CD/flat |
|---|---|
| PCA (równe wagi) | 0.20/0.20/0.20/0.20/0.20/0 |
| Optymalizacja Python-specific | 0.15/0.05/0.20/0.10/0.15/0.35 |

PCA wykazała, że wszystkie 5 eigenvalues są zbliżone — brak dominującego wymiaru. Dodanie `flat_score` jest heurystyką bazującą na obserwacji empirycznej, nie na wyniku PCA.

---

## Znane ograniczenia

- n=30 to zbyt mała próba do silnych wniosków statystycznych
- Problem odwróconego kierunku dla Modularity nie jest wyjaśniony
- Brak walidacji na projektach przemysłowych (closed-source Python)
- Formuła z `flat_score=0.35` nie przeszła jeszcze cross-walidacji na niezależnym zbiorze

---

## Planowane działania

1. **Rozszerzenie Python GT** do n≥50 (analogicznie jak Java GT)
2. **Badanie Modularity** — dlaczego M zachowuje się odwrotnie w Python?
3. **Cross-validation** formuły Python-specific
4. **Category-aware normalization** — normalizacja względem kategorii (library vs application)

---

## Zobacz też

- [[Benchmark Index]] — przegląd wszystkich zbiorów
- [[Java GT Dataset]] — dobrze skalibrowany zbiór Java
- [[flatscore|flat_score]] — komponent specyficzny dla Pythona
- [[GT]] — metodologia ground truth
- [[W9 AGQv3c Python Discriminates Quality|W9]] — hipoteza Python GT
- [[Limitations|Ograniczenia]] — pełna lista known limitations
