---
type: glossary
language: pl
---

# ChurnRisk

## Prostymi słowami

ChurnRisk to szacowane ryzyko procesowe projektu — na ile prawdopodobne jest, że zmiany w kodzie będą bolesne i prowadzą do regresji. Projekt z niską spójnością (klasy robią za dużo) i cyklami (zmiany się kaskadują) ma HIGH ChurnRisk — każda modyfikacja ryzykuje efekt domina. To jak sygnalizacja drogowa na skrzyżowaniu: zielone = zmieniaj spokojnie, czerwone = uważaj, bo zmiana w jednym miejscu pociągnie za sobą kaskadę.

## Szczegółowy opis

ChurnRisk jest jedną z pięciu metryk [[AGQ Enhanced]] (Warstwa 5). Łączy informacje z dwóch składowych AGQ:
- **C** ([[Cohesion]]) — spójność klas (LCOM4): niskie C = klasy robią wiele rzeczy
- **A** ([[Acyclicity]]) — brak cykli (Tarjan SCC): niskie A = zmiany kaskadują

### Logika klasyfikacji

| ChurnRisk | Warunek | Interpretacja | Typowy scenariusz |
|---|---|---|---|
| **LOW** | C ≥ 0.50 i A ≥ 0.95 | Klasy spójne, brak cykli — zmiany lokalne | DDD projects, dobrze utrzymane biblioteki |
| **MEDIUM** | C < 0.50 lub A < 0.95 (nie oba) | Jedno ryzyko — lokalizowalne | Spring Boot (C ok, lekkie cykle) lub YouTube-dl (brak cykli, ale niska C) |
| **HIGH** | C < 0.50 i A < 0.95 | Klasy niespójne + cykle — zmiany kaskadują | Legacy monolity Java, typowe enterprise CRUDs |

### Dlaczego akurat C i A?

**Niska C** (Cohesion < 0.50) oznacza klasy z wieloma odpowiedzialnościami:
- Klasa `OrderService` obsługuje zamówienia, płatności, powiadomienia i logowanie → zmiana logiki płatności dotyka metod logowania (bo współdzielą pola)
- LCOM4 mierzy to formalnie: ile „wysp" metod w jednej klasie (zob. [[LCOM4]])
- Efekt: każda zmiana dotyka wielu metod w tej samej klasie → wysoki churn na plikach

**Niskie A** (Acyclicity < 0.95) oznacza cykliczne zależności:
- Moduł `orders` importuje `payments`, a `payments` importuje `orders` → zmiana w jednym wymusza zmiany w drugim
- Efekt domina: zmiana w A → zmiana w B → zmiana w C → potencjalnie z powrotem w A
- Efekt: każda zmiana rozlewa się na wiele plików → wysoki churn na commitach

**Kombinacja obu to najgorszy scenariusz:** zmiana jednej metody wymusza zmiany w wielu metodach tej samej klasy (niskie C) I rozlewa się na inne moduły przez cykle (niskie A).

### Przykłady z GT i pilotów

| Repo | Panel | C | A | ChurnRisk | Komentarz |
|---|---|---|---|---|---|
| ddd-by-examples/library | 8.50 | 0.72 | 1.00 | **LOW** | Wzorcowe DDD — spójne klasy, zero cykli |
| spring-boot | 7.25 | 0.38 | 0.98 | **MEDIUM** | Nieco niskie C, ale cykle minimalne |
| shopizer (before) | 4.00 | 0.41 | 0.95 | **MEDIUM** | C ok-ish, cykle LOW → MEDIUM |
| shopizer (after E13e) | 4.80 | 0.41 | 1.00 | **LOW** | Naprawione cykle → spadek ryzyka |
| mall | 2.00 | 0.15 | 0.93 | **HIGH** | God classes + cykle = koszmar |
| newbee-mall (before) | 2.50 | 0.29 | 1.00 | **MEDIUM** | Niska C, ale brak cykli |
| newbee-mall (after E13g) | ~4.2 | 0.36 | 1.00 | **MEDIUM** | Lekka poprawa C, nadal < 0.50 |

### Relacja z behavioral metrics

ChurnRisk jest **heurystyką statyczną** — mierzy *potencjał* ryzykownych zmian, nie rzeczywistą historię commitów. Czy to wystarczy?

Eksperymenty E11 przetestowały korelację AGQ z behavioral metrics (churn rate, bug density, commit frequency):
- Churn rate vs AGQ: r ≈ 0.1–0.2 **ns** (nieistotne)
- Bug density vs AGQ: r ≈ 0.15 **ns**

**Wniosek:** metryki procesowe (z VCS) słabo korelują z metrykami strukturalnymi (z kodu). To nie znaczy, że struktura nie wpływa na churn — ale wpływ jest mediowany przez inne czynniki (rozmiar zespołu, praktyki CI, coverage testów). ChurnRisk mierzy potencjał strukturalny, nie procesowy.

Dla porównania: [[References|CodeScene]] (komercyjne narzędzie) analizuje historię VCS i daje komplementarny widok — procesowy zamiast strukturalnego. QSE i CodeScene mierzą różne wymiary tego samego problemu.

### Rozkład ChurnRisk w benchmarku

Z 558 repozytoriów:
- **LOW:** ~45% (głównie Go i Python — niski odsetek cykli, wyższa spójność)
- **MEDIUM:** ~40% (większość Java)
- **HIGH:** ~15% (legacy Java, duże monolity)

**Per język:**
- **Go:** 90%+ LOW (Go wymusza brak cykli, spójne pakiety)
- **Python:** 75% LOW (Python ma naturalne warstwy)
- **Java:** 30% LOW, 45% MEDIUM, 25% HIGH (Java ma najgorszy profil ryzyka)

## Definicja formalna

\[\text{ChurnRisk}(r) = g(C(r), A(r))\]

\[\text{ChurnRisk}(r) = \begin{cases}
\text{LOW} & \text{jeśli } C(r) \geq 0.50 \text{ i } A(r) \geq 0.95 \\
\text{HIGH} & \text{jeśli } C(r) < 0.50 \text{ i } A(r) < 0.95 \\
\text{MEDIUM} & \text{wpp.}
\end{cases}\]

## Ograniczenia

1. **Tylko dwa wymiary** — ChurnRisk ignoruje M (Modularity), S (Stability), CD (Coupling Density). Projekt z doskonałą C i A ale z CD=0 (archipelag) może mieć inne problemy.
2. **Progi binarne** — C=0.49 → HIGH, C=0.51 → MEDIUM. Brak gradientu w okolicy progu.
3. **Nie uwzględnia rozmiaru** — mały projekt (20 klas) z HIGH ChurnRisk to inny problem niż duży (2000 klas) z HIGH ChurnRisk.
4. **Nie walidowane na GT** — ChurnRisk nie był testowany przeciwko rzeczywistym danym churnowym. E11 wykazał słabą korelację behavioral ↔ structural, ale to dotyczyło surowego AGQ, nie ChurnRisk specyficznie.

## Zobacz też

- [[AGQ Enhanced]] — zestaw metryk rozszerzonych
- [[Cohesion]] — spójność klas (LCOM4)
- [[Acyclicity]] — brak cykli
- [[CycleSeverity]] — bardziej granularna ocena cykli (5 poziomów)
- [[Fingerprint]] — wzorzec architektoniczny (pokrewna klasyfikacja)
- [[E11 Literature Approaches]] — behavioral metrics nie korelują z AGQ
- [[E13e Shopizer Pilot]] — naprawienie cykli obniża ChurnRisk
