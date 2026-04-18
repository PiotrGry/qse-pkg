# QSE/AGQ Memory

## Aktualny stan projektu (2026-04-18, post repo scan + eng review)

### Branch
- Active: `fix/metrics-redesign` (225 commits ahead of main)
- 130852+ insertions / 36131− (większość: experiment data JSON, nie kod)
- 1 untracked: `TODOS.md` (wymaga commit)

### TRL + Grant
- **TRL 4 (grant V7 lock-in, marzec 2026)** — NIE TRL 3 jak było zapisane wcześniej
- Grant FENG SMART **5.1M PLN** (V7 budget, wariant 70/30 BI/PR), NIE 4M
- 4 WP (BR1-BR4), Miesiąc 1-24, TRL 4→5→6→6→7
- KPI-01 (WP-BR1): r_s(AGQ, expert) ≥ 0.60 on N≥50 repos × 3 architektów
- KPI-04 (WP-BR2): r(ΔAGQ, defect_rate) ≥ 0.55 DoE n≥250

### Krytyczny kontekst — recenzja 2026-04-16
Dokument: `docs/recenzja_2026-04-16.md`
- §1.1: AGQ brak aksjomatycznego fundamentu
- §1.2: Louvain modularity — category error na directed graphs
- §1.3: Stability invariant pod direction reversal + renaming
- §1.4: **Archipelago effect ρ=−0.900** między E/N ratio a AGQ (AGQ może mierzyć głównie graph sparsity)
- §2.1: Ground truth circular (persony = 1 researcher)
Eksperyment E13g (najnowszy) PRZECIWDZIAŁA §1.4: newbee-mall refaktoryzacja NEG→POS (AGQ 0.493→0.639, Panel 2.5→5.7). Pattern = Layer 1 wymaga głębokiej pracy, Layer 2 (PCA/SCC) łapie lżejsze zmiany.

### Repo struktura
- **Rust qse-core**: 1241 linii (9 rs). `qse-core/src/scanner/universal.rs` (825), 4 metryki (56-109 each)
- **PyO3 bindings**: `qse-py/src/lib.rs` (93). Export: `scan_and_compute_agq`, `scan_classes`
- **Python qse/**: 6879 linii, 32 plików. Najgrubsze: `graph_metrics.py` (1329), `archtest.py` (665), `cli.py` (506)
- **Testy**: 13 plików, 3088 linii. Memory mówi 149 testów ~0.6s (niezweryfikowane post branch)
- **Docs**: `docs/qse-wiki/` = Obsidian vault (133 MD, 12 numbered dirs)
- **Artifacts**: 146 plików (42 MD + 93 JSON), 5.5M
- **CI**: 5 workflowów (chaos do konsolidacji — T1)

### Decyzja projektowa: DDD OUT of main flow (2026-04-18)
- User statement: "DDD ma nie wchodzic w projekt a przynajmniej nie w głównym nurcie"
- Rationale: DDD psuje metryki jako imposed-by-design pattern
- Stan (2026-04-18):
  - `templates/ddd_scaffold/` → `_obsolete/` ✅
  - `scripts/trl4_gate.py` (9-line stub dup) → `_obsolete/` ✅
  - `qse/presets/ddd/__init__.py` — deprecation notice added ✅
  - `qse/presets/ddd/` (10 plików) — **nadal w miejscu** bo importowany przez `qse/cli.py:9-11`, `qse/trl4_gate.py:21-22`, 3 testy, 1 script (blast radius)
  - T6 w TODOS.md: Sprint 0 decouple + physical move
- Detectors (`qse/detectors.py` — universal detect_data_only/god_class/dead_class) — zostają, caller-filter pattern

### Decyzja produktowa: AI-Drift Firewall
Design doc: `~/.gstack/projects/PiotrGry-qse/pepus-fix-metrics-redesign-design-20260418-173938.md`
- Product thesis: nie "lepsza metryka jakości", tylko "containment system" na drift architektoniczny z AI-generated kodu
- 3 nazwane reguły: CYCLE_NEW, LAYER_VIOLATION, BOUNDARY_LEAK
- **Strategiczne repositioning (post eng review + Codex cold read):** AGQ = ADVISORY (KPI-01 research zachowane), Rules = BLOCKING
- Sprint 0 = 1 tydzień surface redesign (NIE 2-3 dni polish jak początkowo): decouple DDD, resolve `qse gate` collision, consolidate 5 workflowów, base-graph materialization for Δ mode, SCC delta engine

### Critical gaps (blokujące Sprint 0)
1. **Base-graph materialization substrate** — qse-gate.yml restores tylko scalar AGQ baseline, nie graph. Δ mode wymaga dwóch checkoutów + cached graphs + merge-base strategy.
2. **Rename-aware node identity** — file rename ≠ "removed old + added new" dla CYCLE_NEW detection.
3. **Counterexample structural limitation** — Event Bus / CQRS saga / plugin systems mają intencjonalne cykle. Bez edge typing (T3) są structural false positives, nie QA gaps.

### 11 Known Limitations (L1-L11, kwiecień 2026) — stan z `docs/qse-wiki/11 Research/Limitations.md`

Pełna lista znanych ograniczeń AGQ (self-acknowledged przez zespół, poza recenzją z 2026-04-16):

- **L1 Language bias** — raw AGQ incomparable cross-language (Java ≠ Python ≠ Go). Mitigation: AGQ-z percentile. Go n_GT=0.
- **L2 Small project bias** — <50 nodes unreliable, neutral/inflated scores.
- **L3 OSS-Python calibration bias** — wagi skalibrowane na OSS, może nie generalizować do enterprise Python.
- **L4 No industrial validation** — nie testowane na real enterprise code. WP-BR4 ma to rozwiązać.
- **L5 Simulated panel** — 4 persony zdefiniowane przez 1 researcher (recenzja §2.1). WP-BR1 ma rozwiązać via 3 external architects.
- **L6 No prediction** — AGQ mierzy current state, nie forecast.
- **L7 Parser limitations** — TypeScript 73% nodes=0 w benchmark 558 (parser bug).
- **L8 (KRYTYCZNE, kwiecień 2026)** — **S gameable przez sam rename namespace.** newbee-mall: `ltd.newbee.mall.*` → `mall.*` dało +0.38 S bez zmiany zależności. Cosmetic repackaging pomogło label transition NEG→POS.
- **L9 (kwiecień 2026)** — **M pompable przez martwe interfejsy.** newbee-mall: 4 nieimplementowane interfejsy = +0.02 M. 20% wagi (AGQ) na metryce z dead-pattern gaming.
- **L10 (kwiecień 2026)** — **LCOM4 penalizuje Java interfaces.** Interface z n metodami i 0 shared state → LCOM4 = n (max). Well-designed Java interface (rich contract) scoruje gorzej niż god class. Cohesion niewiarygodne dla Javy.
- **L11 (kwiecień 2026)** — **Panel formula zawyża delty 8×.** E13g newbee-mall: hardcoded formula dała Δ=+3.2, honest independent architect assessment Δ=+0.4. Panel to regression-fit function, nie expert consensus.

### PILOT counter-evidence (`papiers/PILOT_RESULTS_FINAL.md`)

12 runs (4 models × 3 feedback modes), 10 e-commerce specs per model:

| Metric | QSE feedback | None | Random feedback |
|---|---|---|---|
| Total pass rate | **18/36 (50%)** | 22/40 (55%) | **26/39 (67%)** |
| Convergence (improvement rate on retry) | 18/24 (75%) | 15/23 (65%) | 15/23 (65%) |

- **QSE feedback UNDERPERFORMS random** w immediate pass rate (Fisher's p=0.34 NS overall)
- **Tylko Claude Sonnet 4 pokazuje istotny sygnał** (convergence p=0.012)
- **Qwen: 3 API errors z QSE feedback** vs 0 z None/Random (QSE prompts za długie)
- **H3 grant ("ratchet reduces review by ≥70%") ma kontrsygnał** w tym piloci. Wymaga multi-turn refinement albo lepszego filtering violations (v2 detector ~84% precision).

### E11 BREAKTHROUGH finding (docs/qse-wiki/05 Experiments/E11*.md)

**`2×rank(C) + rank(S)` bije ważony AGQ composite o +51% w Spearman correlation:**
- rank(C) + rank(S): ρ=0.41, p=0.0025, AUC=0.757 (cross-repo GT Java n=52)
- 2×rank(C) + rank(S): ρ=0.45, p=0.0007 (E13b refinement)
- AGQ v3c (ważony): ρ=0.27, p=0.05

**Grant KPI-01 (r≥0.60) — AGQ NIE osiąga progu; rank(C)+rank(S) bliżej ale nadal poniżej.**

**Wiki rekomendacja (E11 Final Comparison, April 2026):** "Use component-level dashboard, not single composite. AGQ-composite ranks weakly across repos. Use rank-based aggregation or components separately."

### Fundamentalna tensja: cross-repo vs within-repo

| Metryka | Cross-repo ρ | Within-repo ρ | Verdict |
|---|---|---|---|
| **M (Modularity)** | ns (p=0.226) | **+0.79 (p<0.001)** | dominuje w ramach repo, martwe cross-repo |
| **C (Cohesion)** | +0.31 (p=0.03) | flat | dominuje cross-repo |
| **S (Stability)** | +0.26 (p=0.06) | ~0.00 we wszystkich iter | cross-repo signal, martwe in-repo |
| rank(C)+rank(S) | **+0.41** (p=0.0025) | n/a | best cross-repo ever |
| AGQ v3c composite | +0.27 | +0.35 (p=0.15 NS) | kompromis — nigdzie nie best |

**Konsekwencja dla produktu:** AGQ jako single blocker score = sub-optymalne. Rules (deterministic axiom-backed) + component dashboard (research-grade) > AGQ-as-blocker.

### Archipelago effect — Pilot-2 Multi-Repo Scan findings

15 repozytoriów (5 expected-GOOD, 5 MIXED, 5 expected-BAD):
- expected-BAD mean AGQ = **0.630** (wyższe!)
- expected-GOOD mean AGQ = **0.475**
- ρ(AGQ, E/N ratio) = **−0.900**, p<0.0001
- **5/5 blind spots** — AGQ failed wszystkie expected-BAD repos (TheAlgorithms, Baeldung, tutorial collections)

Mitigation zaimplementowana: archipelago detector cc_ratio > 0.08 → warning, 0 false positives na 22 repos. Ale **status integracji w CLI niejasny** (wiki mówi że detector istnieje, ale czy archtest auto-flags?).

### AGQ metryki stan
- Layer 1: Modularity (Louvain), Acyclicity (Tarjan), Stability (Martin), Cohesion (LCOM4)
- Layer 2: PCA weights, dip_violations, largest_scc (E12b QSE Dual Framework)
- Layer 3: AGQ-z (percentile), Fingerprint (7 wzorców), CycleSeverity, ChurnRisk, AGQ-adj
- E11 BREAKTHROUGH: `rank(C) + rank(S)` prosta suma rang bije ważony kompozyt
- S mechanism (Java): partial_r=0.570 p=0.001 (Java-S pilot, kwiecień 2026)

### Architektoniczne rdzenie
- AGQ jest **architecture-agnostic** — mierzy graf, nie pattern (zgodne z użyciem jako "AI-drift" signal)
- DDD był opcjonalnym presetem — teraz TO DEPRECATE (patrz T6)
- Level 1 = zero-config, czyste metryki grafowe
- **Level 2 (Policy-as-a-Service)** — `qse/discover.py` + future `qse/gate.py` rules (CYCLE_NEW, LAYER_VIOLATION, BOUNDARY_LEAK)
- LLM NIGDY w scoring path (AI pre-scoring: classifier, post-scoring: rekomendacje)
- Rust scanner (qse-core) — 25-30× szybszy od Pythona, primary engine
- Python scanner (qse/scanner.py) — ZOSTAJE jako fallback (memory prior twierdził że usunięty — błąd)

## Kluczowe pliki memory (stan 2026-04-18)

- `feng_smart_br_input.md` — pełny wsad B+R, 1370 linii (stan marzec 2026, do update dla V7 budget 5.1M)
- `research_thesis.md` — teza, paradoks Sabra, benchmarki
- `market_analysis.md` — rynek, konkurencja, sizing
- `agq_metrics_explained.md` — metryki jak dla 5-latka
- `sources_analysis.md` — analiza źródeł naukowych

## Zewnętrzne artefakty

- **Design doc (office-hours)**: `~/.gstack/projects/PiotrGry-qse/pepus-fix-metrics-redesign-design-20260418-173938.md`
- **Test plan (eng-review)**: `~/.gstack/projects/PiotrGry-qse/pepus-fix-metrics-redesign-eng-review-test-plan-20260418-190700.md`
- **TODOS.md**: 6 items (T1-T6), untracked

## Decyzje produktowe (2026-04-18, zatwierdzone)

1. Sprint 0 scope: 1 tydzień surface redesign, nie 2-3 dni polish
2. AGQ advisory, Rules block (Codex + office-hours recommended, user accepted)
3. CYCLE_NEW jako SCC-delta engine, nie constraint dispatch
4. Config format: qse-gate.toml (TOML, nie JSON/YAML)
5. Telemetry: JSONL per-run artifact + optional webhook (5s timeout)
6. Two-scan Δ mode od Sprint 0 (pod warunkiem base-graph substrate)
7. Counterexample testbed jest CRITICAL przed Sprint 0 ship
