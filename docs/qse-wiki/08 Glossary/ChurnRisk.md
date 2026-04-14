---
type: glossary
language: pl
---

# ChurnRisk

## Prostymi słowami

ChurnRisk to szacowane ryzyko procesowe projektu — na ile prawdopodobne jest, że zmiany w kodzie będą bolesne i prowadzą do regresji. Projekt z niską spójnością (klasy robią za dużo) i cyklami (zmiany się kaskadują) ma HIGH ChurnRisk — każda modyfikacja ryzykuje efekt domina.

## Szczegółowy opis

ChurnRisk jest jedną z pięciu metryk [[AGQ Enhanced]] (Warstwa 5). Łączy informacje z dwóch składowych AGQ:
- **C** ([[Cohesion]]) — spójność klas (LCOM4)
- **A** ([[Acyclicity]]) — brak cykli (Tarjan SCC)

### Logika klasyfikacji

| ChurnRisk | Warunek | Interpretacja |
|---|---|---|
| **LOW** | C ≥ 0.50 i A ≥ 0.95 | Klasy spójne, brak cykli — zmiany lokalne |
| **MEDIUM** | C < 0.50 lub A < 0.95 (nie oba) | Jedno ryzyko — lokalizowalne |
| **HIGH** | C < 0.50 i A < 0.95 | Klasy niespójne + cykle — zmiany kaskadują |

### Dlaczego C i A?

- **Niska C** = klasy robią wiele rzeczy → zmiana jednej odpowiedzialności dotyka wielu metod w tej samej klasie → wysoki churn
- **Niskie A** = cykliczne zależności → zmiana modułu X wymusza zmiany w modułach Y, Z, które zależą od X → efekt domina

Kombinacja obu to najgorszy scenariusz: zmiana jednej metody wymusza zmiany w wielu klasach, a te zmiany kaskadują przez cykle.

### Ograniczenia

ChurnRisk jest **heurystyką statyczną** — nie analizuje historii VCS (commitów, churn rate). Eksperymenty E11 wykazały, że behavioral metrics (commit churn, bug density) mają **słabą korelację z AGQ** (r ≈ 0.1–0.2 ns). ChurnRisk mierzy *potencjał* ryzykownych zmian, nie rzeczywistą historię.

## Definicja formalna

\[\text{ChurnRisk}(r) = g(C(r), A(r))\]

gdzie \(g\) jest deterministyczną funkcją progową opartą na wartościach Cohesion i Acyclicity.

## Zobacz też

- [[AGQ Enhanced]] — zestaw metryk rozszerzonych
- [[Cohesion]] — spójność klas (LCOM4)
- [[Acyclicity]] — brak cykli
- [[E11 Literature Approaches]] — behavioral metrics nie korelują z AGQ
- [[Fingerprint]] — wzorzec architektoniczny (pokrewna klasyfikacja)
