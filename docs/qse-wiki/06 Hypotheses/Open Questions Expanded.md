---
type: meta
language: pl
---

# Otwarte Pytania Badawcze — Rozszerzony Widok

## Prostymi słowami

Nauka nie kończy się na znalezieniu odpowiedzi — kończy się na wyraźnym sformułowaniu pytań, które zostały. Ten dokument kataloguje pytania które QSE postawiło ale nie odpowiedziało. Każde pytanie to potencjalny przyszły eksperyment.

## Kategorie pytań otwartych

### I. Walidacja cross-językowa

#### Q1: Czy formuła Java działa dla Go i TypeScript?

AGQ v3c Java (equal 0.20 weights) był kalibrowany wyłącznie na projektach Java. Benchmark zawiera ~30 Go i TypeScript repo — ale bez GT panelu.

```
Stan: benchmark dostępny, GT brak
Blokada: brak panelu ekspertów Go/TypeScript
Szacowany koszt: 2–3 dni (panel + skan)
Powiązana hipoteza: O1
```

**Dlaczego Go może działać:** statyczne typowanie + konwencja pakietów podobna do Javy.
**Dlaczego TypeScript może nie działać:** 73% TypeScript repo w benchmarku ma nodes=0 (problem z parserem). TypeScript ma też monorepo (np. wszystko w `src/`) podobne do Python flat pattern.

#### Q2: Czy język = formuła?

Obecna hipoteza: Java i Python potrzebują innych formuł. Go może być bliższe Javie. TypeScript bliższe Pythonowi. Ale to spekulacja bez danych.

Formalne pytanie: czy AGQ potrzebuje N formuł per język, czy istnieje jedna formuła z parametrem językowym?

---

### II. Metryki per język

#### Q3: Co mierzy CD dla Pythona? (→ O5)

Mechanizm znany: flat spaghetti = niski ratio = fałszywy sygnał dobrej architektury. Ale czy to jedyna przyczyna? Czy istnieje zła architektura Python z WYSOKIM ratio?

```
Blokada: za mało NEG Python w GT (n_neg=6)
Potrzeba: n_neg_Python ≥ 15, sklasyfikowane jako flat vs tangled
```

#### Q4: Jakie metryki Python uzupełniłyby flat_score?

flat_score (depth>2) wykrywa flat spaghetti. Co wykrywa:
- Bogate importy bez struktury?
- Brak interfejsów / protokołów?
- God modules (jeden plik = 5000 linii)?

```
Kandydaci: __init__.py density, import depth, god_module_ratio
Powiązana hipoteza: O4
```

#### Q5: Czy god_class_ratio działa dla Pythona?

Z sesji (Turn 7): surowy Spearman(gcr, panel) = −0.379, p=0.039. Ale nie przeżywa size control (partial r=−0.323, p=0.087). Nie oddziela kategorii. **Nie gotowy do formuły** — ale może w kombinacji z flat_score?

```
Stan: wstępny test negatywny
Blokada: nie przeżywa partial control
Potrzeba: sprawdzić na większym n
```

---

### III. Semantyka kodu vs topologia grafu

#### Q6: Jak odróżnić DDD domain od anemic domain bez semantyki?

Problem E1: mall.domain (instability≈0, puste POJO) wygląda identycznie jak library.domain (instability=0.464, rich domain) dla S_hierarchy. Jedyna różnica jest semantyczna (czy metody mają logikę).

```
Aktualnie niemożliwe bez: parsowania body metod
Możliwe przez: tree-sitter heurystyki (długość metod, liczba linii)
Koszt: wysoki (modyfikacja parsera Rust)
```

#### Q7: Czy metryki heurystyczne (długość metody, liczba pól) dają sygnał?

Proxy semantyki bez pełnego parsowania:
- `mean_method_length` per klasa: długie metody → logika biznesowa
- `fields_per_class`: dużo pól = data object (POJO)
- `annotation_density`: @Entity, @Getter, @Service → DDD vs CRUD

Żadne z tych nie jest w QSE. Wszystkie wymagają modyfikacji Rust parsera.

---

### IV. Wolna przestrzeń — nowe wymiary

#### Q8: Czy AGQ mierzy jakość testów?

Obecne QSE: `QSE_test` (metryki testów istnieją, ale oddzielne od AGQ). Hipoteza: projekt z dobrą architekturą ma też lepsze testy (test coverage, brak test smells).

```
Częściowa odpowiedź: cohesion↔complexity/KLOC r=−0.28 (p=0.01) — pozytywny sygnał
Brak bezpośredniej korelacji AGQ↔coverage
Powiązanie: QSE_test jako osobna metryka (nie do AGQ)
```

#### Q9: Czy AGQ przewiduje przyszłą jakość (dAGQ/dt)?

W8 obalony na Jolak: dAGQ/dt nie predykuje zmian jakości. Ale 533 snapshots to jeden projekt. Czy istnieje wzorzec degradacji AGQ który poprzedza problemy?

```
Stan: W8 obalona na Jolak (n=1 projekt)
Pytanie: czy seria projektów z longitudinalnym GT dałaby inny wynik?
```

#### Q10: Metryki przepływu danych (DataFlow coupling)

Obecny graf QSE: importy i wywołania klas. Co z przepływem danych? Klasy które wymieniają dane (przez pola, przez parametry) mogą być silniej sprzężone niż sugeruje statyczny import graph.

```
Aktualnie niemożliwe bez: analizy dynamicznej lub głębszego parsowania
Koszt: bardzo wysoki
```

---

### V. Walidacja i GT

#### Q11: Jak zebrać GT dla większej próby (n≥100)?

Obecne GT: panel 3 ekspertów, σ<2.0, n=14 Java + n=11 Python. To za mało. Opcje:
1. **Crowdsourced panel:** większa liczba oceniających (7–10), Condorcet aggregation
2. **Blast radius:** pct_cross_package_fixes z historii VCS — r=0.31 (n=25), najlepszy automatyczny GT
3. **Defects4J:** baza bugów z poprawkami — wymaga Java 8 (ograniczone)
4. **Zewnętrzne oceny:** Jolak, Papers With Code, architekturalne case studies

```
Rekomendacja: blast_radius jako GT automatyczny dla dużych n
               panel jako GT premium dla walidacji
```

#### Q12: Jak kontrolować za „poinformowaną architekturą"?

Problem selection bias: GT panel bazuje na nazwach projektów które eksperci znają. DDD repos (dddsample, IDDD) są oceniane wysoko po części dlatego że są słynne jako przykłady dobrej architektury. Czy ślepy panel (bez nazw) dałby inne wyniki?

---

### VI. Interpretacja i użytkowanie

#### Q13: Co zrobić z wynikiem 0.50?

Fingerprint LAYERED: AGQ ≈ 0.45–0.55 (środek skali). To 80% projektów benchmarku. AGQ nie odróżnia dobrze projektów w środku zakresu. Potrzeba albo:
- Rozszerzonego zakresu (więcej POS z AGQ>0.70 i NEG z AGQ<0.35)
- Lub przyznania że AGQ klasyfikuje dobrze tylko ekstrema

#### Q14: Kiedy AGQ_z (Z-score) jest lepszy niż AGQ?

AGQ_z = normalizacja względem mediany i odchylenia standardowego dla języka. Dla użytkownika: „twój projekt jest w top 20% projektów Java tej wielkości". Pytanie: czy AGQ_z ma lepszą korelację z GT niż surowe AGQ?

---

## Priorytety badawcze (subiektywna ocena)

| Pytanie | Priorytet | Koszt | Blokada |
|---|---|---|---|
| Q11: GT n≥100 | **1 — krytyczny** | wysoki | czas |
| Q1: Go walidacja | **2 — ważny** | średni | panel ekspertów Go |
| Q3: CD mechanizm dla Pythona | **3 — ważny** | niski | n_neg_Python |
| Q7: Heurystyki semantyczne | 4 — badawczy | wysoki | parser Rust |
| Q6: DDD vs anemic domain | 5 — akademicki | bardzo wysoki | semantyka |

## Zobacz też

- [[Hypotheses Register]] — formalny rejestr hipotez O1–O5
- [[O1 AGQv3c Java to Go]] — Go walidacja
- [[O2 Type 2 Legacy Monolith Detection]] — false positive problem
- [[O3 AGQv3c vs AGQv2 on Jolak]] — zewnętrzna walidacja
- [[O4 Namespace Metrics for Python]] — metryki namespace
- [[O5 Python CD Direction]] — mechanizm odwróconego CD
- [[How to Read Experiments]] — protokół badawczy
