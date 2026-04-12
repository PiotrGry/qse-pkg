# Słownik pojęć i metryk — projekt AGQ / QSE

> **Wersja:** kwiecień 2026 (post Java-S experiment) | **Branch:** perplexity  
> Żywy dokument — aktualizowany po każdym eksperymencie.  
> Źródła prawdy: wyniki sesji > literatura > implementacja repo.  
> **Last updated:** 2026-04-12 — Java-S experiment results, AGQ v3c, S mechanism, Jolak cross-validation.

---

## Akronimy

| Akronim | Pełna nazwa | Kontekst |
|---|---|---|
| **AGQ** | Architecture Graph Quality | Główna metryka projektu — kompozyt M/A/S/C |
| **QSE** | Quality Software Engineering | Nazwa pakietu / projektu (`qse-pkg`) |
| **M** | Modularity | Składowa AGQ — modularność grafu |
| **A** | Acyclicity | Składowa AGQ — brak cykli |
| **S** | Stability | Składowa AGQ — stabilność wg Martina |
| **C** | Cohesion | Składowa AGQ — kohezja klas |
| **CD** | Coupling Density | Składowa AGQ v2 — gęstość sprzężeń (E2) |
| **BLT** | Bug Lead Time | Ground truth v1 — czas od otwarcia do zamknięcia buga |
| **GT** | Ground Truth | Dane referencyjne do walidacji AGQ |
| **DDD** | Domain-Driven Design | Metodologia projektowania — Evans, Vernon |
| **TRL** | Technology Readiness Level | Skala dojrzałości technologii (1–9) |
| **PC** | Package Coupling | Sprzężenie między pakietami (Jolak et al.) |
| **DL** | Dependency Length | Długość zależności w historii commitów (Jolak) |
| **LCOM** | Lack of Cohesion in Methods | Metryka kohezji klas (LCOM4 — wariant grafowy) |
| **LOOCV** | Leave-One-Out Cross-Validation | Walidacja krzyżowa na 8 projektach Jolak |
| **OSS** | Open Source Software | Publiczne repozytoria GitHub używane w benchmarku |
| **ASAT** | Automated Static Analysis Tool | Narzędzia jak SonarQube, PMD, Checkstyle |
| **CV** | Cross-Validation | Tu: Spearman r na podzbiorcach danych |
| **BC** | Bounded Context | Kontekst domenowy w DDD |
| **CQRS** | Command Query Responsibility Segregation | Wzorzec separacji odczytu i zapisu |
| **ns** | not significant | p > 0.05 — wynik statystycznie nieistotny |

---

## Metryki AGQ — szczegółowy opis

### AGQ — Architecture Graph Quality

```
AGQ = 0.20·M + 0.20·A + 0.55·S + 0.05·C

Zakres: [0.0, 1.0]
Próg research: ≥ 0.70
Próg TRL4:     ≥ 0.80
```

**Co mierzy:** jakość grafu zależności między pakietami/modułami projektu.  
Graf jest budowany przez parser tree-sitter (Rust) — węzły to pakiety, krawędzie to importy.

**Ograniczenia znane empirycznie (kwiecień 2026):**
- Ślepe na jakość DDD — `library` (Panel=8.5) ma AGQ=0.439 < `struts` (Panel=2.5) AGQ=0.449
- Kalibrowane głównie na Python (63% iter6) → bias względem Java
- Stability (55% wagi) penalizuje rich domain model — patrz sekcja S poniżej

---

### M — Modularity (Modularność)

```
Implementacja: Newman's Q via algorytm Louvain (NetworkX)
Normalizacja:  max(0, Q) / Q_REF  gdzie Q_REF = 0.75
Waga w AGQ:    0.20
Zakres:        [0.0, 1.0]
```

**Co mierzy:** czy pakiety grupują się w wyraźne klastry (spójne wewnętrznie, luźno powiązane z resztą). Q=0 → brak struktury społecznościowej. Q=0.75 → silna modularność (mapuje na 1.0).

**Interpretacja:**
- M > 0.70 → projekt dobrze podzielony na moduły
- M < 0.40 → brak wyraźnych granic modułowych (FLAT lub jeden wielki klaster)
- Uwaga: Louvain jest niedeterministyczny na małych grafach (nodes < 10 → zwraca 0.5 neutral)

**Typowe wartości (Java OSS, iter6):**
- DDD pozytywne: M ≈ 0.60–0.74
- Negatywne: M ≈ 0.55–0.67
- Słaby sygnał: Mann-Whitney p=0.476 ns na GT dataset (n=10)

---

### A — Acyclicity (Acykliczność)

```
Implementacja: 1 - (liczba węzłów w cyklach / total węzłów)
               wykrywanie SCC (Strongly Connected Components) przez Kosaraju
Waga w AGQ:    0.20
Zakres:        [0.0, 1.0]
```

**Co mierzy:** czy graf zależności zawiera cykle. Cykl = pakiet A importuje B, a B importuje A (bezpośrednio lub przez łańcuch). Cykle uniemożliwiają niezależne wdrożenie i testowanie modułów.

**Interpretacja:**
- A = 1.0 → DAG (Directed Acyclic Graph) — brak cykli, ideał
- A < 0.90 → poważny problem — znaczna część kodu w cyklach zależności
- A < 0.70 → ekstremalny spaghetti (np. OsmAnd A=0.676)

**Typowe wartości (Java OSS):**
- DDD wzorcowe (dddsample, library, ftgo): A = 1.000
- Negatywne: A = 0.85–0.99 (velocity-engine 0.871, struts 0.941)
- Mann-Whitney p=0.306 ns na GT n=10 — słaby sygnał przy małej próbie

---

### S — Stability (Stabilność)

```
Implementacja: 1 - mean(instability_i)
               instability_i = fan_out_i / (fan_in_i + fan_out_i)
               (metryka Martina, "Instability" z Agile Software Development)
Waga w AGQ v1: 0.55  (dominująca)
Waga w AGQ v3c: 0.20  (equal weights — Java)
Zakres:        [0.0, 1.0]
```

**Co mierzy:** czy moduły mają właściwy balans między tym ile zależą od innych (fan-out) a ile inne zależą od nich (fan-in). Wysoka S = moduły mają dużo incomingów (są "stabilne" bo inni od nich zależą).

**JAVA-S EXPERIMENT FINDING (kwiecień 2026, GT n=29):**

S jest najsilniejszym pojedynczym predyktorem jakości architektury w Javie.

```
S alone:  partial_r = 0.570, p = 0.001 ***  (kontrola nodes)
Bez S:    partial_r spada do 0.274 (ns)     → S jest niezbędne
S weight vs partial_r: Spearman r = 1.00   → perfect monotonic
```

**Mechanizm:** S mapuje na **Martin's Stability Index** — Java pakiety z konwencją
hierarchii (com.example.domain → com.example.app → com.example.infra) tworzą
warstwową strukturę, którą S naturalnie rejestruje. POS repos mają średnią S ≈ 0.38,
NEG repos S ≈ 0.13 — duża separacja.

**Cross-validation z Jolak et al. (2025):** Jolak analizowali smelle architektoniczne
w 8 projektach Java (378 wersji). Ich finding: "Unstable Dependencies" (oparte
na metryce Martina) to NAJCZĘSTSZY smell, obecny we WSZYSTKICH 8 projektach.
To niezależnie potwierdza dominację sygnału stabilności w Javie.

**Wcześniejsze obserwacje na małej próbie (GT n=10, marzec 2026):**

*UWAGA: Poniższe obserwacje opierały się na n=10 i zostały unieważnione*
*przez Java-S experiment (n=29). S wyglądało na ślepe bo próba była za mała.*

Na n=10 obserwowano paradoks: library (Panel=8.50) S=0.181, struts (Panel=2.50)
S=0.212. Na pełnym n=29 paradoks znika — S jest jednoznacznie POS > NEG.

**Typowe wartości (GT n=29, kwiecień 2026):**
- Java POS (n=15): S mean = 0.38, range 0.16–0.99
- Java NEG (n=14): S mean = 0.13, range 0.07–0.17
- Mann-Whitney POS vs NEG: p = 0.001 ***
- Python OSS: S mean ≈ 0.30 (mniejszy sygnał — brak deep package convention)

---

### C — Cohesion (Kohezja)

```
Implementacja: 1 - mean(LCOM4_i - 1) / max_lcom4_normalized
               LCOM4 = Lack of Cohesion in Methods (wariant grafowy)
               LCOM4=1 → klasa spójna; LCOM4>1 → klasa rozspójona (można podzielić)
Waga w AGQ:    0.05  (najniższa)
Zakres:        [0.0, 1.0]
```

**Co mierzy:** czy metody wewnątrz klas operują na wspólnych polach (spójna klasa) czy są ze sobą niepowiązane (kandydat do podziału). Dostarczany przez parser Rust — wymaga informacji o metodach i polach.

**Uwaga implementacyjna:** Jeśli parser nie może wyciągnąć LCOM4 (np. dla niektórych języków), C=0.5 (neutral). Stąd C często "działa" tylko dla Javy i Kotlina.

**Typowe wartości:**
- DDD library: C=0.372 (najwyższe w datasecie — rich domain objects)
- IDDD_Samples: C=0.103 (niskie — duże klasy z wieloma metodami)
- Mann-Whitney p=0.257 ns na GT n=10

---

### CD — Coupling Density (Gęstość Sprzężeń) [AGQ v2, E2]

```
Implementacja: 1 - clip(edges/nodes / CD_REF, 0, 1)
               CD_REF = 6.0  (95. percentyl Java OSS, iter6, n=147)
Waga w AGQ v2: 0.20
Zakres:        [0.0, 1.0]  (wyższe = lepiej = mniej sprzężeń na moduł)
```

**Co mierzy:** ile krawędzi (importów/zależności) przypada na jeden węzeł (pakiet). Niski ratio = sparse dependencies = dobra architektura. Wysoki ratio = każdy pakiet zależy od wielu innych = spaghetti.

**Interpretacja:**
- CD = 1.0 → ratio=0 (izolowane moduły — nierealistyczne)
- CD ≈ 0.55 → ratio≈2.7 (DDD pozytywne: dddsample=0.531, library=0.554)
- CD ≈ 0.28 → ratio≈4.3 (apache/struts=0.278)
- CD ≈ 0.20 → ratio≈4.8 (Stirling-PDF=0.197)

**Empiryczna walidacja (GT n=10, kwiecień 2026):**
- Mann-Whitney pos vs neg: p=0.010 **
- Spearman r(CD, Panel): r=+0.630, p=0.051 ns (blisko progu)
- Partial Spearman | nodes: r=−0.697 * (przeżywa kontrolę rozmiaru)

**Uwaga o bias:** CD może preferować DDD (luźne warstwy → niski ratio) nad innymi dobrymi architekturami. Wymaga walidacji na non-DDD pozytywnych repo.

---

## AGQ v2 — formuła eksperymentalna

```
AGQ_v2 = 0.20·M + 0.20·A + 0.35·S + 0.05·C + 0.20·CD

Zmiana względem v1:
  S: 0.55 → 0.35  (zredukowane — S ślepe na DDD hierarchy)
  CD: 0.00 → 0.20  (dodane — edges/nodes ratio, E2 kwiecień 2026)
```

**Wyniki na GT n=10 (kwiecień 2026):**

| Test | AGQ v1 | AGQ v2 | Zmiana |
|---|---|---|---|
| Mann-Whitney p (pos vs neg) | 0.038 * | **0.010 \*\*** | lepiej |
| Spearman r (Panel) | +0.661 * | **+0.746 \*** | lepiej |
| Partial r \| nodes | +0.564 ns | **+0.721 \*** | **przełom** |

**Status:** eksperymentalny — wymaga walidacji na non-DDD pozytywnych repo (n>30).

---

## AGQ v3c — current best (kwiecień 2026)

```
Java:   AGQ_v3c = 0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD
Python: AGQ_v3c = 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score

Zmiana względem v2 (Java):
  S: 0.35 → 0.20  (rozłożone równomiernie)
  C: 0.05 → 0.20  (C ma partial_r=0.398 p=0.032 — drugi najsilniejszy)
  Equal weights via PCA-informed justification
```

**Java-S Experiment (GT n=29, 3 iteracje, 13 wariantów):**

| Test | AGQ v2 | AGQ v3c | Zmiana |
|---|---|---|---|
| Mann-Whitney p (pos vs neg) | 0.001 *** | **0.001 \*\*\*** | równe |
| Partial r \| nodes | +0.675 ** | **+0.675 \*\*** | równe |
| Bootstrap 95% CI | [0.35, 0.88] | **[0.35, 0.88]** | równe |

**Dlaczego v3c a nie v2:** v3c wygrywa na balansie — żadna składowa nie dominuje.
Wszystkie warianty z większym S osiągają wyższe partial_r (monotonic r=1.00),
ale różnice są w obrębie bootstrap CI. V3c jest bezpieczniejszy jako default.

**Stop criterion:** Iteracja 3 zatrzymana — wszystkie warianty w CI v3c,
brak improvement > uncertainty. 2 kolejne iteracje bez poprawy.

**Rezerwa:** S15_C25_CD20 (M=0.20, A=0.20, S=0.15, C=0.25, CD=0.20)

---

## Fingerprints architektury

Klasyfikacja automatyczna na podstawie AGQ składowych:

| Fingerprint | Warunki | Interpretacja |
|---|---|---|
| **CLEAN** | AGQ ≥ 0.70, A ≥ 0.95, S ≥ 0.70 | Wzorcowa architektura |
| **LAYERED** | AGQ ≥ 0.60, M ≥ 0.60, A ≥ 0.90 | Dobra struktura warstwowa |
| **LOW_COH** | C < 0.20, S może być dowolne | Niska kohezja klas — typowe dla Java DDD (!) |
| **TANGLED** | A < 0.90 lub wiele cykli | Splątane zależności, cykle |
| **FLAT** | M < 0.35, brak hierarchii pakietów | Brak struktury — typowy dla AI-generated code |

**Uwaga krytyczna:** Java DDD (dddsample, IDDD, library) ma fingerprint LOW_COH mimo bycia wzorcową architekturą. LOW_COH ≠ zła architektura w kontekście Java DDD.

**Cohen's d (FLAT vs CLEAN):** d=4.05 *** — AGQ bardzo skutecznie odróżnia FLAT od CLEAN. Główne zastosowanie: detekcja kodu AI-generated.

---

## Ground Truth — rodzaje i jakość

### BLT — Bug Lead Time

```
BLT = mean(data_zamknięcia_buga - data_otwarcia_buga)  [dni]
Filtr: BLT > 0 (wyklucz natychmiastowe zamknięcia — artefakty)
Filtr: BLT ≤ 365 (wyklucz stare zaległe issue)
```

**Problem:** BLT mierzy kulturę procesu (CI/CD, review, team size) — nie architekturę.  
Po oczyszczeniu: r(AGQ→BLT≤7d) = −0.125 ns (było −0.217* z artefaktami BLT=0).

### Panel Ekspertów (aktualny GT)

```
PANEL_SCORE = (Robert + Martin + Vaughn + Mark) / 4
Skala: 0–10
Próg pozytywny GT: ≥ 7.0, σ < 2.0
Próg negatywny GT: ≤ 3.5, σ < 2.0
Wyklucz jeśli:     σ ≥ 2.0 (eksperci się nie zgadzają)
```

Czterej eksperci symulowani przez panel v2.0 (skalibrowany na dddsample, struts, ardalis):
- **Robert** — Clean Architecture, Uncle Bob, warstwy i Dependency Rule
- **Martin** — Evolutionary Architecture, Fowler, evolvability i coupling
- **Vaughn** — DDD, Vernon/Evans, Bounded Contexts i ubiquitous language
- **Mark** — Distributed Systems, Richards, pattern correctness i granularność

### Blast Radius

```
blast_radius = pct_cross_package_fixes
             = (bugfixy dotykające >1 pakiet) / (wszystkie bugfixy)
```

Najlepszy dostępny proxy GT z git historii. r=+0.313 (teza T6, artefakty OSS-30).  
Wymaga historii commitów — nie dostępne w shallow clone.

---

## Kluczowe eksperymenty i wyniki

| ID | Eksperyment | Wynik | Status |
|---|---|---|---|
| **E1** | Stability Hierarchy Score | Hipoteza: S(domain) < S(app) < S(infra) predyktuje DDD quality | PLANOWANY |
| **E2** | Coupling Density w formule | AGQ_v2 lepszy: Mann-Whitney p=0.010**, partial r=0.721* | ZAIMPLEMENTOWANY |
| **E3** | Package Layer Classifier | Binarny: czy istnieje `domain/`, `application/`, `infrastructure/` | PLANOWANY |
| **E4** | GT n≥30 z panelem | Aktualnie: n=10 pewnych (4 pos + 6 neg) | W TOKU |
| **Grid** | Grid search wag (1771 kombinacji) | Baseline (0.20/0.20/0.55/0.05) = globalne optimum | ZAMKNIĘTY |
| **dAGQ** | dAGQ/dt jako predyktor | NIE predyktuje — stan (AGQ_now) predyktuje, zmiana nie | ZAMKNIĘTY |

---

## Wagi per język — aktualny stan

| Język | W_M | W_A | W_S | W_C | n (GT) | Status |
|---|---|---|---|---|---|---|
| **Baseline** | 0.20 | 0.20 | 0.55 | 0.05 | 558 iter6 | Używaj domyślnie |
| Python | 0.05 | 0.90 | 0.05 | 0.00 | 111 | Grid search iter6 — używaj ostrożnie |
| Java | 0.00 | 0.05 | 0.95 | 0.00 | 37 BLT | **BŁĘDNE** — kalibrowane na BLT, nie Panel |
| Go | ? | ? | ? | ? | 14 | Za mało danych |
| COBOL | 0.15 | 0.10 | 0.45 | 0.10 | 31 | Prototyp (+ PC_copy=0.20) |

**Krytyczna uwaga:** Wagi Java (S=0.95) z grid search na BLT są gorsze na GT panelu (r=+0.587 ns) niż baseline (r=+0.661*). Nie używaj Java-specific wag dopóki GT n<150 per język.

---

## Dane i pliki

### Sandbox (/tmp/)

| Plik | Zawartość | n |
|---|---|---|
| `iter6_checkpoint.jsonl` | Surowe dane iter6 | 569 rekordów |
| `iter6_filtered.json` | Po filtrach BLT>0, ≤365, nodes≥10 | 237 repo |
| `gt_clean.json` | GT dataset z panelem — wszystkie repo | 19 repo |
| `gt_agq_v2.json` | GT z AGQ_v1 i AGQ_v2 porównaniem | 19 repo |
| `gt_panel_results.json` | Oryginalne oceny panelu (7 repo) | 7 repo |
| `agq_trajectories/` | Jolak et al. — 8 projektów × 533 punkty | 4264 pkt |
| `l4j_merged_pcdl.json` | light-4j PC/DL ground truth | n=82 |
| `cobol_agq_results.json` | AWS CardDemo COBOL | 31 programów |

### Repo (`artifacts/`)

| Plik | Zawartość |
|---|---|
| `agq_oss30_ground_truth.json` | OSS-30: 29 Python repo, blast_radius GT |
| `agq_churn_analysis_v3.json` | 74 Python repo, AGQ vs churn (wszystkie ns) |
| `agq_weight_calibration.json` | Stary artefakt — wagi pod churn (A=0.73) — **nie używaj** |

---

## Literatura kluczowa

| Skrót | Pełne odniesienie | Zastosowanie w projekcie |
|---|---|---|
| **Jolak 2025** | Jolak et al. — architectural smells vs technical debt, 8 Java projects, 533 snapshots | Zewnętrzna walidacja AGQ: r(AGQ,DL)=−0.751*** |
| **Martin** | Robert C. Martin — "Agile Software Development", Instability metric | Podstawa metryki S (fan-in/fan-out) |
| **Evans 2003** | Eric Evans — "Domain-Driven Design" | Wzorzec oceny panelu (DDD Bounded Contexts) |
| **Vernon 2013** | Vaughn Vernon — "Implementing DDD" | Referencja dla IDDD_Samples |
| **Newman Q** | Newman & Girvan 2004 — modularity in networks | Podstawa metryki M |
| **LCOM4** | Hitz & Montazeri 1995 — graph-based LCOM | Podstawa metryki C |

---

## Znane pułapki i błędy do unikania

### 1. Wnioskowanie z małej próby

```
n < 30 → żadne p-value nie jest pewne
n < 10 → nie liczyć korelacji
Aktualnie: n=10 pewnych GT → wyniki kierunkowe, nie ostateczne
```

### 2. Size confound

Większe projekty mają inny profil AGQ niż małe. Zawsze sprawdzaj:
```python
# Partial Spearman | nodes — obowiązkowe przy n>15
r_partial = spearman(residuals(metric, nodes), residuals(panel, nodes))
```
OsmAnd (6831 nodes) i OpenMetadata (5017) — wykluczone z GT ze względu na size outlier.

### 3. Multi-module repos

`ityouknow/spring-boot-examples` — 87 sub-modułów sklejonych przez QSE w jeden graf.  
Symptom: nodes/pliki Java = sensowne, ale architektura to agregat snippetów.  
Fix: sprawdzaj liczbę `pom.xml` lub `build.gradle` przed includowaniem.

### 4. Java DDD bias

Java DDD ma AGQ ≈ 0.44–0.50 mimo bycia wzorcową architekturą (Panel=7.5–8.5).  
Nie interpretuj niskiego AGQ dla Java DDD jako złej architektury.  
Sprawdź: czy repo ma pakiety `domain/`, `application/`, `infrastructure/`?

### 5. BLT=0 artefakty

53 repo w iter6 miało BLT=0 (natychmiastowe zamknięcie issue).  
To nie architektura — to boty zamykające spam lub pomyłkowe labele.  
Filtr obowiązkowy: `BLT > 0`.

### 6. Wagi skalibrowane na złe GT

`agq_weight_calibration.json` w artefaktach ma A=0.73 (churn-optimal).  
Churn nie koreluje z architekturą (r≈0, wszystkie ns, n=74).  
→ Ten artefakt jest historyczny — nie używaj do kalibracji.

---

## AGQ v2 — walidacja na n=13 (DDD + non-DDD, kwiecień 2026)

### Wyniki z rozszerzonym GT (4 DDD-pos + 3 nonDDD-pos + 6 neg)

| Metryka | r_raw | p | r_partial\|nodes | p_partial |
|---|---|---|---|---|
| **AGQ_v2** | +0.723 | 0.005 ** | **+0.599** | **0.031 \*** |
| AGQ_v1 | +0.588 | 0.035 * | +0.341 | 0.255 ns |
| CD (coupling density) | +0.623 | 0.023 * | **+0.604** | **0.029 \*** |
| S (stability) | +0.409 | 0.165 ns | +0.165 | 0.590 ns |
| ratio (edges/nodes) | −0.623 | 0.023 * | −0.604 | 0.029 * |

### Test biasu CD względem DDD

```
DDD-pos ratio:    mean=2.62  [2.08–2.89]
nonDDD-pos ratio: mean=2.32  [1.60–2.71]
NEG ratio:        mean=3.89  [3.23–4.82]

Mann-Whitney DDD vs nonDDD: p=0.400 → brak istotnego biasu CD na DDD
Mann-Whitney nonDDD vs NEG: p=0.024 * → CD odróżnia non-DDD od negatywnych
```

**Wniosek:** CD nie jest biased na DDD. non-DDD pozytywne (hexagonal, CQRS-lite,
layered) mają podobny ratio jak DDD (mean 2.32 vs 2.62, p=0.40 ns).
AGQ_v2 zachowuje p<0.05 po kontroli rozmiaru — wynik jest generyczny, nie DDD-specyficzny.

---

## flat_score — metryka Python-specific (E6, kwiecień 2026)

```
flat_score = 1 - flat_ratio
flat_ratio = (liczba węzłów z depth <= 2) / (wszystkie węzły wewnętrzne)
depth = liczba segmentów pakietu (bez nazwy klasy)

Zakres:  [0.0, 1.0]  — wyższy = lepszy (więcej hierarchii)
Java:    zawsze ~1.0 (konwencja com.company.app.domain.model = depth≥4)
Python:  różnicuje — flat spaghetti → 0.0, dobrze warstwowe → 0.7-0.9
```

**Empiryczna walidacja (Python GT n=23, kwiecień 2026):**
- pos_mean=0.665  neg_mean=0.311  Δ=+0.354
- Mann-Whitney p=0.017 *
- Spearman r=+0.549 p=0.007 **
- Partial Spearman | nodes: r=+0.443 p=0.034 *

**Wzorce:**
- youtube-dl: flat_score=0.000 (895/895 węzłów w depth≤2) — FLAT SPAGHETTI
- saleor:     flat_score=0.936 (64/3763 węzłów w depth≤2) — DOBRZE WARSTWOWE
- buildbot:   flat_score=0.946 ALE panel=2.75 — LEGACY MONOLITH (flat_score nie wykrywa!)

**Ograniczenie:** wykrywa brak hierarchii namespace, ale nie wykrywa złej architektury
z głęboką hierarchią (buildbot, Medusa). Dwa różne typy złej architektury Pythonowej.

## Stan algorytmu AGQ — kwiecień 2026 (aktualizacja finalna)

### Formuły

```
AGQ_v1  = 0.20·M + 0.20·A + 0.55·S + 0.05·C                       [baseline]
AGQ_v2  = 0.20·M + 0.20·A + 0.35·S + 0.05·C + 0.20·CD             [E2, kwiecień 2026]
AGQ_v3c (Java)   = 0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD   [PCA equal weights]
AGQ_v3c (Python) = 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score
```

### Walidacja końcowa (GT Java n=14, Python n=23)

| Metryka | Java MW p | Java partial r | Python MW p | Python partial r | Zgodność |
|---|---|---|---|---|---|
| AGQ_v2  | 0.001 ** | +0.675 ** | 0.077 ns | −0.284 ns | ODWROTNY ✗ |
| AGQ_v3c | 0.001 ** | +0.675 ** | 0.045 *  | +0.460 *  | ZGODNY ✓ |
| flat_score | — (brak wariancji) | — | 0.017 * | +0.443 * | Python only |

### Otwarte problemy

1. **Legacy monolith bez flat namespace** (buildbot, Medusa) — niewidoczny dla żadnej metryki
2. **Go** — brak GT, brak walidacji wag
3. **n zbyt małe** — Java n=14, Python n=23 → wyniki kierunkowe, nie ostateczne (cel: n≥30 per język)
4. **flat_score brak wariancji dla Javy** — potrzeba innej metryki hierarchii dla Javy
   (NS_depth jest kandydatem: partial r=+0.698** Java)
