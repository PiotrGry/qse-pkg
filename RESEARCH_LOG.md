# QSE Research Log — Pełna historia badań

> Ostatnia aktualizacja: 14 kwietnia 2026 (v2 — pełne E1-E7 + Piloty)
> Autor: Piotr Gryzło
> Branch: perplexity

---

## 1. Geneza projektu (luty 2026)

### Problem biznesowy
W dobie galopującego AI (Copilot, Cursor, Claude Code) generowany kod często ma defekty architektoniczne niewidoczne w standardowych linterach (SonarQube mierzy bug density, nie architekturę). Potrzeba twardej, automatycznej metryki jakości architektury kodu — niezależnej od języka, działającej w CI/CD.

### Cel
Stworzyć **QSE (Quality Score Engine)** — system automatycznej walidacji jakości architektury oprogramowania, działający jako "strażnik" w pipeline'ach CI/CD. Dwa zastosowania:
1. **FFplus B+R grant** — projekt badawczo-rozwojowy (AI code validation in DDD)
2. **Softwarehouse 2.0** — produkt komercyjny (SaaS metric dashboard)

### Fundament teoretyczny
AGQ (Architecture Graph Quality) — kompozytowa metryka bazująca na grafie zależności między modułami. Cztery wymiary:
- **M** (Modularity) — stosunek abstrakcji do betonu: `abstract_modules / total_modules`
- **A** (Acyclicity) — binarnie: czy graf pakietów jest DAG? `1.0` jeśli tak, `0.0` jeśli nie
- **S** (Stability) — `var(I_pkg) / 0.25`, gdzie I = instability Martina per pakiet (2nd-level grouping)
- **C** (Cohesion) — `1 - mean(LCOM4_norm)`, gdzie LCOM4 mierzy spójność klas
- **CD** (Coupling Density) — `internal_edges / (nodes * (nodes-1))`

---

## 2. Faza eksploracyjna — eksperymenty E1-E7 (luty–marzec 2026)

### Pierwsze eksperymenty
- Implementacja skanera w Rust (qse-core) dla Java, Python, Go
- AGQ v1: wagi `{M: 0.25, A: 0.25, S: 0.25, C: 0.25}`
- Benchmark na ~560 repo OSS (Python: 351, Java: 147, Go: 30, TS: 8)
- Odkrycie: korelacja AGQ z GitHub stars/issues jest słaba — potrzeba GT (Ground Truth)

### Budowanie Ground Truth
- **Java GT** — rozbudowane od n=14 do n=29 (final), potem n=59 (expanded)
  - POS: Spring Boot, Hibernate, Apache Commons, Guava, etc.
  - NEG: typical tutorial repos, spaghetti code, no-DDD patterns
  - Kryteria: panel ekspercki oceniający package organization, dependency hygiene, class responsibility, arch patterns, maintainability
- **Python GT** — n=23 (pos=10, neg=13), potem n=30
  - POS: Django, Flask, FastAPI, scikit-learn, Black, etc.
  - NEG: flat repos, god classes, no package structure

---

### E1 — Stability Hierarchy | Status: OBALONY

**Hipoteza:** Jeśli projekt ma poprawną hierarchię instability (domain < application < infrastructure), to jest lepszą architekturą.

**Dane:** GT Java n=13 (4 POS DDD + 3 non-DDD POS + 6 NEG)

**Wynik:** Spearman r(S_hierarchy, Panel) = **−0.093**, p = 0.762 **ns**

**Kluczowe odkrycie — paradoks mall vs library:**

| Repo | Panel | S_hierarchy | domain_instability | Typ |
|------|-------|-------------|-------------------|-----|
| mall | 2.0 | **1.0** | 0.024 | CRUD (MyBatis POJO sink) |
| ddd-by-examples/library | 8.5 | **1.0** | 0.464 | DDD (rich domain) |

Oba repo mają identyczny S_hierarchy = 1.0, ale z różnych powodów:
- **mall:** domain stabilna bo puste POJO (gettery/settery) — zero logiki → instability ≈ 0 → „poprawna hierarchia" przez przypadek
- **library:** domain stabilna bo dobrze zaprojektowane centrum domeny — ale klasy DDD rozmawiają ze sobą → instability = 0.464

**Wniosek:** Metryka Martina (fan-in/fan-out) nie odróżnia "stabilne bo dobrze zaprojektowane" od "stabilne bo puste POJO". Bez semantyki kodu (parsowanie body metod) to rozróżnienie jest niemożliwe. Hipoteza W7 definitywnie obalona.

---

### E2 — Coupling Density | Status: POTWIERDZONY ⭐

**Hipoteza:** Projekt z niskim stosunkiem krawędzi do węzłów (edges/nodes ratio) ma lepszą architekturę.

**Dane:** GT Java, iteracje n=10 → n=13 → n=14

**Kluczowe wyniki:**

| Metryka | Wartość | Istotność |
|---------|---------|----------|
| r(ratio, Panel) | **−0.787** | p = 0.007 ** |
| partial r (kontrola nodes) | **−0.697** | p < 0.05 * |

**Separacja POS vs NEG:**
- POS (dobra arch.): średni ratio = **2.62**, CD ≈ 0.56
- NEG (zła arch.): średni ratio = **4.25–4.9**, CD ≈ 0.35
- Mann-Whitney p = 0.010–0.034

**Porównanie AGQ v1 vs v2 (po dodaniu CD):**

| Test | AGQ v1 | AGQ v2 |
|------|--------|--------|
| Mann-Whitney p (POS vs NEG) | 0.038 * | **0.010 \*\*** |
| Spearman r (Panel) | +0.661 * | **+0.746 \*\*** |
| Partial r (kontrola nodes) | +0.564 ns | **+0.721 \*\*** |

AGQ v2 jako pierwsza wersja przeżywa kontrolę rozmiaru (partial r istotny). CD nie jest bias na DDD — Mann-Whitney DDD vs non-DDD: p=0.40 ns.

**Formuła:** `CD = 1 − clip((edges/nodes) / 6.0, 0, 1)`, wchodzi do AGQ v2 z wagą 0.20.

**Ograniczenia:** CD źle ocenia security frameworki (spring-security ratio=6.03 mimo Panel=6.50) i bardzo małe projekty (petclinic ratio=1.60 bo mały, nie bo dobry).

---

### E3 — Package Layer Classifier | Status: WSTRZYMANY

**Cel:** Binarna klasyfikacja pakietów jako domain/infrastructure/application na podstawie FQN.

**Problem:** Wymaga FQN węzłów (re-skan), a GT bazujący na BLT został obalony jako Ground Truth. Ścieżka A (GT n=13) możliwa, ale nie przeprowadzona. Eksperyment odłożony na rzecz E5/E6.

---

### E4 — Rozszerzenie GT do n≥30 | Status: ZAKOŃCZONY

**Cel:** Rozbudowa Ground Truth panelu do minimalnej próby statystycznej.

**Wyniki:**
- Java GT rozszerzony: n=14 → n=29 → n=59 (31 POS + 28 NEG)
- AGQ v2 partial r = +0.675, p = 0.008 — pierwsza liczba oparta na solidnych danych
- Python GT: pierwsze 20 repo, AGQ v2 działa na Python
- Commity: c1ee146, cfa15c8, c3a633e

---

### E5 — Namespace Metrics (NSdepth i NSgini) | Status: CZĘŚCIOWY

**Hipoteza:** Metryki przestrzeni nazw eliminują odwrócony kierunek sygnału między Javą a Pythonem.

**Dane:** Java GT n=14, Python GT n=7

**Kluczowe wyniki:**

| Metryka | Java partial r | Java p | Python partial r | Python p | Zgodność kierunku |
|---------|---------------|--------|-----------------|----------|------------------|
| AGQ v2 | — | ** | — | ns | ODWROTNY ✗ |
| **NSdepth** | **+0.698** | **0.008** | +0.433 | 0.122 ns | ZGODNY ✓ |
| NSgini | — | ns | — | ns | brak sygnału |

**Dlaczego NSdepth działa dla Javy ale nie dla Pythona:**
- Java konwencja głębokich pakietów: `com.company.app.domain.model` → depth=5; dobre projekty mają głębię 4-6, złe 2-3
- Python strukturalnie płytszy: netbox (Panel=8.0) → depth=3.7, youtube-dl (Panel=2.25) → depth=3.1 — Δ=0.6 za małe

**Odkrycie multikolinearności:** S i AGQ v2: r=+0.852 (tautologia, S ma wagę 0.35). Zastąpienie A przez NSdepth poprawiłoby ortogonalność.

**Wniosek:** NSdepth lepsze od CD dla Javy (r=+0.698 vs r=+0.508), ale gorsze jako składowa AGQ w kombinacji. Problem Pythona wymaga dedykowanej metryki → prowadzi do E6.

---

### E6 — flatscore (dla Pythona) | Status: POTWIERDZONY ⭐

**Hipoteza:** flatscore (odsetek węzłów zagnieżdżonych głębiej niż 2 poziomy FQN) predykuje jakość architektury Python.

**Dane:** GT Python n=11 (5 POS + 6 NEG)

**Kluczowe wyniki:**

| Metryka | pos_mean | neg_mean | Δ | MW p | partial r |
|---------|----------|----------|---|------|-----------|
| **flat_score** | **0.665** | **0.200** | **+0.465** | **0.004 \*\*** | **+0.670 \*\*** |
| AGQ v2 | 0.553 | 0.643 | −0.090 | 0.066 ns | −0.309 ns |
| AGQ v3c | 0.565 | 0.453 | +0.112 | 0.045 * | +0.460 * |

**Kluczowe przykłady:**
- **youtube-dl:** 895/895 węzłów w depth≤2 → flat_score=0.000 (Panel=2.25, NEG) — AGQ v2 daje 0.831 (najwyższy!)
- **netbox:** flat_score=0.936 (Panel=8.0, POS) — AGQ v2 daje 0.504

**Przełom:** AGQ v3c jako pierwsza metryka kompozytowa ma **zgodny kierunek i istotność statystyczną w obu językach jednocześnie** (Java Δ=+0.107 p=0.001, Python Δ=+0.112 p=0.045).

**Formuła:** `flat_score = 1 − (nodes z depth≤2) / total_nodes`
- 0.0 = flat spaghetti (wszystko w depth≤2)
- 1.0 = hierarchiczna struktura (wszystko głębiej)

Wchodzi do AGQ v3c Python z najwyższą wagą 0.35:
```
AGQ v3c (Python) = 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score
```

---

### E7 — P4 Java-S na Expanded GT (n=59) | Status: ZAKOŃCZONY ⭐

**Cel:** Czy v3c z równymi wagami 0.20 jest optymalna na rozszerzonym GT?

**Protokół:** 18 wariantów wag, Bootstrap CI (B=5000), split-half stability test.

**Top 5 wariantów (z 18):**

| # | Wariant | Wagi (M/A/S/C/CD) | Partial r | p | AUC |
|---|---------|-------------------|-----------|---|-----|
| 1 | C_boost | 10/10/20/30/30 | 0.484 | 0.0001 | 0.789 |
| 2 | S10_C30_CD20 | 20/20/10/30/20 | 0.472 | 0.0002 | 0.785 |
| ... | ... | ... | ... | ... | ... |
| 9 | **v3c** | **20/20/20/20/20** | **0.447** | **0.0004** | **0.767** |

**S Monotonicity — ZŁAMANA:**
- Na n=29: silna monotoniczność (ρ=1.00) — im więcej S, tym lepiej
- Na n=59: **ρ=0.00 (p=1.00)** — brak monotoniczności. Inverted-U z peakiem przy S=0.20
- Interpretacja: S na n=29 miała artefaktycznie silny sygnał. Na n=59 S jest istotna (p=0.016) ale nie dominująca

**Split-half stability:** Żaden wariant nie jest stabilny (Δ partial_r > 0.15). Krajobraz optymalizacji płaski — różnice mniejsze niż szum.

**Wnioski:**
1. v3c POTWIERDZONE — brak dowodów na lepszy wariant
2. S monotonicity to artefakt małego zbioru
3. C i CD kluczowe — warianty z wyższą wagą C/CD numerycznie lepsze (ale w CI)
4. **Zamknięcie optymalizacji wag** — v3c 0.20 jest rekomendacją finalną

---

### Pilot-1 — Before/After Refactoring OSS | Status: ZAKOŃCZONY

**Repo:** `colinbut/monolith-enterprise-application` → fork `PiotrGry/qse-pilot-enterprise`
(84 pliki Java, 194 nodes, 609 edges, warstwowa architektura)

**Refactoring (19 plików, +451/-129 linii):**
1. Extract ClientProjectPort + ClientProjectAdapter (usunięcie RestTemplate z domain)
2. Move 4 repository impls z domain/ → infrastructure/
3. Fix UserServiceImpl — UserDao → UserRepository
4. Refactor ReportingData — kompozycja zamiast agregacji

**Wyniki:**

| Metryka | BEFORE | AFTER | Delta |
|---------|--------|-------|-------|
| AGQ_v3c | 0.5739 | 0.5760 | **+0.002 (szum!)** |
| S | 0.1900 | 0.1900 | 0.0 (bez zmian) |
| C | 0.5147 | 0.5143 | −0.0004 |
| Expert Panel | 3.0/10 (NEG) | — | — |
| AGQ Status | GREEN | GREEN | **BLIND SPOT** |

**Wnioski:**
- **Sensitivity AGQ: NISKA** — +0.002 po istotnym refactoringu = szum
- **S nie zareagowało wcale** — mimo fundamentalnej zmiany kierunków zależności
- **Blind spot POTWIERDZONY** — AGQ=GREEN vs Expert=NEG, nie rozwiązany przez refactoring
- **CI/CD: SUKCES** — GitHub Actions pipeline działał poprawnie (~30s scan)

---

### Pilot-2 — Multi-Repo Scan (15 repos) | Status: ZAKOŃCZONY, KRYTYCZNY ⚠️

**Cel:** Test qse-archtest na 15 repo spoza GT (5 GOOD + 5 MIXED + 5 BAD).

**KRYTYCZNY WYNIK — AGQ jest odwrócone:**

| Kategoria | Przykłady | Mean AGQ | Status |
|-----------|-----------|----------|--------|
| Expected BAD | TheAlgorithms, Baeldung, JCSprout | **0.630** | 5/5 GREEN |
| Expected GOOD | AxonFramework, Dropwizard, Apollo | **0.475** | 1/5 RED |
| Expected MIXED | Dubbo, MyBatis, Redisson | 0.476 | — |

**Per-komponent analiza — 3/5 odwrócone:**

| Komponent | Avg GOOD | Avg BAD | Kierunek |
|-----------|----------|---------|----------|
| M | 0.612 | 0.789 | **INVERTED** |
| S | 0.101 | 0.280 | **INVERTED** |
| CD | 0.211 | 0.602 | **INVERTED** |
| A | 0.998 | 1.000 | ≈ same |
| C | 0.452 | 0.479 | ≈ same |

**Diagnoza — "Efekt archipelagu":**
Kolekcje tutoriali i algorytmów to "archipelagi" — wiele małych, niezależnych modułów bez wspólnej architektury. Grafowe metryki interpretują to jako doskonałą modularność. Problem nie w formule (wewnątrz GT działa), ale w tym że **GT nie zawiera archipelagów**.

Korelacja E/N ratio vs AGQ: ρ = **−0.900** (p < 0.0001) — E/N ratio jest niemal idealnym negatywnym predyktorem AGQ.

**Zrealizowane rozwiązania:**
1. **Archipelago Detector** w archtest.py — cc_ratio > 0.08 = ostrzeżenie; 0 false positives na POS/GOOD repos
2. **GT EXCL** — 4 repo-kolekcje przeniesione z POS do EXCL (java-design-patterns, camunda-examples, javaee7-samples, quarkus-quickstarts)

**Implikacje:** AGQ w obecnej formie nie nadaje się do skanowania dowolnych repozytoriów bez pre-filtracji archipelagów.

---

### Ewolucja formuł AGQ
| Wersja | Wagi | Nowe metryki | Wynik |
|--------|------|--------------|-------|
| v1 | 0.25 × 4 | M, A, S, C | Bazowa, działa na Java |
| v2 | 0.20 × 5 | + CD | Lepsza dyskryminacja Java+Python |
| v3 | PCA-derived | + flat_score | Problemy z overfit |
| v3c | 0.20 × 5 (per-language) | + flat_ratio | **Winner** — optymalne dla Java i Python |

---

## 3. Faza walidacyjna (kwiecień 2026, sesja b5c7b74b — 206 turns)

### P0: Korekta danych i bugfixes
- Naprawiono 3 błędy w implementacji AGQ (metrics calculation)
- Zaktualizowano stale AGQ_v2 values dla 4 repo w GT
- Naprawiono `compute_instability_variance` NameError

### P1: Jolak Cross-Validation
- Skan 8 repo z artykułu Jolak et al. (external validation set)
- Pure-Python Java scanner (tree-sitter-java) — bo CLI nie działało na multi-module
- Wyniki: Jolak repos sit between GT-POS and GT-NEG (mean v3c=0.535)
- Wysoka wariancja S [0.065-0.954] — potwierdza niestabilność Jolak

### P2: Rozszerzenie GT Java do n=59
- Dodano 30 nowych repo (15 POS + 15 NEG → total 31 POS + 28 NEG)
- Kryteria: zróżnicowanie domen (e-commerce, messaging, auth, config)

### P3: Benchmark 558 repo
- Skan 558 repozytoriów (Java + Python + Go)
- iter4, iter5, iter6 — po ~560 repo każda iteracja z poprawkami skanera
- Naprawiono: `detect_language` dla Java multi-module, `walkdir_until_found`
- Odkryto: 28% repo miało nodes=0 (3 fixy w skanerze)

### P4: Java-S re-run na expanded GT (n=59)
- v3c z wagami 0.20 = winner
- S-weight monotonicity broken — inverted-U curve peaking at 0.20
- **Zamknięcie optymalizacji wag** — v3c 0.20 jest finalne
- Commit: 5566912

### Kluczowy wynik P0-P4
- **C jest najsilniejszym dyskryminatorem** jakości architektonicznej
- Partial Spearman r(C, panel) ≈ 0.5-0.7 po kontroli na size
- S wyjaśnia 72.6% wariancji AGQ_v2 — dominuje kompozyt

---

## 4. Obsidian Wiki (sesje 03c4a893, 10417e47)

Stworzono pełną wiki projektu w Obsidian, zorganizowaną w 11 sekcjach:
- 00 Home: wprowadzenie, mapa dokumentów
- 01 Canon: architektura systemu, invarianty, skaner
- 02 Concepts: wymiary konceptualne, graf zależności
- 03 Formulas: AGQ v1, v2, v3c definicje
- 04 Metrics: każda metryka opisana
- 05 Experiments: E1-E7 + piloty
- 06 Hypotheses: otwarte pytania (O1-O5), potwierdzone (W1-W10)
- 07 Benchmarks: 558 repo, Java GT, Python GT, Jolak
- 08 Glossary: AGQ, BLT, LCOM4, Tarjan SCC, etc.
- 09 Templates: szablony dla nowych eksperymentów
- 10 Handbook: podręcznik QSE
- 11 Research: future directions, limitations, literature review, market analysis

---

## 5. Faza pilotowa — seria E8-E13 (kwiecień 2026, sesje 840eb81e, 0ffb1d34)

### E8: LFR (Large-scale Feature Ranking)
- Ranking cech na n=29 Java GT
- S dominuje, C drugie, M/A marginalne

### E9: Pilot Battery
- Iteracyjne testowanie formuł na GT
- Odkrycie: AGQ_v2 lepsze od v3 na GT Java

### E10: GT Scan + Within-repo pilots
- Pełny skan GT z nowymi metrykami
- Within-repo: 5 repo × 19 iteracji (sztuczne perturbacje)

### E11: Literature approaches (A-D)
- **PRZEŁOM**: rank(C) + rank(S) — prosta suma rang lepiej dyskryminuje niż kompozyt
- Behavioral metrics (commit churn, bug density) — słaba korelacja z AGQ

### E12: Blind pilot on 14 new repos
- 14 repo spoza GT — walidacja "na ślepo"
- LOOCV (Leave-One-Out Cross-Validation) na GT

### E12b: QSE dual framework
- **QSE-Rank**: 2×rank(C) + rank(S) — ranking jakości architektonicznej
- **QSE-Track**: PCA, dip_violations, largest_scc — mierzenie zmian

### E13: Three-layer QSE framework
Ostateczna architektura systemu:

| Warstwa | Metryki | Cel |
|---------|---------|-----|
| Layer 1: QSE-Rank | M, A, S, C → AGQ_v2 | Ranking absolutny |
| Layer 2: QSE-Track | PCA, SCC, DIP violations | Śledzenie zmian |
| Layer 3: QSE-Diagnostic | C, S, percentyle, problemy | Szczegółowa diagnostyka |

### E13d: QSE-Track within-repo pilot
- 5 repo × 19 iteracji — QSE-Track reaguje na zmiany

### E13e: Shopizer pilot (pierwsza prawdziwa refaktoryzacja)
- Repo: Shopizer (~400 klas, e-commerce)
- Refaktoryzacja: usuwanie cykli pakietowych
- Wynik: **SCC 17→0, PCA 0.95→1.0, Panel 4.0→4.8**
- Layer 1 (M/A/S/C) NIE zareagował — Δ < 0.01
- **Wniosek**: Layer 2 łapie cykle, Layer 1 nieczuły na ten typ zmian
- Decyzja: **usunięcie M z QSE-Track** (commit dcfe68e)

### E13f: Apache Commons Collections pilot
- Repo: 458 klas, 20 pakietów
- Refaktoryzacja: przeniesienie 19 *Utils, ekstrakcja BuilderFactory, JDK wrappers
- Wynik: **PCA 0.11→1.0, SCC 16→0, Panel 5.3→5.7**
- Layer 1 nadal nieczuły (ΔS=0, ΔC=0)
- Potwierdza E13e: Layer 2 wiarygodny, Layer 1 wymaga głębszych zmian

### E13g: newbee-mall — Layer 1 validation pilot ⭐
- Cel: przetestować czy Layer 1 W OGÓLE reaguje
- Repo: newbee-mall (88 klas, panel=2.5, AGQ=0.493, label=NEG)
- 6 kroków refaktoryzacji:
  1. Package restructuring: `ltd.newbee.mall.*` → `mall.*` (6 2nd-level packages)
  2. Controller split: PersonalController → AuthController + ProfileController
  3. DAO CQRS split: 8 Mappers → ReadMapper + WriteMapper pairs
  4. Service CQRS split: 3 Services → QueryService + CommandService pairs
  5. Abstraction layer: ApiResponse, Pageable, DomainEntity, DataAccessObject interfaces
  6. VO/Entity cohesion: equals/hashCode/toString added to 23 classes

- **Wyniki**:
  - S: 0.21 → 0.59 (+0.38)
  - C: 0.29 → 0.36 (+0.07)
  - M: 0.59 → 0.61 (+0.02)
  - AGQ_v2: 0.493 → 0.639 (NEG → POS)
  - Panel formula: 2.5 → 5.7

### Krytyczna analiza E13g — co naprawdę się zmieniło

| Zmiana | Wpływ na architekturę | Wpływ na QSE | Ocena |
|--------|----------------------|--------------|-------|
| Namespace `ltd.newbee` → `mall` | Zerowy — te same importy | S: +0.38 (dominujący!) | KOSMETYKA |
| DAO Read/Write split | Pozorny — nikt nie używa oddzielnie | C/M: lekki | SZUM |
| Service Query/Command | Pozorny — controllery dalej używają starego IF | C: lekki | SZUM |
| Martwe interfejsy (4 szt.) | Zerowy — nikt ich nie implementuje | M: +0.02 | SZUM |
| PersonalController → Auth + Profile | Realny SRP split | Minimalny | OK |
| equals/hashCode na 23 entity | Boilerplate, ale poprawne | C: +0.07 | OK |

**Rzetelna ocena panelu**: 3.8/10 → 4.2/10 (+0.4), a nie +3.2 jak formuła sugeruje.

---

## 6. Zidentyfikowane problemy metryk

### PROBLEM 1: S jest gamingowalny przez zmianę namespace
- S liczy variance instability po 2. poziomie pakietu
- `ltd.newbee` = 1 blob → S ≈ 0.21
- `mall.*` (8 grup) → S = 0.59
- **Zero zmian w zależnościach** — czysto kosmetyczna zmiana

### PROBLEM 2: M pompowalne martwymi interfejsami
- Dodanie interfejsów których nikt nie implementuje podnosi M
- `abstract_modules` rośnie bez realnej architektury

### PROBLEM 3: LCOM4 źle liczy Java interfejsy
- Interface bez pól → LCOM4 = n_methods (maximum)
- Penalizuje dobrze zaprojektowane interfejsy

### PROBLEM 4: Panel formula zawyża delty 8x
- Deterministyczna formuła (hardcoded weights) → Δ=+3.2
- Rzetelna ocena → Δ=+0.4

---

## 7. Status metryk QSE (stan na 14.04.2026)

| Metryka | Status | Wiarygodność | Ryzyko gamingu |
|---------|--------|-------------|----------------|
| PCA (% acyclic pkgs) | Zwalidowana E13e+E13f | Wysoka | Niskie |
| SCC (largest cycle) | Zwalidowana E13e+E13f | Wysoka | Niskie |
| S (Stability) | **Wymaga naprawy** | Niska (namespace) | WYSOKIE |
| C (Cohesion) | Częściowo OK | Średnia (LCOM4) | Średnie |
| M (Modularity) | **Wymaga naprawy** | Niska (martwe IF) | Średnie |
| A (Acyclicity) | OK | Wysoka (binarna) | Niskie |
| AGQ_v2 (composite) | Zdominowana przez S | Niska | WYSOKIE |

---

## 8. Priorytetowe następne kroki

| Priorytet | Zadanie | Wpływ |
|-----------|---------|-------|
| P0 | Naprawić S — dependency-based grouping zamiast naming-based | Eliminuje gaming |
| P0 | M — ważyć tylko żywotne abstrakcje (z ≥1 implementacją) | Eliminuje pompowanie |
| P1 | Poprawić LCOM4 dla Java interfejsów | C wiarygodna dla Java |
| P1 | Replikacja E13g na 3-5 repo | Statystyczna istotność |
| P2 | Kalibracja panelu na n≥10 z niezależnymi recenzentami | Walidacja zewnętrzna |
| P2 | TypeScript scanner | Największy język AI-kodu |

---

## 9. Architektura kodu QSE

```
qse-pkg/
├── qse-core/          # Rust scanner (Java, Python, Go)
│   ├── src/
│   │   ├── graph.rs       # Dependency graph construction
│   │   ├── metrics.rs     # M, A, S, C, CD computation
│   │   ├── scanner.rs     # Language-specific file parsing
│   │   └── main.rs        # CLI entrypoint
├── qse/               # Python package (pip install -e .)
│   ├── java_scanner.py    # Pure-Python Java scanner (tree-sitter)
│   ├── qse_track.py       # QSE-Track: PCA, DIP, SCC
│   ├── qse_diagnostic.py  # QSE-Diagnostic: percentiles, problems
│   └── __init__.py
├── scripts/           # Experiment scripts (E8-E13)
├── artifacts/         # JSON results, charts, benchmark data
├── docs/
│   ├── qse-wiki/      # Obsidian wiki (11 sections)
│   └── wiki/          # GitHub wiki pages
├── tests/             # pytest test suite
└── setup.py
```

### Scanner Note
`qse scan` CLI zwraca puste wyniki dla multi-module repos Java. Dla E13 pilotów używamy bezpośrednio:
```python
from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
```

---

## 10. Otwarte pytania badawcze

### Potwierdzone hipotezy (W-series)
- **W1**: BLT correlation — częściowo (commit churn koreluje ze złożonością)
- **W4**: AGQv2 > AGQv1 na Java GT — potwierdzone
- **W7**: Stability hierarchy score — namespace depth nie pomaga
- **W9**: AGQv3c Python discriminates quality — potwierdzone
- **W10**: flatscore predicts Python quality — potwierdzone

### Otwarte hipotezy (O-series)
- **O1**: AGQv3c Java-to-Go transfer — nie testowane (Go GT brak)
- **O2**: Type 2 Legacy Monolith detection — flat_score fails for Type E
- **O3**: AGQv3c vs AGQv2 on Jolak — v3c nie lepsze
- **O4**: Namespace metrics for Python — NSgini słabe
- **O5**: Python CD direction — wymaga badań

---

## 11. Kontekst grantowy

### FFplus B+R
- Cel: AI code validation in DDD
- TRL: 3 → 7 (od proof-of-concept do prototypu)
- Status: teza B+R napisana, artifacts przygotowane
- Dokumenty: `artifacts/grant_*.md`

### Koszty infrastruktury
- Plan: 4× Mac Studio Ultra (cluster HPC)
- Badane programy: FENG SMART, PARP STEP, PFP Kraków, FEPW
- Wnioski: najlepsze dopasowanie to FFplus B+R lub PFP pożyczka rozwojowa

---

## 12. Kluczowe referencje naukowe

Pełna lista w `artifacts/references.md`. Najważniejsze:
- Martin, R. C. — Clean Architecture (Instability metric, DIP)
- Chidamber & Kemerer — LCOM4 (cohesion metric)
- Tarjan — Strongly Connected Components
- Jolak et al. — External validation dataset
- ISO 25010 — Software quality model (maintainability sub-characteristics)
