---
type: glossary
language: pl
---

# Fingerprint

## Prostymi słowami

Fingerprint to etykieta opisująca „wzorzec architektoniczny" projektu — jedna z siedmiu kategorii. Zamiast jednej liczby AGQ, Fingerprint mówi *jaki typ* architektury ma projekt: czy jest czysty jak podręcznik (CLEAN), warstwowy (LAYERED), płaski bez struktury (FLAT), czy poplątany z cyklami (TANGLED).

## Szczegółowy opis

Fingerprint jest obliczany na podstawie surowych składowych AGQ (M, A, S, C, CD) i benchmarku 558 repo. Algorytm klasyfikuje projekt na podstawie progów per komponent.

### Siedem wzorców

| Wzorzec | Charakterystyka | Typowe dla |
|---|---|---|
| **CLEAN** | Brak cykli, wysoka spójność, wyraźne warstwy | Go (47/51) |
| **LAYERED** | Wyraźna hierarchia, ewentualne drobne cykle | Python (57/68) |
| **LOW_COHESION** | Klasy robią za dużo (niskie C) | Java (40/44) |
| **MODERATE** | Brak wyraźnych patologii | Wszystkie języki |
| **FLAT** | Brak hierarchii warstw (niskie S) | Duże projekty platformowe |
| **TANGLED** | Cykle + niska spójność | Java (9/9) |
| **CYCLIC** | Cykle bez innych problemów | Java (5/5) |

### Rozkład w Benchmarku 558

```
LAYERED       ████████████████████  68 (28%)
CLEAN         ███████████████       51 (21%)
LOW_COHESION  █████████████         44 (18%)
MODERATE      ████████████          40 (16%)
FLAT          ███████               23 (10%)
TANGLED       ███                    9  (4%)
CYCLIC        ██                     5  (2%)
(reszta: nodes=0)
```

### Algorytm klasyfikacji

Fingerprint jest deterministyczny — oparty na progach, nie na modelu ML:

1. A < 0.90 → **CYCLIC** lub **TANGLED** (zależy od C)
2. C < 0.30 → **LOW_COHESION**
3. S < 0.10 → **FLAT**
4. Wszystkie metryki powyżej mediany → **CLEAN**
5. Warstwowa struktura bez patologii → **LAYERED**
6. Pozostałe → **MODERATE**

## Definicja formalna

\[\text{Fingerprint}(r) \in \{\text{CLEAN}, \text{LAYERED}, \text{LOW\_COHESION}, \text{MODERATE}, \text{FLAT}, \text{TANGLED}, \text{CYCLIC}\}\]

Funkcja klasyfikująca jest deterministyczna i zależy wyłącznie od wartości M, A, S, C, CD repozytorium \(r\).

## Zobacz też

- [[AGQ Enhanced]] — zestaw metryk rozszerzonych (Warstwa 5)
- [[Architecture]] — architektura systemu QSE
- [[Benchmark 558]] — dane benchmarkowe
- [[Repository Types]] — typologia repozytoriów
