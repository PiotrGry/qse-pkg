# Teza badawcza — AGQ jako Quality Gate dla kodu AI (2026-03-06)

## Kontekst: Vibe coding to nie moda

Vibe coding = wczesna faza przejscia do aplikacji pisanych w calosci przez AI.
- Pass@1 rosnie ~10pp/rok (GPT-3.5 -> Claude Sonnet 4 = 77%)
- GitHub: >40% kodu enterprise z AI (2025)
- Narzedzia: autocomplete -> autonomous agent (Devin, Cursor, Claude Code)
- Brak udokumentowanego enterprise-grade systemu w calosci przez AI (stan: 2026-03)
- Jestesmy na etapie "AI pisze, czlowiek recenzuje" — pelna autonomia = kwestia quality gates

## Problem: Quality drift w erze AI

1. **Paradoks Sabra:** lepszy model = wyzszy Pass@1 = WIECEJ defektow strukturalnych
   - Claude Sonnet 4: najlepszy Pass@1 (77%) ale najgorszy jakosc (2.11 issues/task)
   - BLOCKER bugi 2x przy upgrade Claude 3.7 -> Sonnet 4
2. **Skala:** AI generuje kod 10-100x szybciej = drift 10-100x szybszy
3. **Brak pamieci architektonicznej:** LLM nie pamięta decyzji z poprzednich promptow
4. **Brak ownership:** nikt nie "czuje" kodu = nikt nie zauwaza erozji

## Pre-AI quality stack vs luka

| Warstwa | Narzedzie | Co lapie |
|---|---|---|
| Linting | ESLint, Pylint | Styl, proste bledy |
| SAST | SonarQube, Checkmarx | Code smells, vulnerabilities per PLIK |
| Testy | Unit/Integration/E2E | Poprawnosc funkcjonalna |
| Code review | Czlowiek | Architektura, design, intencja |
| Arch rules | ArchUnit (Java only) | Zaleznosci miedzy pakietami |

**Luka:** Code review = JEDYNA warstwa widząca architekture. Usun czlowieka = nikt nie pilnuje makro.

## Research gap

Istniejace narzedzia QA operuja na poziomie pliku (SonarQube) lub wymagaja
ludzkiego reviewera do oceny architektonicznej. W erze kodu generowanego przez AI
— gdzie wolumen rosnie wykladniczo, a jakosc strukturalna spada (Sabra et al.)
— brakuje **deterministycznego, automatycznego quality gate na poziomie grafu
zaleznosci**, ktory moglby zastapic architektoniczny aspekt code review.

## Teza glowna

AGQ (Architecture Graph Quality) jako "Policy as a Service" moze zastapic
architektoniczny aspekt code review poprzez deterministyczne metryki grafowe
+ deklaratywne constraints, umozliwiajac bezpieczna autonomiczna generacje kodu.

## Research Questions

RQ1: Czy metryki grafowe (Modularity, Acyclicity, Stability, Cohesion) koreluja
     z defect density w repozytoriach open-source? (cel: Pearson r >= 0.5)

RQ2: Czy AGQ score potrafi wykryc degradacje architektoniczna niewidoczna
     dla SonarQube? (porownanie R^2: AGQ vs SQ Maintainability Rating)

RQ3: Czy deklaratywne constraints (forbidden edges) pokrywaja dominujace
     kategorie defektow w kodzie LLM (code smells = 90-93%, Sabra et al.)?

RQ4: Czy ratchet mechanism (score nie moze spasc) skutecznie blokuje
     quality drift w CI przy ciaglej generacji kodu przez AI?

## Hipotezy

H1: AGQ koreluje z defect density silniej niz SonarQube Maintainability Rating
    (Pearson r_AGQ > r_SQ na N=100 OSS repos)

H2: Kod generowany przez LLM z AGQ gate ma nizszy defect density niz
    kod bez gate (kontrolowany eksperyment, ten sam LLM + prompt)

H3: Ratchet + forbidden edges redukuje potrzebe human code review o >= 70%
    (mierzone: % PR wymagajacych interwencji czlowieka)

H4: AGQ adresuje ~80% defektow wykrywanych w kodzie LLM (mapowanie
    metryk na kategorie Sabra et al.)

## Pass@1 i benchmarki LLM

Pass@1 = prawdopodobienstwo ze pierwsza probka kodu przechodzi wszystkie testy.
Sukces = kompilacja + wszystkie asserty PASS. Nie sprawdza jakosci, architektury, security.

### Paradoks Sabra — mechanizm

Lepszy model rozwiazuje trudniejsze zadania = bardziej zlozony kod = wiecej defektow.
Pass@1 nagradza "dziala", nie karze za "spaghetti". Testy nie sprawdzaja JAKOSCI.
Dowod: upgrade Claude 3.7->Sonnet 4: Pass@1 +4.58pp, BLOCKER bugi +93%.
Branza optymalizuje LLM pod Pass@1 = systematycznie rosnie ukryty dlug techniczny.

### Benchmarki kodu LLM — kategorie

Poprawnosc funkcjonalna: Pass@1, Pass@k (HumanEval, MBPP, SWE-bench, EvoCodeBench)
Podobienstwo do referencji: BLEU, CodeBLEU, CrystalBLEU, ROUGE
Execution-based: TLE, MLE, CE, RTE (czy crashuje, czy jest wolny)
Jakosc statyczna: SonarQube issues/task (TYLKO Sabra et al.), CC (sporadycznie)
Multi-dim: ProxyWar, EvoCodeBench (correctness+efficiency+robustness+adaptability)

### Multi-dimensional benchmarki — szczegoly

ProxyWar (2602.04296): Arena rywalizacji LLM-ow. Dwa modele dostaja to samo zadanie,
kody rywalizuja w execution arena. Wymiary: correctness, efficiency, robustness,
adaptability. Ranking ELO-like. Cel: dynamiczna ewaluacja odporna na memorization.

EvoCodeBench (2602.10171): 3822 zadan, 5 jezykow, self-evolution (rotacja zadan
vs data leakage). 7 wymiarow: Pass@k, CE, RTE, TLE, MLE, avg runtime, avg memory.
Human-performance baseline. Cel: odpornosc na contamination + efektywnosc.

BigCodeBench: Praktyczne zadania (API calls, pandas, sqlite — nie algorytmy olimpiad).
Warianty: Complete (docstring->kod) i Instruct (NL->kod).
Cel: mierzyc "codzienna praca developera".

### AGQ vs benchmarki — NIE konkurencja

Benchmarki oceniaja MODEL ("ktory LLM lepszy?") — mikro, per zadanie, pre-deployment.
AGQ ocenia KOD ("czy ten PR psuje architekture?") — makro, per projekt, post-generation.

Relacja komplementarna: benchmark -> wybierasz model, AGQ -> pilnujesz wynik modelu.
Nawet najlepiej zbenchmarkowany model potrzebuje quality gate w CI.

### Luka w benchmarkach

NIE ISTNIEJE benchmark mierzacy jakosc architektoniczna kodu LLM.
Sabra = jedyny paper z statyczna analiza jakosci, i to tylko SonarQube (mikro/plik).
Nikt nie mierzy makro (graf zaleznosci, modularity, cykle, stability).
= luka ktora wypelnia AGQ.

## Mapowanie: Metryki AGQ -> Kategorie defektow Sabra et al.

### Code Smells (90-93% defektow)

| Defekt (Sabra) | Metryka AGQ | Level |
|---|---|---|
| Dead/Unused/Redundant code (14-43%) | Cohesion (LCOM4), Modularity, Zombie detector | L1+L2 |
| Design/Framework best practices (11-22%) | Constraints (forbidden edges), Stability | L2+L1 |
| Cognitive complexity (4-8%) | CC (cyclomatic complexity) | L1 |

### Bugs (5-8%)

| Defekt (Sabra) | Metryka AGQ | Level |
|---|---|---|
| Control-flow mistakes (14-48%) | CC, Acyclicity | L1 |
| Exception handling (11-17%) | Anemic detector | L2 |
| Resource management/leaks (7-15%) | Coupling (Ca/Ce) | L1 |

### Vulnerabilities (~2%)

| Defekt (Sabra) | Metryka AGQ | Level |
|---|---|---|
| Path-traversal & injection (31-34%) | Constraints (forbidden edges) | L2 |
| Hard-coded credentials (14-30%) | POZA ZAKRESEM (SAST) | — |
| Crypto misconfiguration (19-25%) | POZA ZAKRESEM (SAST) | — |

Pokrycie wazone: ~80% defektow adresowalnych przez AGQ.

## Model "Policy as a Service" w CI

```
Dzis:     LLM -> kod -> CZLOWIEK review -> merge
Jutro:    LLM -> kod -> AGQ gate -> merge (czlowiek tylko przy FAIL)
```

Ratchet = score nigdy nie spada. Kazdy PR >= poprzedni. Drift fizycznie niemozliwy.

```yaml
# qse.yaml — deklaratywna polityka jakosci
gate:
  agq_min: 0.80
  max_cc_per_function: 15
  max_coupling: 0.3
constraints:
  - from: "src/api/**"
    to: "src/db/**"
    type: forbidden
  - from: "src/domain/**"
    to: "src/infrastructure/**"
    type: forbidden
ratchet: true
```
