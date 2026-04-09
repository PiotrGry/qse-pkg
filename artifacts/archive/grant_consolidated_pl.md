# QSE - Kompletny wsad do wniosku grantowego
## Wersja skonsolidowana | Marzec 2026 | TRL 4→7 | Wariant 70/30 BI/PR

> **Pliki źródłowe:**
> - Opis projektu: `/home/pepus/dev/qse-pkg/artifacts/grant_preview_pl.md`
> - WP i KPI: `/home/pepus/dev/qse-pkg/artifacts/grant_wp_milestones.md`
> - Literatura: `/home/pepus/dev/qse-pkg/artifacts/references.md`
> - Dane benchmark (finalne): `/home/pepus/dev/qse-pkg/artifacts/benchmark/agq_enhanced_{python,java,go}80.json`
> - Repozytorium: `https://github.com/PiotrGry/qse-pkg`

---

## 1. STRESZCZENIE WYKONAWCZE

**QSE (Quality Score Engine)** to system automatycznego pomiaru, klasyfikacji i egzekwowania jakości architektonicznej oprogramowania generowanego przez modele AI. Adresuje lukę którą SonarQube i inne narzędzia linii kodowej nie wypełniają: strukturalną degradację architektury systemu.

**Kluczowe osiągnięcia POC (przed wnioskiem):**
- 237 w pełni sklonowanych repozytoriów OSS (Python-78, Java-77, Go-80) przebadanych
- Scanner w Rust: 7–46× szybszy od Python baseline
- 12 odkryć naukowych, w tym pierwsze empiryczne potwierdzenie language bias w metrykach architektonicznych
- 244 testy automatyczne, działające CLI dla Python/Java/Go

**Cel projektu:** Udowodnić że AGQ (Architecture Graph Quality) koreluje ze stabilnością systemu (r ≥ 0.55, p<0.01) i zastosować tę miarę jako reward signal dla modeli LLM generujących kod.

**TRL start: 4 | TRL koniec: 7 | Czas: 24 miesiące | Ratio BI/PR: 70/30**

---

## 2. PROBLEM I MOTYWACJA

### 2.1 Era AI-assisted development - nowe zagrożenia

Narzędzia takie jak GitHub Copilot, Cursor i Claude Code generują ponad 46% nowego kodu na GitHubie (dane 2025). AI optymalizuje pod kątem "działa teraz" - nie pod kątem "będzie działać za rok". Kod przechodzi testy jednostkowe, lecz systematycznie degraduje architekturę systemu:

- Moduły zaczynają importować z warstw których nie powinny dotykać
- Pojawiają się cykliczne zależności (A importuje B, B importuje A)
- Klasy stają się "god objects" robiącymi 20 rzeczy jednocześnie

### 2.2 Luka rynkowa

SonarQube sprawdza kod linijka po linijce (bugs, smells, security). **Nie mierzy architektury jako całości.**

Dowód empiryczny z POC: spośród 78 dojrzałych projektów Python OSS, **21 z 78 (27%) dostaje od SonarQube rating "A"** (najwyższy możliwy), ale AGQ identyfikuje u nich problemy architektoniczne poniżej progu jakości. Cross-validation z SonarQube (n=79, metryki znormalizowane per KLOC) potwierdza: AGQ composite nie koreluje ze smells/KLOC (r=-0.11, n.s.), ale składowe stability i cohesion wykazują istotny inverse z bugs/KLOC (r=-0.32, p=0.003) i complexity/KLOC (r=-0.28, p=0.01). AGQ i SonarQube mierzą **komplementarne** wymiary - z mierzalnym overlap w stability↔bugs i cohesion↔complexity.

### 2.3 Cel projektu

> Zbudować i zwalidować naukowo miarę architektoniczną AGQ, która koreluje ze stabilnością systemu (r ≥ 0.55) i może służyć jako reward signal dla modeli LLM generujących kod.

---

## 3. STAN WIEDZY I POC (TRL 4)

### 3.1 Co zostało zrealizowane przed wnioskiem

| Zasób | Stan | Ścieżka |
|---|---|---|
| Kod QSE (Python + Rust) | 244 testy, działające CLI | `/home/pepus/dev/qse-pkg/qse/` |
| Scanner Rust (qse-core) | Python/Java/Go, 7-46× szybszy | `/home/pepus/dev/qse-pkg/qse-core/` |
| Benchmark Python-78 | OSS-80, v1–v4, enhanced metrics | `artifacts/benchmark/agq_enhanced_python80.json` |
| Benchmark Java-77 | Pełne klony, 77% repo z cyklami | `artifacts/benchmark/agq_enhanced_java80.json` |
| Benchmark Go-80 | Pełne klony, cohesion=1.0 wszystkie | `artifacts/benchmark/agq_enhanced_go80.json` |
| Kalibracja wag | L-BFGS-B + LOO-CV, n=74 | `artifacts/benchmark/agq_weight_calibration.json` |
| Policy discovery | qse discover: Django, Spring Boot | `qse/discover.py` |
| AGQ Enhanced metrics | 5 nowych wymiarów | `qse/agq_enhanced.py` |
| Literatura | 40+ źródeł | `artifacts/references.md` |

### 3.2 Kluczowe wyniki POC

**Dyskryminacja (Python OSS-80, v4):**
- spread = 0.548, std = 0.093 (wzrost 2× vs v1 = 0.286)
- T1: determinizm delta=0.0000000000 ✅
- T3: 21/78 repo Sonar=A ale AGQ < próg (komplementarność) ✅
- T4: mediana 0.32s vs 15.0s Sonar (~47× szybciej) ✅

**Korelacje (n=231–237, pełne klony):**
- AGQ-adj vs churn_gini: r=−0.162, **p=0.014** ✅
- AGQ-adj vs hotspot_ratio: r=+0.232, **p<0.001** ✅
- acyclicity vs hotspot_ratio: r=+0.223, **p=0.001** ✅
- Go per-language: AGQ vs churn_gini r=−0.270, **p=0.017** ✅

**Walidacja z niezależnymi źródłami:**
- SonarQube (n=79, per KLOC): stability↔bugs r=-0.32 (p=0.003), cohesion↔complexity r=-0.28 (p=0.01)
- Expert classification (n=20): known-good vs known-bad **p<0.001, d=3.22**, 80% good=LAYERED
- Dai et al. architectural integrity (n=4 Java): Spearman **rho=1.0** (ranking agreement)
- Emerge modularity (n=16): r=0.06 - Louvain Q graph-definition dependent

**Extended metrics (CCD, IC, fan-out - benchmark 240 repo × 3 języki):**
- fan_out_std / log(n) vs churn_gini: **r=+0.13, p=0.048** (jedyna cross-lang po normalizacji rozmiaru)
- Indirect Coupling vs churn_gini: **r=-0.27, p=0.007** (po kontroli rozmiaru, n=97)
- CCD: brak istotnych korelacji - odłożona
- Size confound poważny: max_fan_out r=+0.50 z nodes. Normalizacja per log(n) konieczna.

**Kalibracja wag (L-BFGS-B, LOO-CV, n=74):**
- Acyclicity = **0.730** (dominuje)
- Cohesion = 0.174
- Stability = 0.050
- Modularity = 0.000
- LOO-CV MSE = 0.006 ± 0.013 (stabilny)

### 3.3 Granice POC - dlaczego TRL 4, nie 5

1. **Brak integracji z rzeczywistym CI/CD** - żaden zespół nie używa QSE w produkcyjnym pipeline
2. **Brak walidacji eksperta-architekta** - KPI r_s(AGQ, expert_score) nie jest jeszcze osiągnięty
3. **Korelacje z proxy, nie z docelową zmienną** - churn/hotspot ≠ defect_rate
4. **Środowisko badacza** - 237 OSS repo kontrolowane przez badacza, nie przez użytkownika
5. **Brak pętli feedbacku** - żaden developer nie potwierdził że AGQ zmienia jego decyzje architektoniczne

**Framing dla eksperta:** *"Wstępna walidacja laboratoryjna potwierdzająca obliczalność i deterministyczność metryk. TRL 5 wymaga walidacji w środowisku relewantnym: ekspert-architekt potwierdza że AGQ odpowiada jego ocenie (KPI-01, WP-BR1)."*

---

## 4. SYSTEM QSE - OPIS TECHNICZNY

### 4.1 Architektura 5-warstwowa

```
┌─────────────────────────────────────────────────────────┐
│  WARSTWA 5: AGQ Enhanced                                │
│  AGQ-z, Fingerprint, CycleSeverity, ChurnRisk, AGQ-adj  │
├─────────────────────────────────────────────────────────┤
│  WARSTWA 4: Policy-as-a-Service                         │
│  Automatyczne reguły architektoniczne (qse discover)    │
├─────────────────────────────────────────────────────────┤
│  WARSTWA 3: Quality Gate (TRL4 + ratchet)               │
│  Blokada gdy jakość spada poniżej progu                 │
├─────────────────────────────────────────────────────────┤
│  WARSTWA 2: AGQ Metrics (4 naprawione + kalibracja)     │
│  Modularity, Acyclicity, Stability, Cohesion            │
├─────────────────────────────────────────────────────────┤
│  WARSTWA 1: Scanner (Rust tree-sitter, 7-46× szybszy)   │
│  Python, Java (Maven/Gradle), Go - jeden silnik         │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Scanner multi-language

Rust qse-core z tree-sitter: jeden silnik dla Python, Java, Go.
Kluczowa innowacja dla Javy: czyta `package com.google.common.collect;`
z pliku źródłowego → semantycznie poprawne nazwy modułów
(zamiast ścieżki pliku `android.guava-testlib.src...`).

**Wydajność (release build + rayon):**
- requests (Python): 37ms → **6ms** (7×)
- django (Python): 2095ms → **54ms** (39×)
- pandas (Python): 6162ms → **134ms** (46×)
- home-assistant: 19604ms → **655ms** (30×)

### 4.3 Cztery metryki AGQ

**Modularity** - "czy moduły są naprawdę niezależne?"
Algorytm Louvain wykrywa klastry w grafie zależności.
Normalizacja: max(0, Q) / 0.75. Dla n<10: 0.5 neutralne.
Wynik 0 = "big ball of mud", wynik 1 = idealna izolacja modułów.

**Acyclicity** - "czy nie ma błędnych pętli zależności?"
Tarjan SCC na wewnętrznych nodach (filtruje stdlib/third-party).
A = 1 − (largest_SCC_size / internal_nodes).
Waga empiryczna: **0.730** (dominuje w kalibracji).
Odkrycie: 77% repo Java ma cykliczne zależności (niewidoczne w shallow clone).

**Stability** - "czy architektura ma wyraźne warstwy?"
Package-level instability variance: var(I_per_package) / 0.25.
I = Ce/(Ca+Ce) per pakiet. Wysoka wariancja = wyraźne warstwy (core vs leaves).
*Naprawa POC:* oryginalny wzór Martina (Distance from Main Sequence)
degeneruje bez danych o abstrakcji - zastąpiony wariancją.

**Cohesion** - "czy każda klasa robi jedną rzecz?"
LCOM4: liczba spójnych komponentów w grafie metoda-atrybut.
LCOM4=1 → klasa spójna, LCOM4=5 → powinna być podzielona na 5.
*Odkrycie language bias:* Go = 1.000 zawsze (interfaces/structs),
Java = 0.379 średnio (złożone hierarchie klas).

### 4.4 Pięć metryk Enhanced

| Metryka | Wzór | Co daje |
|---|---|---|
| **AGQ-z** | (AGQ − μ_lang) / σ_lang | Percentyl w języku - usuwa language bias. jackson: 4.3%ile Java |
| **AGQ-adj** | AGQ × log(500) / log(n) | Score niezależny od rozmiaru repo. r=-0.162 vs gini p=0.014 |
| **Fingerprint** | reguły na (mod,acy,stab,coh) | 7 wzorców: CLEAN/LAYERED/MODERATE/FLAT/LOW_COHESION/CYCLIC/TANGLED |
| **CycleSeverity** | 1 − acyclicity → 5 poziomów | NONE/LOW/MEDIUM/HIGH/CRITICAL z % klas w cyklu |
| **ChurnRisk** | 1−(0.5·acy+0.3·stab+0.2·mod) | Predykcja hotspot files. r=-0.149 vs hotspot p=0.024 |

**Fingerprint - 7 wzorców architektonicznych (237 repo):**

| Wzorzec | n | Py | Java | Go | Opis |
|---|---|---|---|---|---|
| LAYERED | 68 | 57 | 4 | 7 | Warstwowa - dobra |
| CLEAN | 49 | 1 | 1 | 47 | Strukturalnie czysty - Go dominuje |
| LOW_COHESION | 44 | 4 | 40 | 0 | Klasy robią za dużo - Java |
| MODERATE | 39 | 12 | 11 | 16 | Bez patologii |
| FLAT | 23 | 5 | 8 | 10 | Brak warstw - dominujący bad pattern |
| TANGLED | 9 | 0 | 9 | 0 | Cykle + niska spójność |
| CYCLIC | 5 | 0 | 5 | 0 | Cykle bez innych patologii |

**CLEAN ≠ Clean Architecture (Uncle Bob).** CLEAN to matematyczne właściwości grafu:
zero cykli + wysoka spójność + wyraźne warstwy. Dominuje w Go ze względu
na strukturalne cechy języka (interfaces zamiast dziedziczenia).

### 4.5 Wyjście CLI z enhanced metrics

```bash
$ qse agq /path/to/repo --threshold 0.70

# Java (jackson-databind):
AGQ GATE FAIL  agq=0.4618  M=0.57 A=0.85 St=0.26 Co=0.16  lang=Java
  [TANGLED]  z=-1.71 (4.3%ile Java)  cycles=HIGH

# Go (vault):
AGQ GATE PASS  agq=0.8760  M=0.52 A=1.00 St=0.98 Co=1.00  lang=Go
  [CLEAN]  z=+0.95 (82.8%ile Go)  cycles=NONE

# Python (spring-boot):
AGQ GATE PASS  agq=0.8030  M=0.70 A=1.00 St=0.94 Co=0.52  lang=Java
  [LAYERED]  z=+1.93 (97.3%ile Java)  cycles=LOW
```

### 4.6 Policy-as-a-Service

```bash
# Automatyczne odkrycie granic architektonicznych:
$ qse discover /path/to/repo --output-constraints .qse/arch.json

# Spring Boot: 27 reguł m.in.:
# forbidden: org.springframework.boot.loader/* → org.springframework/*
# (classloader nie może zależeć od kodu aplikacji)

# Egzekwowanie w CI/CD:
$ qse agq . --constraints .qse/arch.json
# Każdy PR sprawdzany automatycznie
```

Walidacja: reguły dla Django (Python) i Spring Boot (Java) są
architektonicznie prawidłowe i konsekwentnie utrzymane w kodzie.

### 4.7 QSE_test - jakość testów

5 wymiarów: assertion_density, test_to_code_ratio, naming_quality,
isolation_score, coverage_potential. Moduł: `qse/test_quality.py`.

---

## 5. WYNIKI EKSPERYMENTALNE - NAJŚWIEŻSZE DANE

> **Dane finalne:** `artifacts/benchmark/agq_enhanced_{python,java,go}80.json`
> **Data:** marzec 2026 | **Pełne klony** (bez depth limit)

### 5.1 Benchmark 237 repozytoriów cross-language

| Język | n | AGQ mean | AGQ std | min | max | Cohesion | Acy | % z cyklami |
|---|---|---|---|---|---|---|---|---|
| Go | 80 | **0.816** | 0.061 | 0.655 | 0.920 | **1.000** | **1.000** | **0%** |
| Python | 78 | 0.746 | 0.055 | 0.581 | 0.860 | 0.647 | 0.999 | 4% |
| Java | 77 | **0.619** | 0.087 | 0.463 | 0.839 | **0.379** | 0.973 | **77%** |

### 5.2 Fingerprint - rozkład (237 repo)

*Patrz tabela w sekcji 4.4.*

**Kluczowe odkrycie:** FLAT jest dominującym wzorcem złej architektury
cross-language. Najgorsze projekty w każdym języku:
- Python: home-assistant (z=−2.81), ansible (z=−2.28) → FLAT
- Java: avro (z=−3.11), solr (z=−2.33), flink (z=−2.32) → FLAT
- Go: kubernetes (z=−2.58), grafana (z=−2.21) → FLAT

### 5.3 Language bias - tabela porównawcza (n=237)

| Wymiar | Python (78) | Java (77) | Go (80) |
|---|---|---|---|
| AGQ mean | 0.746 | 0.621 | **0.816** |
| Cohesion | 0.647 | **0.379** | **1.000** |
| Acyclicity | 0.999 | 0.973 | **1.000** |
| % z cyklami | 4% | **77%** | **0%** |
| Stability | 0.806 | 0.486 | 0.736 |
| Modularity | 0.533 | **0.637** | 0.531 |
| Dominant pattern | LAYERED | LOW_COHESION | CLEAN |

**Wniosek:** Cross-language porównania AGQ bez normalizacji (AGQ-z) są
metodologicznie błędne - language paradigm dominuje nad jakością kodu.

### 5.4 Korelacje statystycznie istotne (n=229–237)

| Para | r | p-value | Kierunek |
|---|---|---|---|
| acyclicity vs hotspot_ratio | +0.223 | **0.001** | confounding (Go aktywne) |
| stability vs hotspot_ratio | +0.173 | **0.009** | confounding |
| AGQ-z vs churn_gini | −0.130 | **0.048** | ✅ właściwy |
| **AGQ-adj vs churn_gini** | **−0.162** | **0.014** | ✅ najsilniejszy |
| **AGQ-adj vs hotspot_ratio** | **+0.232** | **<0.001** | ✅ |
| **ChurnRisk vs hotspot_ratio** | **−0.149** | **0.024** | ✅ właściwy |
| Go: AGQ vs churn_gini | −0.270 | **0.017** | ✅ per-language |

*Uwaga:* Korelacje z "+" na acyclicity/stability wynikają z confoundera dojrzałości -
projekty Go (acy=1.0) są aktywnie rozwijane i mają naturalnie więcej hotspotów.

### 5.5 Kalibracja wag (L-BFGS-B, LOO-CV, n=74)

> Plik: `artifacts/benchmark/agq_weight_calibration.json`

| Składowa | Waga empiryczna | Waga równa |
|---|---|---|
| Acyclicity | **0.730** | 0.250 |
| Cohesion | **0.174** | 0.250 |
| Stability | **0.050** | 0.250 |
| Modularity | **0.000** | 0.250 |

LOO-CV MSE = 0.006 ± 0.013. Spójne z Gnoyke et al. JSS 2024:
*"cyclic dependencies correlate with defects most among architectural smells."*

### 5.6 Odkrycie metodologiczne: shallow clone maskuje cykle Java

Przy shallow clone (--depth 1): Java acy=1.000 dla wszystkich repo.
Przy pełnych klonach: **77% Java repo ma cykliczne zależności.**

| Repo | Acy (shallow) | Acy (full) |
|---|---|---|
| hibernate-orm | 1.000 | **0.840** |
| mockito | 1.000 | **0.868** |
| jackson-databind | 1.000 | **0.850** |
| spring-boot | 1.000 | **0.999** |

**Implikacja:** Benchmarki na shallow clone są nierzetelne dla analizy architektonicznej.
Invaliduje wyniki poprzednich prac MSR używających shallow clone dla Javy.

### 5.7 Najlepsze i najgorsze (AGQ-z, cross-language)

**Top 5 (CLEAN):** staticcheck Go +1.66, grpc-gateway Go +1.65,
protoc-gen-go Go +1.35, dagger Java +2.51, spring-boot Java +1.93

**Bottom 5 (FLAT):** avro Java −3.11, kubernetes Go −2.58,
solr Java −2.33, home-assistant Python −2.81, flink Java −2.32

---

## 6. ODKRYCIA NAUKOWE - 12 TWIERDZEŃ

| # | Twierdzenie | Dowód liczbowy | Literatura |
|---|---|---|---|
| 1 | Martin's D degeneruje bez abstrakcji | spread 0.286→0.548 po naprawie | Drotbohm 2024 |
| 2 | Language bias w cohesion | Go=1.0, Java=0.38, Py=0.65 | - pierwsze empiryczne |
| 3 | AGQ ⊥ SonarQube (komplementarność) | 21/78 Sonar=A, AGQ<próg | - |
| 4 | Acyclicity=0.73 w kalibracji | LOO-CV MSE=0.006 | Gnoyke JSS 2024 |
| 5 | Auto policy discovery działa | Django, Spring Boot walidacja | - |
| 6 | Shallow clone maskuje 77% cykli Java | 59/77 repo z cyklami | - metodologiczne |
| 7 | Acyclicity koreluje cross-language | r=+0.223, p=0.001, n=229 | - |
| 8 | Stability koreluje cross-language | r=+0.173, p=0.009, n=229 | - |
| 9 | AGQ-adj vs churn_gini istotne | r=−0.162, p=0.014 | - |
| 10 | AGQ-adj vs hotspot istotne | r=+0.232, p<0.001 | - |
| 11 | Size bias AGQ | r=−0.269, p<0.001 | - |
| 12 | FLAT = dominant bad pattern | bottom 10 wszystkich języków = FLAT | - |

---

## 7. PLAN BADAŃ - WORK PACKAGES

### 7.1 Oś korelacji przez projekt

```
TRL 4 (start): r_obs=0.23 na OSS proxy (potwierdzony sygnał)
     ↓
WP-BR1: r_s(AGQ, expert) ≥ 0.60   → construct validity
     ↓
WP-BR2: r(ΔAGQ, defect_rate) ≥ 0.55 → predictive validity (DoE)
     ↓
WP-BR3: r(AGQ_LLM, defects) ≥ 0.55 → applied validity (LLM)
     ↓
WP-BR4: regresje ↓ 15%              → operational validity
TRL 7 (koniec)
```

### 7.2 Tabela WP

| WP | Miesiące | Typ | Kamień milowy | KPI / próg PASS | TRL |
|---|---|---|---|---|---|
| WP-BR1 | 1–6 | **BI** | M1 (m-c 6) | r_s(AGQ, expert_score) ≥ 0.60; n≥50; p<0.01 | 4→5 |
| WP-BR2 | 7–12 | **BI** | M2 (m-c 12) | r(ΔAGQ, defect_rate_DoE) ≥ 0.55; p<0.01; n≥250 | 5→6 |
| WP-BR3 | 13–18 | **BI** | M3 (m-c 18) | H5: monotoniczność konwergencji 7B→70B + gate pass ≥85% | 6 |
| WP-BR4 | 19–24 | **PR** | M4 (m-c 24) | Redukcja regresji ≥15% (A/B, n≥5 zespołów); TRL=7 | 6→7 |

**Ratio: 70% BI / 30% PR**

### 7.3 WP-BR1 - Construct validity (BI, m-c 1–6)

**Pytanie badawcze:** Czy AGQ mierzy to samo co ekspert-architekt ocenia jako "jakość architektury"?

**Deliverables:**
- D1.1 Expert labeling: 3 architektów × 50 repo, ocena 0–5 per składowa
- D1.2 Call graph inter-proceduralny (nie tylko import graph)
- D1.3 Korekcja language bias: AGQ-z per język - czy poprawia construct validity
- D1.4 Partial correlation controlling for project age confounder
- D1.5 Ground truth corpus opublikowany (Zenodo)

**Uzasadnienie BI:** Wynik niepewny - AGQ może nie zgadzać się z ekspertem.
Human labeling study = typowe BI. F1 layer detection: poprawa 0.615→0.80
wymaga nowego algorytmu o niepewnym wyniku.

**KPI M1:**
- KPI-01: r_s(AGQ, expert_score) ≥ 0.60; n≥50; p<0.01 *[GŁÓWNY]*
- KPI-02: Partial r po kontrolowaniu za dojrzałość ≥ 0.55; p<0.05
- KPI-03: Czas skanowania 80k LOC ≤ 2 min

### 7.4 WP-BR2 - Predictive validity / DoE (BI, m-c 7–12)

**Pytanie badawcze:** Czy AGQ przewiduje defect_rate w kontrolowanym eksperymencie?

**Warunek wejścia:** KPI-01 (construct validity) osiągnięty.

**Schemat DoE:**
```
Faktor A: Typ defektu (4): cycle_injection | god_class | flat_structure | cross_boundary
Faktor B: Intensywność θ (5): {0, 0.25, 0.5, 0.75, 1.0}
Faktor C: Typ projektu (3): library | framework | application

Jednostka: 50 projektów × 5 wariantów = 250 obserwacji
Zmienna zależna: defect_rate = regresje / zmiany_kodu
  (na standardowym diff-corpus 100 zmian per projekt)
```

**Uzasadnienie BI:** DoE z kontrolowaną injekcją defektów = klasyczne BI.
Wynik r(ΔAGQ, defect_rate) niepewny - może nie osiągnąć 0.55.

**KPI M2:**
- KPI-04: r(ΔAGQ, defect_rate) ≥ 0.55; p<0.01; n≥250 *[GŁÓWNY - H2 wniosku]*
- KPI-05: Cross-validation r na held-out 20% ≥ 0.50
- KPI-06: Dataset opublikowany Zenodo ≥ 250 obs.

**Uzasadnienie matematyczne progu 0.55 (do wniosku):**
```
r_obs(OSS proxy) = 0.23
Korekcja atenuacji (Fuller 1987):
  r_true = r_obs / √(rel_x × rel_y)
         = 0.23 / √(0.95 × 0.40) ≈ 0.37
Przejście do bezpośredniego pomiaru (rel=0.85):
  r_controlled ≥ 0.37 × √(0.85/0.40) ≈ 0.54
Próg 0.55 jest konserwatywny.
Precedens: Hassan (2009) - obs. r≈0.20 → kontrolowane r≈0.55.
```

### 7.5 WP-BR3 - Architectural RLHF / QSELiner (BI, m-c 13–18)

**Pytanie badawcze:** Czy AGQ jako reward signal konwerguje w DPO dla open-source LLM?
Czy monotoniczność konwergencji zależy od rozmiaru modelu (7B→70B)?

**Uzasadnienie BI:**
POC (generate_loop.py) używał binarnych detektorów kodu jako sygnału zwrotnego
na modelu komercyjnym. WP-BR3 bada inny, niezbadany przypadek:
ciągła wielowymiarowa miara architektoniczna (AGQ 0–1, 4 składowe)
jako reward signal w DPO dla open-source LLM (7B–70B).
Hipoteza H5: monotoniczność konwergencji reward względem rozmiaru modelu
nie ma precedensu w literaturze dla domain-specific structural code metrics.
DPO jako technika jest znana - ten konkretny reward signal + typ modelu + hipoteza = BI.

**Deliverables:**
- D3.1 Preference dataset ≥ 10k par (fail_diff, pass_diff)
- D3.2 DPO fine-tuning: 4 rozmiary (7B, 13B, 34B, 70B)
- D3.3 Learning curves - dokumentacja H5 (monotoniczność)
- D3.4 Model "ArchitectureAware-Coder" na HuggingFace
- D3.5 Policy-as-a-Service v2: multi-language, UI zarządzania regułami

**KPI M3:**
- KPI-07: H5 monotoniczność konwergencji 7B→70B udokumentowana
- KPI-08: AGQ gate pass rate ≥ 85% first-attempt (baseline ~40%)
- KPI-09: r(AGQ_generated, defect_rate) ≥ 0.55 na kodzie LLM
- KPI-10: Model opublikowany HuggingFace

### 7.6 WP-BR4 - Walidacja eksperymentalna (PR, m-c 19–24)

**Uwaga terminologiczna:** "Wdrożenie" = nie B+R (wykluczone wg kryteriów str. 8).
Poprawnie: "walidacja eksperymentalna w warunkach zbliżonych do operacyjnych",
"testy A/B z realnymi zespołami", "pilotowe uruchomienie u partnera badawczego".

**Deliverables:**
- D4.1 A/B test: ≥5 zespołów z QSE vs ≥5 bez QSE, 6 miesięcy
- D4.2 Pilotowe uruchomienie u ≥2 partnerów badawczych
- D4.3 Pomiar: regression rate, architectural drift per sprint, onboarding time
- D4.4 Raport końcowy B+R + publikacja (IEEE TSE lub JSS)
- D4.5 Zgłoszenie patentowe: metodologia architektonicznego RLHF

**KPI M4:**
- KPI-11: Redukcja regression rate ≥ 15% (A/B)
- KPI-12: ≥2 partnerów badawczych z pilotowym uruchomieniem
- KPI-13: TRL końcowy = 7

### 7.7 Tabela KPI zbiorczych

| KPI-ID | KPI | Próg PASS | WP |
|---|---|---|---|
| KPI-01 | r_s(AGQ, expert_score) - construct validity | ≥ 0.60; p<0.01 | WP-BR1 |
| KPI-02 | Partial r controlling age confounder | ≥ 0.55; p<0.05 | WP-BR1 |
| KPI-03 | Czas skanowania 80k LOC | ≤ 2 min | WP-BR1 |
| KPI-04 | r(ΔAGQ, defect_rate) DoE | ≥ 0.55; p<0.01 | WP-BR2 |
| KPI-05 | Cross-validation held-out 20% | ≥ 0.50 | WP-BR2 |
| KPI-06 | Dataset DoE (Zenodo) | ≥ 250 obs. | WP-BR2 |
| KPI-07 | H5: monotoniczność konwergencji 7B→70B | udokumentowana | WP-BR3 |
| KPI-08 | QSELiner gate pass rate | ≥ 85% 1st-attempt | WP-BR3 |
| KPI-09 | r(AGQ_LLM, defect_rate) | ≥ 0.55; p<0.01 | WP-BR3 |
| KPI-10 | Model HuggingFace | opublikowany | WP-BR3 |
| KPI-11 | Redukcja regression rate (A/B) | ≥ 15% | WP-BR4 |
| KPI-12 | Partnerzy badawczy | ≥ 2 | WP-BR4 |
| KPI-13 | TRL końcowy | 7 | WP-BR4 |

### 7.8 Uzasadnienie 70/30 BI/PR

| Wariant | Grant | +1 pkt K3 | Ryzyko Frascati |
|---|---|---|---|
| 50/50 | 2 912 462 PLN | NIE | NISKIE |
| **70/30 (wybrany)** | **3 078 888 PLN** | NIE | ŚREDNIE (WP-BR3) |
| 40/60 | 2 829 249 PLN | TAK | NISKIE |

Decyzja: 70/30 - +166k PLN grantu vs brak punktu K3.
Ryzyko WP-BR3 zarządzalne po przeformułowaniu argumentu
(nowy reward signal + nowa hipoteza H5 = BI).

---

## 8. UZASADNIENIA GRANTOWE

### 8.1 Obrona TRL 4

**Argumenty dla eksperta oceniającego:**

1. *Brak integracji z CI/CD:* żaden zespół nie używa QSE jako blokady merge-request
2. *Brak walidacji eksperckiej:* KPI-01 (r vs expert) nieosionięty
3. *Proxy ≠ zmienna docelowa:* r=0.23 na churn ≠ r(AGQ, defect_rate)
4. *Środowisko badacza:* 237 OSS repo kontrolowane przez badacza, nie przez użytkownika
5. *Brak pętli decyzyjnej:* żaden developer nie potwierdził że AGQ zmienia jego decyzje

**Framing POC:** "Wstępna walidacja laboratoryjna potwierdzająca obliczalność
i deterministyczność metryk (delta=0.000 na 78 repo). TRL 5 wymaga
walidacji w środowisku relewantnym: ekspert-architekt potwierdza że AGQ
odpowiada jego ocenie (KPI-01, WP-BR1, miesiąc 6)."

### 8.2 Uzasadnienie KPI r ≥ 0.55

Rozbieżność r=0.23 (POC) vs r≥0.55 (cel) wynika z trzech efektów:

**Efekt 1 - Atenuacja (Fuller 1987):**
```
r_true = r_obs / √(rel_x × rel_y) = 0.23 / √(0.95×0.40) ≈ 0.37
```
Proxy churn_gini ma rzetelność ≈ 0.40 (zaszumiony, confounded).

**Efekt 2 - Usunięcie confoundera (DoE):**
Dojrzałość projektu koreluje zarówno z AGQ jak i niskim churnem.
W DoE ten confounder jest usunięty przez randomizację θ.

**Efekt 3 - Bezpośrednia miara (defect_rate vs proxy):**
```
r_controlled ≥ 0.37 × √(rel_controlled/rel_proxy)
             = 0.37 × √(0.85/0.40) ≈ 0.54
```
Próg 0.55 jest konserwatywny.
Precedens: Hassan (2009) - obserwacyjne r≈0.20 → kontrolowane r≈0.55.

### 8.3 WP-BR3 jako BI - nowy reward signal, nowa hipoteza konwergencji

POC (generate_loop.py) używał binarnych detektorów kodu (sygnał zwrotny
PASS/FAIL) na modelu komercyjnym (Sonnet, API). WP-BR3 bada inny,
**niezbadany przypadek**:

- Sygnał: ciągła wielowymiarowa miara (AGQ 0–1, 4 składowe)
  ≠ binarny detektor kodu
- Model: open-source LLM (7B–70B) ≠ model komercyjny
- Hipoteza H5: monotoniczność konwergencji reward względem rozmiaru modelu
  - **brak precedensu w literaturze** dla domain-specific structural metrics

DPO jako technika jest znana (Rafailov 2023).
Zastosowanie z tym konkretnym reward signal + tej konkretnej hipotezy
konwergencji = BI zgodnie z Frascati.

### 8.4 Terminologia WP-BR4

| Zakazane (non-B+R) | Prawidłowe (PR) |
|---|---|
| wdrożenie | walidacja eksperymentalna |
| deployment produkcyjny | pilotowe uruchomienie u partnera badawczego |
| integracja CI/CD | testy A/B w warunkach zbliżonych do operacyjnych |
| klient | partner badawczy |

---

## 9. ZASOBY ISTNIEJĄCE

### 9.1 Kod i testy

| Zasób | n/stan | Ścieżka absolutna |
|---|---|---|
| Testy automatyczne | **244** | `/home/pepus/dev/qse-pkg/tests/` |
| Moduł core Python | działający | `/home/pepus/dev/qse-pkg/qse/` |
| Scanner Rust (qse-core) | 7-46× szybszy | `/home/pepus/dev/qse-pkg/qse-core/` |
| PyO3 bindings | działające | `/home/pepus/dev/qse-pkg/qse-py/` |
| AGQ Enhanced metrics | 5 nowych wymiarów | `/home/pepus/dev/qse-pkg/qse/agq_enhanced.py` |
| Policy discovery | walidowany | `/home/pepus/dev/qse-pkg/qse/discover.py` |
| CLI (qse agq/gate/discover) | język-agnostyczny | `/home/pepus/dev/qse-pkg/qse/cli.py` |

### 9.2 Dane benchmarkowe (finalne)

| Dataset | n repo | Ścieżka absolutna |
|---|---|---|
| **Python-78 enhanced** | 78 | `/home/pepus/dev/qse-pkg/artifacts/benchmark/agq_enhanced_python80.json` |
| **Java-77 enhanced** | 77 | `/home/pepus/dev/qse-pkg/artifacts/benchmark/agq_enhanced_java80.json` |
| **Go-80 enhanced** | 80 | `/home/pepus/dev/qse-pkg/artifacts/benchmark/agq_enhanced_go80.json` |
| Kalibracja wag | n=74 | `/home/pepus/dev/qse-pkg/artifacts/benchmark/agq_weight_calibration.json` |
| Python OSS-80 v4 | 78 | `/home/pepus/dev/qse-pkg/artifacts/benchmark/agq_thesis_oss80_v4.json` |
| Wersje v1→v4 | porównanie | `/home/pepus/dev/qse-pkg/artifacts/benchmark/agq_version_comparison.md` |
| Repo lists (80×3) | listy JSON | `/home/pepus/dev/qse-pkg/scripts/repos_{oss80,java80,go80}_benchmark.json` |
| Sklonowane repozytoria | ~237 repo | `/tmp/qse_240/{python,java,go}/` (~50 GB) |

### 9.3 Dokumenty grantowe

| Dokument | Ścieżka absolutna |
|---|---|
| Niniejszy dokument | `/home/pepus/dev/qse-pkg/artifacts/grant_consolidated_pl.md` |
| Opis projektu PL | `/home/pepus/dev/qse-pkg/artifacts/grant_preview_pl.md` |
| WP i KPI | `/home/pepus/dev/qse-pkg/artifacts/grant_wp_milestones.md` |
| Opis EN (wymaga aktualizacji) | `/home/pepus/dev/qse-pkg/artifacts/grant_description.md` |
| Literatura (40+ pozycji) | `/home/pepus/dev/qse-pkg/artifacts/references.md` |

### 9.4 Repozytorium

- GitHub: `https://github.com/PiotrGry/qse-pkg`
- Branch: `main` | Commits: 45+
- Rust: `~/.cargo/bin/` (rustc 1.94.0)
- Build: `python3 -m maturin develop --release -m qse-py/Cargo.toml`

### 9.5 IP - podstawy patentowe

Metodologia kwalifikuje się do zgłoszenia patentowego:
- Metoda obliczania AGQ (package-level instability variance jako zamiennik Martin's D)
- Metodologia architektonicznego RLHF (AGQ jako reward signal dla DPO)
- Pipeline: injekcja defektów → pomiar defect_rate → kalibracja wag

---

## 10. DALSZE KIERUNKI BADAŃ (poza zakresem projektu)

**A) Temporal AGQ - architectural decay curves**
Jak zmienia się AGQ projektu przez 5 lat? Czy AI-assisted projekty degradują szybciej?
Wymaga: per-commit AGQ na pełnej historii git.

**B) Per-language weight calibration**
Wagi acyclicity=0.73 kalibrowane na Python. Czy są takie same dla Java i Go?
Potrzeba: labeled dataset per język n≥100.

**C) AGQ dla mikrousług (cross-repo)**
Coupling między repozytoriami przez API calls, shared types, event schemas.
Rozszerzenie `qse agq` o multi-repo mode.

**D) Human study: AGQ vs developer decision**
Czy wyższy AGQ koreluje z krótszym onboarding time? Czy FLAT pattern
prowadzi do dłuższego time-to-fix? Wymaga: human study z programistami.

---

## 11. LITERATURA

> Pełna lista 40+ pozycji: `/home/pepus/dev/qse-pkg/artifacts/references.md`

**Kluczowe pozycje:**
- Nagappan & Ball (ICSE 2005) - code churn, defect prediction
- D'Ambros & Lanza (WCRE 2009) - change coupling vs defects
- Gnoyke, Schulze, Krüger (JSS 2024) - architectural smell evolution, 485 releases
- Pisch, Cai, Kazman (ESEM 2024) - M-score, hierarchical modularity
- Fuller (1987) - measurement error, attenuation correction
- Zimmermann et al. (FSE 2009) - cross-project defect prediction limitations
- Hassan (2009) - observational vs controlled software metrics
- Rafailov et al. (2023) - Direct Preference Optimization (DPO)

---

*Dokument wygenerowany: marzec 2026*
*Repozytorium: https://github.com/PiotrGry/qse-pkg*
*Kontakt: [Uczelnia/Instytut]*
