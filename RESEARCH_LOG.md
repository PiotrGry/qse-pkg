# QSE Research Log — Pełna historia badań

> Ostatnia aktualizacja: 14 kwietnia 2026
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

## 2. Faza eksploracyjna (luty–marzec 2026)

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

### Kluczowe eksperymenty wczesne
- **E1** (Stability Hierarchy): namespace_depth nie koreluje z jakością
- **E2** (Coupling Density): CD w AGQ_v2 poprawia dyskryminację pos/neg
- **E4** (Python GT): pierwsze 20 repo Python — AGQ_v2 działa na Python
- **E5** (Namespace Metrics): NSdepth, NSgini — słabe predyktory
- **E6** (flatscore): wykrywanie "Type 1 flat spaghetti" — repo z płaską strukturą

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
