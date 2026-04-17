---
type: glossary
language: pl
---

# AGQ Enhanced

## Prostymi słowami

AGQ Enhanced to zestaw metryk rozszerzonych, które nadają kontekst surowemu wynikowi AGQ. Zamiast jednej liczby (np. 0.57) dostajesz: pozycję na tle języka (AGQ-z), wzorzec architektoniczny ([[Fingerprint]]), powagę cykli ([[CycleSeverity]]), ryzyko procesowe ([[ChurnRisk]]) i wynik skorygowany o rozmiar (AGQ-adj). To Warstwa 5 w architekturze QSE — „interpretacja" surowych liczb z Warstwy 2.

## Szczegółowy opis

AGQ Enhanced to **Warstwa 5** w [[Architecture|architekturze QSE]]. Nie dodaje nowych skanowań kodu — oblicza się wyłącznie na podstawie wyników z Warstwy 2 (AGQ Core) i danych benchmarkowych (558 repozytoriów, zob. [[Benchmark 558]]).

### Pięć metryk rozszerzonych

| Metryka | Co mówi | Wejścia | Przykład |
|---|---|---|---|
| **AGQ-z** | Pozycja na tle języka (z-score) | AGQ + benchmark stats per lang | `kubernetes`: AGQ-z = −2.58 → 0.5%ile Go |
| **[[Fingerprint]]** | Wzorzec architektoniczny | M, A, S, C, CD + progi | CLEAN / LAYERED / FLAT / TANGLED / CYCLIC / LOW_COHESION / MODERATE |
| **[[CycleSeverity]]** | Powaga cyklicznych zależności | A, largest_scc | NONE / LOW / MEDIUM / HIGH / CRITICAL |
| **[[ChurnRisk]]** | Szacowane ryzyko procesowe | C, A | LOW / MEDIUM / HIGH |
| **AGQ-adj** | Wynik skorygowany o rozmiar | AGQ, nodes | Kalibracja do 500 węzłów jako baseline |

### AGQ-z (Z-score normalizacja)

AGQ-z normalizuje surowe AGQ względem mediany i odchylenia standardowego dla danego języka:

\[\text{AGQ-z} = \frac{\text{AGQ} - \mu_{\text{lang}}}{\sigma_{\text{lang}}}\]

**Dlaczego to ważne:** Surowe AGQ nie jest porównywalne między językami. Go ma strukturalnie wyższe AGQ (mean=0.783) niż Java (mean=0.627), bo Go wymusza brak cykli i ma prostszą hierarchię pakietów. AGQ-z eliminuje ten efekt.

**Parametry benchmarkowe (z Benchmark 558, iter6):**

| Język | n | μ (mean AGQ) | σ (std dev) | Mediana |
|---|---|---|---|---|
| Go | 30 | 0.783 | 0.087 | 0.795 |
| Python | 351 | 0.748 | 0.114 | 0.762 |
| Java | 147 | 0.627 | 0.122 | 0.631 |
| TypeScript | 8 | 0.604 | 0.185 | 0.618 |

**Przykłady interpretacji AGQ-z:**

| Repo | Język | AGQ | AGQ-z | Percentyl | Interpretacja |
|---|---|---|---|---|---|
| kubernetes | Go | 0.558 | −2.58 | 0.5% | Gorszy niż 99.5% projektów Go (ale Go to wysoka poprzeczka) |
| django | Python | 0.781 | +0.29 | 61% | Lekko powyżej mediany Pythona |
| spring-boot | Java | 0.574 | −0.43 | 33% | Poniżej mediany Javy — zaskakujące dla spring-boot |
| mall | Java | 0.493 | −1.09 | 14% | Dolny kwartyl Javy — spójne z oceną NEG |

### AGQ-adj (korekta rozmiaru)

Małe projekty (< 50 węzłów) mają strukturalnie zawyżone AGQ:
- Trywialnie brak cykli w 10 plikach → A = 1.0
- Mała gęstość krawędzi → CD wysoki
- Louvain na małym grafie → M zawyżone

AGQ-adj kalibruje wynik do 500 węzłów jako baseline. Korekta jest logarytmiczna:

\[\text{AGQ-adj} = \text{AGQ} - \beta \cdot \log\left(\frac{500}{\max(\text{nodes}, 10)}\right)\]

gdzie β jest kalibrowane na benchmarku. Projekty z nodes > 500 nie są korygowane (korekta = 0).

**Ograniczenie:** AGQ-adj nie został walidowany na GT — istnieje korelacja r=+0.236 z hotspot_ratio, ale to słaby sygnał. W obecnej formie AGQ-adj jest eksperymentalny.

### Kiedy używać Enhanced vs surowe AGQ?

| Scenariusz | Użyj | Dlaczego |
|---|---|---|
| Porównanie projektów w tym samym języku | surowe AGQ | Bezpośrednio porównywalne |
| Porównanie Java vs Python | **AGQ-z** | Normalizacja per język |
| Diagnoza problemu architektonicznego | **Fingerprint + CycleSeverity** | Mówi *jaki* problem, nie tylko *ile* |
| Ocena ryzyka przed refaktoryzacją | **ChurnRisk** | Kombinacja spójności i cykli |
| Małe projekty (< 100 nodes) | **AGQ-adj** | Korekta na rozmiar |
| CI/CD quality gate | surowe AGQ + próg | Deterministyczne PASS/FAIL |

### Implementacja

AGQ Enhanced jest obliczane w `qse/graph_metrics.py`, metoda `compute_enhanced_metrics()`. Wymaga benchmarku jako inputu (plik `artifacts/benchmark_iter6.json`).

```python
from qse.graph_metrics import compute_agq, compute_enhanced_metrics

metrics = compute_agq(graph, abstract_modules, lcom4_values, weights=(0.20, 0.20, 0.20, 0.20))
enhanced = compute_enhanced_metrics(metrics, language="java", benchmark_stats=benchmark)
# enhanced.agq_z, enhanced.fingerprint, enhanced.cycle_severity, enhanced.churn_risk, enhanced.agq_adj
```

## Definicja formalna

AGQ Enhanced = {AGQ-z, Fingerprint, CycleSeverity, ChurnRisk, AGQ-adj} obliczane na wyjściu Warstwy 2 bez dodatkowych skanowań.

\[\text{Enhanced}(r) = \{f_1(\text{AGQ}(r), \mu_\text{lang}, \sigma_\text{lang}), \; f_2(M, A, S, C, CD), \; f_3(A, \text{scc}), \; f_4(C, A), \; f_5(\text{AGQ}(r), n)\}\]

Każda \(f_i\) jest deterministyczna i nie wymaga dodatkowego skanowania kodu.

**Niezmiennik:** Warstwa 5 nie modyfikuje wyników warstw niższych. AGQ i składowe (M, A, S, C, CD) pozostają identyczne — Enhanced tylko dodaje interpretację.

## Ograniczenia

1. **Benchmark dependency** — AGQ-z i AGQ-adj zależą od jakości benchmarku. Benchmark 558 jest zdominowany przez Python (351/558 = 63%) — statystyki dla Go (n=30) i TypeScript (n=8) są niereprezentatywne.
2. **AGQ-adj nie walidowane** — korelacja z jakością jest słaba (r=0.236), eksperymentalny status.
3. **Fingerprint progi arbitralne** — oparte na analizie rozkładów benchmarku, nie na Ground Truth. Mogą wymagać kalibracji.
4. **ChurnRisk to heurystyka** — nie analizuje historii VCS. Mierzy potencjał ryzyka, nie rzeczywisty churn (zob. [[E11 Literature Approaches]] — behavioral metrics słabe).

## Zobacz też

- [[Architecture]] — architektura 5-warstwowa QSE
- [[AGQ Formulas]] — wzory AGQ (Warstwa 2)
- [[Fingerprint]] — 7 wzorców architektonicznych
- [[CycleSeverity]] — klasyfikacja powagi cykli
- [[ChurnRisk]] — heurystyka ryzyka procesowego
- [[Benchmark 558]] — dane benchmarkowe do normalizacji
- [[E13 Three-Layer Framework]] — kontekst Layer 1/2/3
