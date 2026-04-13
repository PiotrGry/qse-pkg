---
type: experiment
status: zakończony
language: pl
---

# Pilot Multi-Repo Scan — archtest na 15 repozytoriach spoza GT

## Prostymi słowami

Przeskanowaliśmy 15 repozytoriów Java spoza Ground Truth narzędziem qse-archtest. Wynik jest krytyczny: **AGQ jest odwrócone** — kolekcje tutoriali i algorytmów dostają wyższe AGQ niż dobrze zaprojektowane frameworki. 5/5 "złych" repozytoriów = GREEN, 1/5 "dobrych" = RED. Trzy z pięciu komponentów (M, S, CD) działają odwrotnie niż powinny na tym zbiorze. Przyczyna: "efekt archipelagu" — rozłączone moduły wyglądają jak dobra modularność dla grafowych metryk.

---

## Szczegółowy opis

### Cel

Przetestować qse-archtest na zróżnicowanym zbiorze repozytoriów spoza GT, żeby ocenić:
1. Blind spot rate (GREEN dla złych repos)
2. False positive rate (RED dla dobrych repos)
3. Rozkład statusów i składowych
4. Czy problem z Pilot-1 (blind spot) jest systemowy czy incydentalny

### Wybór repozytoriów

| Repo | Typ | Expected | Uzasadnienie |
|---|---|---|---|
| AxonFramework | CQRS/ES framework | GOOD | Referencyjny DDD framework |
| Dropwizard | REST framework | GOOD | Dojrzały, dobrze zaprojektowany |
| Apollo Config | Config management | GOOD | Alibaba, enterprise-grade |
| Zalando Logbook | HTTP logging lib | GOOD | Czysty design, Zalando |
| Eventuate Tram | Event-driven | GOOD | Microservices patterns |
| Alibaba Nacos | Service discovery | MIXED | Duży, złożony, enterprise |
| Alibaba Canal | Binlog subscriber | MIXED | Specjalistyczny tool |
| Redisson | Redis client | MIXED | Duży, utility-like |
| Apache Dubbo | RPC framework | MIXED | Ogromny, historycznie narastający |
| MyBatis | SQL mapper | MIXED | Utility framework |
| TheAlgorithms/Java | Algorithm collection | BAD | Brak architektury, luźna kolekcja |
| Baeldung Tutorials | Tutorial collection | BAD | 37k plików, kolekcja przykładów |
| Spring Boot Demo | Demo collection | BAD | Demo apps, nie real project |
| JCSprout | Java basics | BAD | Kolekcja snippetów |
| SB Learning Example | Learning examples | BAD | Przykłady edukacyjne |

---

## Wyniki

### Pełna tabela

| Repo | Expected | AGQ | Status | M | A | S | C | CD | Nodes | E/N |
|---|---|---|---|---|---|---|---|---|---|---|
| SB Learning Example | BAD | 0.692 | GREEN | 0.808 | 1.000 | 0.462 | 0.525 | 0.664 | 266 | 2.0 |
| JCSprout | BAD | 0.668 | GREEN | 0.818 | 1.000 | 0.222 | 0.538 | 0.763 | 198 | 1.4 |
| Baeldung Tutorials | BAD | 0.627 | GREEN | 0.803 | 1.000 | 0.439 | 0.480 | 0.416 | 37250 | 3.5 |
| Spring Boot Demo | BAD | 0.599 | GREEN | 0.871 | 1.000 | 0.056 | 0.493 | 0.574 | 1084 | 2.6 |
| TheAlgorithms | BAD | 0.564 | GREEN | 0.643 | 1.000 | 0.222 | 0.361 | 0.593 | 1712 | 2.4 |
| Eventuate Tram | GOOD | 0.543 | AMBER | 0.647 | 1.000 | 0.160 | 0.546 | 0.363 | 607 | 3.8 |
| Alibaba Canal | MIXED | 0.520 | AMBER | 0.710 | 0.997 | 0.146 | 0.423 | 0.324 | 1470 | 4.1 |
| Dropwizard | GOOD | 0.494 | AMBER | 0.646 | 0.996 | 0.115 | 0.449 | 0.264 | 2087 | 4.4 |
| MyBatis | MIXED | 0.492 | AMBER | 0.659 | 0.969 | 0.121 | 0.438 | 0.276 | 1754 | 4.3 |
| Apache Dubbo | MIXED | 0.486 | AMBER | 0.647 | 0.987 | 0.255 | 0.377 | 0.164 | 7135 | 5.0 |
| Zalando Logbook | GOOD | 0.480 | AMBER | 0.624 | 1.000 | 0.051 | 0.418 | 0.307 | 1296 | 4.2 |
| Redisson | MIXED | 0.467 | AMBER | 0.635 | 0.987 | 0.098 | 0.285 | 0.329 | 2938 | 4.0 |
| Apollo Config | GOOD | 0.453 | AMBER | 0.594 | 0.997 | 0.105 | 0.445 | 0.121 | 1415 | 5.3 |
| Alibaba Nacos | MIXED | 0.416 | RED | 0.589 | 0.998 | 0.086 | 0.408 | 0.000 | 5333 | 7.3 |
| AxonFramework | GOOD | 0.405 | RED | 0.551 | 0.996 | 0.074 | 0.404 | 0.000 | 3937 | 6.2 |

### Kluczowe statystyki

| Metryka | Wartość |
|---|---|
| **Blind spots (BAD→GREEN)** | **5/5 = 100%** |
| **False positives (GOOD→RED)** | **1/5 = 20%** |
| **Correct extreme calls** | **0/10** |
| Mean AGQ — Expected GOOD | 0.475 |
| Mean AGQ — Expected MIXED | 0.476 |
| Mean AGQ — Expected BAD | **0.630** |

**AGQ jest odwrócone: expected-BAD repos mają wyższe AGQ niż expected-GOOD.**

### Korelacja

| Para | Spearman ρ | p |
|---|---|---|
| E/N ratio vs AGQ | **−0.900** | **<0.0001** |
| Nodes vs AGQ | −0.500 | 0.058 |

E/N ratio (edges/nodes) jest niemal idealnym negatywnym predyktorem AGQ — im więcej zależności per node, tym niższe AGQ. To karze prawdziwe systemy za bycie prawdziwymi systemami.

### Analiza per-komponent

| Komponent | Avg GOOD | Avg BAD | Delta | Kierunek |
|---|---|---|---|---|
| M (Modularity) | 0.612 | 0.789 | +0.176 | **INVERTED** |
| A (Acyclicity) | 0.998 | 1.000 | +0.002 | ≈ same |
| S (Stability) | 0.101 | 0.280 | +0.179 | **INVERTED** |
| C (Cohesion) | 0.452 | 0.479 | +0.027 | ≈ same |
| CD (Coupling Density) | 0.211 | 0.602 | +0.391 | **INVERTED** |

**Trzy z pięciu komponentów (M, S, CD) są odwrócone na tym zbiorze.**

---

## Diagnoza: "Efekt archipelagu"

Kolekcje tutoriali i algorytmów to "archipelagi" — wiele małych, niezależnych modułów bez wspólnej architektury. Grafowe metryki interpretują to jako doskonałą modularność:

1. **M (Modularity)**: Rozłączone componenty = silna struktura community (wysoki Louvain Q)
2. **S (Stability)**: Pakiety z niskim E/N mają równomierną instability → mała wariancja → wysokie S
3. **CD (Coupling Density)**: CD = 1 − clip(E/N / 6.0). Niskie E/N → wysokie CD. Kolekcje mają E/N ≈ 1.5-2.5 → CD ≈ 0.6-0.75

Problem nie w formule samej w sobie (wewnątrz GT działa poprawnie), ale w tym że **GT nie zawiera archipelagów**. GT składa się z prawdziwych aplikacji i frameworków. AGQ discriminuje dobrze WŚRÓD prawdziwych systemów, ale nie odróżnia prawdziwego systemu od kolekcji luźnych modułów.

### Dlaczego wewnątrz GT to nie widać?

W GT (n=59) korelacja E/N vs panel jest ρ=−0.230 (p=0.08) — słaba i nieistotna. Rozkład E/N w GT: [1.6, 7.2], median=3.4. Różnica POS vs NEG E/N: 3.31 vs 4.28 — istotna (p=0.007), ale E/N nie dominuje bo GT nie ma archipelagów. Po wyjściu poza GT, archipelago pattern dominuje.

---

## Implikacje

### Krytyczne

1. **AGQ w obecnej formie NIE nadaje się do skanowania dowolnych repozytoriów** — daje fałszywe GREEN dla kolekcji/archipelagów
2. **Potrzebna pre-filtracja lub nowa metryka** — detekcja "czy to jest prawdziwy system czy kolekcja"
3. **GT wymaga rozszerzenia o archipelagi** — żeby formuła mogła się nauczyć tej różnicy
4. **Claims & Evidence wymagają aktualizacji** — claim "AGQ discriminates architecture quality" musi mieć caveat "within single-project repositories"

### Zrealizowane rozwiązania (kwiecień 2026)

**1. Archipelago Detector w archtest.py** (zrealizowane)

Dodano detekcję archipelagu do pipeline'u skanowania. Detektor oblicza metryki połączeniowe (connected components) z grafu NetworkX i emituje ostrzeżenie gdy cc_ratio > 0.08 (>8% węzłów poza największą składową spójną).

| Próg | Wartość | Opis |
|---|---|---|
| cc_ratio > 0.08 | HIGH | Prawdopodobna kolekcja — AGQ niemoarodajne |

Walidacja na 22 repozytoriach:
- **0 false positives** na POS/GOOD repos
- Wyłapuje ekstremalnych archipelagów (TheAlgorithms, JCSprout, java-design-patterns)
- Zawsze emituje metryki połączeniowe w raporcie (nawet bez ostrzeżenia)

Testowane próg T2 (E/N < 3.0 + cc_ratio) zostało odrzucone — generowało false positives na małych, dobrze zaprojektowanych repos (spring-petclinic, buckpal).

**2. GT EXCL — wykluczenie kolekcji** (zrealizowane)

4 repozytoria-kolekcje przeniesione z POS do EXCL:
- iluwatar/java-design-patterns (300 niezależnych demo)
- camunda/camunda-bpm-examples
- javaee-samples/javaee7-samples
- quarkusio/quarkus-quickstarts

Uzasadnienie: nie są pojedynczymi systemami z architekturą. Metryki grafowe nie mają sensownej interpretacji.
Wpływ: accuracy 67.8% → 65.5%, AUC 0.767 → 0.733 (uczciwy spadek).
Szczegóły: [[Ground Truth#Wykluczone repozytoria (EXCL)]]

### Potencjalne dalsze rozwiązania (niezrealizowane)

| Rozwiązanie | Trudność | Opis |
|---|---|---|
| Nowa metryka: inter-package connectivity | Średnia | % edges crossing package boundaries |
| Normalizacja CD przez project-type | Wysoka | Klasyfikacja: single-app vs collection vs library |

---

## Artefakty

- `artifacts/pilot_multirepo_results.json` — pełne wyniki 15 repos
- Clones: `pilot_clones/` (local, nie committed)
- Scan results: `pilot_scan_results/` (local, nie committed)

## Zobacz też

- [[Pilot OSS]] — Pilot-1 (before/after refactoring)
- [[Current Priorities]] — kontekst
- [[Experiments Index]] — indeks
- [[AGQv3c Java]] — wzór AGQ
- [[Ground Truth]] — skład GT
