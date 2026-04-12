---
type: metric
language: pl
---

# NSgini (Namespace Gini)

## Prostymi słowami

NSgini mierzy "nierówność" w rozkładzie klas między namespace'ami. Jeśli jeden namespace ma 200 klas, a reszta po 2 — duża nierówność (gini≈0.9). Jeśli wszystkie namespace'y mają podobną liczbę klas — mała nierówność (gini≈0.2). Intuicja: zbalansowane namespace'y to dobry znak. Jedna "ścisk" z setkami klas to god-module.

## Szczegółowy opis

### Współczynnik Giniego

NSgini używa klasycznego **współczynnika Gini** (z ekonomii: miara nierówności dochodów), ale stosowanego do rozkładu klas między namespace'ami:

- Gini = 0: idealna równość — każdy namespace ma tę samą liczbę klas
- Gini = 1: maksymalna nierówność — jeden namespace ma wszystkie klasy

```
NSgini = Gini(rozkład_klas_per_namespace)
```

### Dane empiryczne (sesja Turn 36)

**Wynik eksperymentu E5:**

| Język | Δ POS-NEG | Sygnał | p |
|---|---|---|---|
| Java | −0.073 | ns | ns |
| Python | 0.000 | ns | ns |
| ALL | — | ns | ns |

**NSgini nie wnosi sygnału w żadnym języku.** Współczynnik Gini mierzy nierówność rozkładu klas, co **nie koreluje z jakością architektury**.

### Dlaczego NSgini nie działa?

Nierówność rozkładu nie jest per se dobra ani zła:
- Mały projekt domenowy: 1 namespace z 15 klasami domenowymi → wysoki Gini, ale dobra architektura
- Duży projekt flat: 1000 klas w jednym namespace → wysoki Gini, zła architektura
- Projekt modularny: 10 namespace'ów × 5 klas → niski Gini, dobra architektura
- Projekt z god-module: 1 moduł × 500 klas + 100 × 2 klasy → wysoki Gini, zła architektura

Gini nie odróżnia "mały specjalistyczny namespace" od "god-module". Dlatego jest nieinformatywny.

### Przykłady z GT Java (ns_metrics_gt_v1.json)

| Repo | Panel | NSgini | Kategoria |
|---|---|---|---|
| spring-projects/spring-security | 6.50 | 0.610 | POS |
| apache/struts | 2.50 | 0.535 | NEG |
| citerus/dddsample-core | 8.25 | 0.383 | POS |
| macrozheng/mall | 2.00 | 0.741 | NEG |

Brak wyraźnego wzorca — POS ma zarówno niskie (0.383) jak i wysokie (0.610) gini.

### NSgini jako metryka informacyjna

Mimo braku wartości predykcyjnej NSgini jest użyteczna jako metryka **diagnostyczna**:
- NSgini > 0.8 może sygnalizować god-module (jeden namespace z nieproporcjonalnie dużą liczbą klas)
- W połączeniu z nscount (liczba namespace'ów) można budować bardziej złożone heurystyki

### Status w projekcie

NSgini jest obliczana przez QSE ale **nie wchodzi do formuły AGQ** (żadna wersja). Jest dostępna w wynikach jako metryka uzupełniająca dla celów diagnostycznych.

## Definicja formalna

Dla projektu z namespace'ami \(\{ns_1, \ldots, ns_k\}\) i liczbami klas \(\{n_1, \ldots, n_k\}\):

\[\text{NSgini} = \frac{\sum_{i} \sum_{j} |n_i - n_j|}{2k \sum_{i} n_i}\]

Równoważnie (wersja uproszczona):
\[\text{NSgini} = 1 - \frac{\sum_{i} (2i - k - 1) \cdot n_{\sigma(i)}}{k \sum_{i} n_i}\]

Gdzie \(n_{\sigma(i)}\) = posortowane rosnąco wartości \(n_i\).

**Zakres:** [0, 1], gdzie 0 = idealna równość, 1 = maksymalna nierówność.

**Walidacja statystyczna** (sesja Turn 36, n=14+14):
- Java: p = ns
- Python: p = ns
- Wniosek: **nie używać do klasyfikacji**

## Zobacz też

- [[NSdepth]] — komplementarna metryka (działa dla Javy)
- [[flatscore]] — metryka dla Pythona
- [[nodes]] — liczba węzłów
- [[E5 Namespace Metrics]] — eksperyment gdzie NSgini okazała się nieinformatywna
