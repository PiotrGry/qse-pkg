---
type: meta
language: pl
---

# Otwarte Pytania Badawcze — Rozszerzony Widok

## Prostymi słowami

Projekt badawczy uczciwy wobec siebie dokumentuje nie tylko to co wie, ale też co nie wie. QSE ma kilka fundamentalnych pytań bez odpowiedzi. To nie jest słabość — to mapa priorytetów dla kolejnych eksperymentów i przyszłych prac naukowych.

Nauka nie kończy się na znalezieniu odpowiedzi — kończy się na wyraźnym sformułowaniu pytań, które zostały. Ten dokument kataloguje pytania które QSE postawiło ale nie odpowiedziało. Każde pytanie to potencjalny przyszły eksperyment.

---

## Pytania badawcze pierwszorzędne (O1–O5)

**O1: Czy AGQ v3c generalizuje z Javy i Pythona na Go?**

Java n=59 (MW p=0.000221) i Python n=30 (flat_score p=0.007). Go jest przebadane tylko benchmarkiem (n=30) bez Ground Truth panelowego. Go ma strukturalnie inne właściwości (brak dziedziczenia klas → Cohesion=1.0 zawsze, ekosystem wymusza brak cykli → Acyclicity≈1.0). Czy metryki M i S nadal dyskryminują jakość dla Go?

*Kryterium sukcesu:* n≥20 Go repos z panelem, MW p<0.05.

**O2: Detekcja Type 2 Legacy Monolith w Pythonie**

Buildbot (Panel=2.75) ma flat_score=0.95 (bo ma głęboką hierarchię) ale jest złą architekturą. „Legacy monolith z hierarchią" to odrębny anty-wzorzec niewidoczny dla flat_score. Jak go wykryć?

Hipoteza: kombinacja wysokiego NSdepth z niskim Cohesion i wysokim CD. Do sprawdzenia.

**O3: Czy AGQ v3c jest lepsza od AGQ v2 na zbiorze Jolak?**

Wyniki sesji Turn 36-37: v3c i v2 mają identyczną moc na Javie (partial r=+0.524 vs +0.543). Jolak cross-validation potwierdziła S i CD. Ale czy v3c (equal 0.20 wagi) jest stabilniejsze na zewnętrznym zbiorze testowym?

**O4: Czy metryki namespace (NSdepth, NSgini) poprawiają AGQ dla Pythona?**

NSdepth ma silny sygnał dla Javy (partial r=+0.698, p=0.008) ale słaby dla Pythona (p=0.122 ns). NSgini jest ns wszędzie. Czy kombinacja NSdepth + flat_score + AGQ_v3c da lepszą moc dla Pythona?

**O5: Dlaczego CD ma odwrócony kierunek dla Pythona?**

Java: wyższe CD → NEG (p=0.034). Python: wyższe CD → POS (odwrotnie). Wyjaśnienie robocze: youtube-dl (NEG) ma 895 modułów w jednym namespace z minimalną liczbą krawędzi (brak struktury) → niski CD. Saleor (POS) ma wiele krawędzi między warstwami → wyższy CD. Ale to hipoteza, nie sprawdzony mechanizm.

---

## Pytania metodologiczne

**Czy symulowany panel jest wystarczający do publikacji naukowej?**

Panel ekspertów w QSE to cztery role symulowane przez LLM — nie prawdziwi eksperci. To ograniczenie metodologiczne. Dla publikacji naukowej może być potrzebna walidacja z prawdziwymi ekspertami (co najmniej n=3 niezależnych recenzentów).

**Czy AGQ-adj (korekta rozmiaru) jest potrzebna?**

Małe projekty (< 50 węzłów) mają zawyżone AGQ z powodów strukturalnych (trywialnie brak cykli w 10 plikach). AGQ-adj normalizuje względem rozmiaru. Czy to poprawia moc predykcyjną? Dane benchmarkowe sugerują r=+0.236 dla AGQ-adj vs hotspot_ratio — ale wymagają dalszej walidacji.

**Jak mierzyć jakość w mikrousługach?**

W systemie mikrousług każda usługa to osobne repozytorium. AGQ per-repo mierzy jakość jednej usługi, ale nie mierzy jakości systemu jako całości (sprzężeń między serwisami przez API). Jak QSE powinno obsłużyć multi-repo systemy?

---

## Pytania praktyczne

**Jaki próg AGQ jako quality gate?**

Benchmark pokazuje: Go mean=0.783, Python mean=0.748, Java mean=0.627. Próg 0.75 może być sensowny dla Pythona/Go, ale zablokuje ~50% projektów Java. AGQ-z jest lepszym mechanizmem gate'owania — ale „jak dużo poniżej średniej jest zbyt mało?"

**Czy AGQ jest stabilne w czasie?**

Projekt może mieć AGQ=0.72 w Q1 i 0.68 w Q2. Czy to degradacja architektoniczna? Czy tylko normalny szum wynikający z nowych modułów? Brak danych temporalnych — to kierunek przyszłych badań.

---

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
| Q1 / O1: Go walidacja | **2 — ważny** | średni | panel ekspertów Go |
| Q3 / O5: CD mechanizm dla Pythona | **3 — ważny** | niski | n_neg_Python |
| Q7: Heurystyki semantyczne | 4 — badawczy | wysoki | parser Rust |
| Q6: DDD vs anemic domain | 5 — akademicki | bardzo wysoki | semantyka |

---

## Lista otwartych pytań (format wiki)

- [[O1 AGQv3c Java to Go]] — generalizacja na Go
- [[O2 Type 2 Legacy Monolith Detection]] — wykrywanie legacy monolith
- [[O3 AGQv3c vs AGQv2 on Jolak]] — porównanie wersji
- [[O4 Namespace Metrics for Python]] — rozszerzenie dla Pythona
- [[O5 Python CD Direction]] — odwrócony kierunek CD

## Definicja formalna

Otwarte pytanie \(Q\) spełnia:

- \(Q\) jest falsyfikowalne (istnieje eksperyment który odpowie TAK lub NIE)
- \(Q\) dotyczy mierzalnej właściwości systemu AGQ
- \(Q\) nie jest jeszcze odpowiedziane w żadnym eksperymencie \(E_1, \ldots, E_k\)

Pytania nie-falsyfikowalne (np. „czy AGQ jest filozoficznie poprawne?") nie należą do tej listy.

## Zobacz też

- [[Hypotheses Register]] — formalny rejestr hipotez O1–O5
- [[O1 AGQv3c Java to Go]] — Go walidacja
- [[O2 Type 2 Legacy Monolith Detection]] — false positive problem
- [[O3 AGQv3c vs AGQv2 on Jolak]] — zewnętrzna walidacja
- [[O4 Namespace Metrics for Python]] — metryki namespace
- [[O5 Python CD Direction]] — mechanizm odwróconego CD
- [[Experiments Index]] — zrealizowane eksperymenty
- [[Hypothesis]] — jak tworzyć hipotezy w QSE
- [[How to Read Experiments]] — protokół badawczy
