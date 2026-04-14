---
type: glossary
language: pl
---

# CycleSeverity

## Prostymi słowami

CycleSeverity mówi jak poważne są cykliczne zależności w projekcie — od NONE (brak cykli, ideał) przez LOW (drobne cykle, do naprawy) aż do CRITICAL (duży procent kodu w jednym gigantycznym cyklu, wymagający pilnej interwencji).

## Szczegółowy opis

CycleSeverity jest jedną z pięciu metryk [[AGQ Enhanced]] (Warstwa 5). Opiera się na dwóch wartościach z Warstwy 2:
- **A** ([[Acyclicity]]) — odsetek modułów NIE będących w cyklach
- **largest_scc** — rozmiar największego silnie spójnego składnika (algorytm [[Tarjan SCC]])

### Progi klasyfikacji

| Poziom | Warunek | Interpretacja |
|---|---|---|
| **NONE** | A = 1.0 (largest_scc ≤ 1) | Brak cykli — graf jest DAG |
| **LOW** | A ≥ 0.95 | Drobne cykle (< 5% modułów) |
| **MEDIUM** | A ≥ 0.85 | Umiarkowane cykle (5–15% modułów) |
| **HIGH** | A ≥ 0.70 | Poważne cykle (15–30% modułów) |
| **CRITICAL** | A < 0.70 | Dominujący cykl (> 30% modułów w jednym SCC) |

### Przykłady z benchmarku

| Repo | A | largest_scc | CycleSeverity |
|---|---|---|---|
| guava | 1.000 | 0 | NONE |
| spring-boot | 0.982 | 12 | LOW |
| shopizer (before) | 0.950 | 17 | LOW |
| shopizer (after E13e) | 1.000 | 0 | NONE |
| commons-collections (before) | 0.110 | 16 | CRITICAL |
| commons-collections (after E13f) | 1.000 | 0 | NONE |

### Relacja z QSE-Track

QSE-Track używa **largest_scc** jako jednej z trzech metryk śledzenia zmian. CycleSeverity jest pochodną tych samych danych, ale w formacie czytelnym dla człowieka.

## Definicja formalna

\[\text{CycleSeverity}(r) = f(A(r), \text{largest\_scc}(r))\]

gdzie \(f\) jest deterministyczną funkcją progową.

## Zobacz też

- [[AGQ Enhanced]] — zestaw metryk rozszerzonych
- [[Acyclicity]] — składowa AGQ (binarna: DAG vs cykl)
- [[Tarjan SCC]] — algorytm wykrywania cykli
- [[E13e Shopizer Pilot]] — refaktoryzacja SCC 17→0
- [[E13f Commons Collections Pilot]] — refaktoryzacja SCC 16→0
