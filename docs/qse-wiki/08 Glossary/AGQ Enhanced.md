---
type: glossary
language: pl
---

# AGQ Enhanced

## Prostymi słowami

AGQ Enhanced to zestaw metryk rozszerzonych, które nadają kontekst surowemu wynikowi AGQ. Zamiast jednej liczby (np. 0.57) dostajesz: pozycję na tle języka (AGQ-z), wzorzec architektoniczny ([[Fingerprint]]), powagę cykli ([[CycleSeverity]]), ryzyko procesowe ([[ChurnRisk]]) i wynik skorygowany o rozmiar (AGQ-adj).

## Szczegółowy opis

AGQ Enhanced to **Warstwa 5** w [[Architecture|architekturze QSE]]. Nie dodaje nowych skanowań — oblicza się wyłącznie na podstawie wyników z Warstwy 2 (AGQ Core) i danych benchmarkowych.

### Pięć metryk rozszerzonych

| Metryka | Co mówi | Przykład |
|---|---|---|
| **AGQ-z** | Pozycja na tle języka (z-score) | `kubernetes`: AGQ-z = −2.58 → 0.5%ile Go |
| **[[Fingerprint]]** | Wzorzec architektoniczny | CLEAN / LAYERED / FLAT / TANGLED / CYCLIC / LOW_COHESION / MODERATE |
| **[[CycleSeverity]]** | Powaga cyklicznych zależności | NONE / LOW / MEDIUM / HIGH / CRITICAL |
| **[[ChurnRisk]]** | Szacowane ryzyko procesowe | HIGH gdy niska spójność + cykle |
| **AGQ-adj** | Wynik skorygowany o rozmiar | Kalibracja do 500 węzłów jako baseline |

### AGQ-z (Z-score normalizacja)

AGQ-z normalizuje surowe AGQ względem mediany i odchylenia standardowego dla danego języka:

\[\text{AGQ-z} = \frac{\text{AGQ} - \mu_{\text{lang}}}{\sigma_{\text{lang}}}\]

Pozwala porównywać projekty między językami: AGQ=0.55 (Java) ≈ AGQ=0.75 (Go) po normalizacji.

### AGQ-adj (korekta rozmiaru)

Małe projekty (< 50 węzłów) mają strukturalnie zawyżone AGQ — trywialnie brak cykli w 10 plikach. AGQ-adj kalibruje wynik do 500 węzłów jako baseline.

## Definicja formalna

AGQ Enhanced = {AGQ-z, Fingerprint, CycleSeverity, ChurnRisk, AGQ-adj} obliczane na wyjściu Warstwy 2 bez dodatkowych skanowań.

**Niezmiennik:** Warstwa 5 nie modyfikuje wyników warstw niższych.

## Zobacz też

- [[Architecture]] — architektura 5-warstwowa QSE
- [[AGQ Formulas]] — wzory AGQ (Warstwa 2)
- [[Fingerprint]] — wzorce architektoniczne
- [[CycleSeverity]] — powaga cykli
- [[ChurnRisk]] — ryzyko procesowe
- [[Benchmark 558]] — dane benchmarkowe do normalizacji
