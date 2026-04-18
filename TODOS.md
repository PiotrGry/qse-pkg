# TODOS — qse-pkg

Kolejka spraw odłożonych z review/sprint planning. Nie żyje w design doc'u, nie żyje w roadmapie WP, ale nie chcemy zgubić.

---

## T1: Workflow consolidation (5 → 1–2)

**What:** Zredukować liczbę workflowów w `.github/workflows/` z 5 do 1 reusable + 1 example.

**Why:** Obecnie `archtest.yml`, `archtest-example.yml`, `qse-gate.yml`, `qse-ci-example.yml`, `trl4-validation.yml` robią nakładające się rzeczy. User nie wie którego użyć. Duplikacja logiki CI. Sprint 0 consolidation dependency — bez tego nie ma jak oddeliverować clean "Use PiotrGry/qse-pkg/.github/workflows/X.yml@v1".

**Pros:** Jeden punkt wejścia dla użytkownika. Mniej kodu do utrzymania. Spójne naming.

**Cons:** Istniejące integracje (jeśli są) pękną. Trzeba napisać migration guide.

**Context:** Codex cold read (2026-04-18) zidentyfikował to jako Sprint 0 feasibility risk. `qse-gate.yml:62` restores tylko scalar AGQ baseline — nie graph baseline potrzebny dla Δ mode. Konsolidacja = dobry moment na dobudowanie base-graph materialization.

**Depends on / blocked by:** Sprint 0 rule engine extraction (qse/gate.py) musi być w miarę stabilny zanim konsolidujemy workflowy. Albo odwrotnie — konsolidacja najpierw jako równoległy sprint.

---

## T2: Command surface consolidation

**What:** Zredukować CLI commands `qse gate`, `qse trl4`, `qse agq`, `qse-archtest` do jednego canonical + aliases z deprecation warnings.

**Why:** Dziś 4 komendy reprezentują overlapping ideas. User pyta "czego mam użyć?" — nie wie. `qse gate` w [cli.py:353](qse/cli.py#L353) blokuje rename `qse/trl4_gate.py → qse/gate.py` (namespace collision). Konsolidacja albo rename wymagana.

**Pros:** Czystszy onboarding. Mniejsze zamieszanie w dokumentacji. Możliwy mniejszy kodzik.

**Cons:** Breaking change dla anyone używającego starych komend. Semantic versioning bump.

**Context:** Codex cold read flagował to jako "adding another renamed gate before consolidation makes rollout harder". Sprint 0 decyzja: nowa nazwa dla gate'u (np. `qse check` albo `qse-gate` jako osobny binary) + aliases dla starych.

**Depends on / blocked by:** Sprint 0 naming decision. Można robić równolegle z T1.

---

## T3: Edge typing dla counterexamples

**What:** Wprowadzić edge categories (sync_call, async_event, plugin_load, data_dependency) w grafie zależności. Gate traktuje cykle w zależności od typu krawędzi.

**Why:** Dziś graf zależności jest untyped — każda krawędź to "A imports B". Ale `Event Bus`, `CQRS saga`, `plugin system` mają intencjonalne cykle na poziomie async events lub plugin registration, które NIE są architectural drift. Obecny gate flaguje je jako false positives — counterexample testbed pokazuje to jako strukturalną limitację, nie QA gap.

**Pros:** Wiarygodność gate'u rośnie. Counterexamples przestają być false positives. Edge typing to generalna primitive ułatwiająca też inne rules (np. "tylko sync calls do domain").

**Cons:** Znacząca zmiana w qse-core scanner. Miesiące 2-3 pracy. Wymaga re-scan całego korpusu benchmarków (AGQ liczby się zmienią).

**Context:** Codex zauważył (2026-04-18): "Event Bus, saga, plugin systems need edge typing or exception semantics. Current graph model has no such notion, so some false positives are structural, not QA gaps."

**Depends on / blocked by:** Stabilny qse-core scanner API. R1 MDL go/no-go gate (Miesiąc 4) — jeśli MDL derivation wymaga edge typing dla "informational edges", to sync'uje.

---

## T4: Parallel scan dla Δ mode performance

**What:** Base graph scan + PR head scan → 2 threads równolegle w `run_gate()`.

**Why:** Obecny design (per Sprint 0 Issue 3 resolution) jest sequential. Dla 100k+ LOC enterprise repo: ~30s × 2 = 60s gate latency. Z parallel: ~30s (plus overhead thread coordination).

**Pros:** Halved gate latency dla dużych repo. Niższy CI bill. Better UX (developer mniej czeka).

**Cons:** Threading concerns — qse-core Rust scanner musi być thread-safe (verify). Dodatkowa złożoność w gate orchestration.

**Context:** Perf finding z eng review [P2] (2026-04-18). Nie blokuje Sprint 0 (demo repo małe), ale blokuje enterprise pilot w Miesiącu 2+.

**Depends on / blocked by:** Confirm qse-core Rust scanner thread-safety. Jeśli nie → thread-per-process albo zamrożenie w Miesiącu 2.

---

## T5: Archtest.py split (665 linii → 3-4 pliki)

**What:** Wydzielić `qse/archtest.py` (obecnie 665 linii, ~9 responsibility) na:
- `qse/archtest.py` (CLI entry, run orchestration)
- `qse/thresholds.py` (green/amber/red config + classification)
- `qse/archipelago.py` (advisory detection logic)
- `qse/report_formatter.py` (JSON + Markdown formatting)

**Why:** Monolityczny plik miesza concerns. Dodawanie "Rules Fired" sekcji (Sprint 0) dotyka archtest.py. Po split — dotyka tylko report_formatter.py. Techniczny dług mid-priority.

**Pros:** Clean SRP per plik. Łatwiejsze testy unit. Mniejsze diff'y przy zmianach.

**Cons:** Importy się przesuwają, breaking change dla downstream caller'ów (jeśli ktoś bezpośrednio importuje z archtest).

**Context:** Eng review [P3] (2026-04-18). Obvious fix, low risk, ale nie blokuje Sprint 0 po przyjęciu scope redesign.

**Depends on / blocked by:** Sprint 0 `qse/gate.py` surface redesign. Lepiej po Sprincie 0 bo gate engine może zmienić interfejs z archtest.

---

## T6: Decouple `qse/cli.py` i `qse/trl4_gate.py` od DDD preset

**What:** Usunąć importy `from qse.presets.ddd.*` z main flow files: `qse/cli.py:9-11` (QSEConfig, analyze_repo, format_json, format_table) i `qse/trl4_gate.py:21-22` (QSEConfig, analyze_repo). Potem przenieść `qse/presets/ddd/` do `_obsolete/qse_presets_ddd/`.

**Why:** Decyzja projektowa (2026-04-18): DDD jest out of main flow ("DDD psuje metryki, DDD jest z góry ułożoną architekturą by design"). Obecnie 3 pliki main-flow (cli.py, trl4_gate.py) oraz 3 pliki testowe (test_metrics.py, test_gate.py, test_universal_metrics.py) + 1 script (scripts/trl4_weekend_validation.py) importują z DDD preset. Dopóki te importy istnieją, DDD jest w main flow pomimo decyzji.

**Pros:** Czyste odseparowanie DDD. `qse` CLI przestaje zależeć od DDD preset — mniejszy blast radius. Zgodność z projekt decision "AI-drift firewall ≠ DDD enforcer".

**Cons:** `qse/cli.py` straci DDD subcommands (albo musi dostać osobny flow bez DDD). `qse/trl4_gate.py` potrzebuje zastąpienia `analyze_repo()` czystszym graph-only analysis. 4 test files trzeba albo naprawić, albo skasować (jeśli testują DDD feature która nie jest już w produkcie).

**Context:** Skan repo (2026-04-18, [MEMORY.md aktualny]) ujawnił że `qse/presets/ddd/__init__.py` zostało oznaczone jako DEPRECATED ale physical move czeka na ten decouple. Templates ddd_scaffold + scripts/trl4_gate.py stub juz przeniesione do _obsolete/. DDD preset (10 plików, ~870 linii) zostaje ostatni do przeniesienia.

**Blast radius:**
- qse/cli.py:9-11 (importy QSEConfig, analyze_repo, format_json, format_table) — CLI usage downstream
- qse/trl4_gate.py:21-22 (importy QSEConfig, analyze_repo) — gate pipeline
- tests/test_metrics.py:7,10,148,159 — DDD metrics tests
- tests/test_gate.py:9,10 — DDD gate tests
- tests/test_universal_metrics.py:20,390,391,400,410,430 — mix (universal detectors + DDD-specific delegations)
- scripts/trl4_weekend_validation.py:23 — research script

**Depends on / blocked by:** Sprint 0 decision na `qse/gate.py` (Issue 1 eng review) — jeśli nowy gate nie używa analyze_repo, to T6 staje się częściowo darmowy (zastępca gotowy).

---

## Priorytetyzacja (sugestia)

**Blokujące Sprint 0 delivery:**
- T1 (workflow consolidation) — bez tego CI flow jest chaotic
- T2 (command surface) — bez tego `qse gate` collision blokuje rename

**Sprint 0 code refactor (równoległy z T1/T2):**
- T6 (DDD decouple + move) — finalne wypchnięcie DDD z main flow. Sprint 0 new gate.py może to dostarczyć jako side effect.

**Miesiąc 2-3:**
- T4 (parallel scan) — zanim pierwszy enterprise pilot
- T5 (archtest.py split) — cleanup przed dodawaniem nowych reguł

**Miesiąc 4+ (wymaga większej pracy research):**
- T3 (edge typing) — tied z R1 MDL go/no-go

---

## T7: Pilot paradox resolution — QSE < Random w pass rate

**What:** `papiers/PILOT_RESULTS_FINAL.md` pokazuje że **QSE feedback underperforms random feedback w immediate pass rate** (50% vs 67% overall, Fisher's p=0.34 NS). Tylko Claude Sonnet 4 pokazuje istotny sygnał w convergence (p=0.012). To jest counter-signal do H3 grantu ("ratchet reduces review by ≥70%").

**Why:** Grant panel może to zakwestionować. Potrzebne: (a) research on WHY — za długie prompts? za dużo false positives w detektorach? model-specific (Sonnet-only) effect?, (b) decision: redefiniować H3, albo zmienić feedback mechanism (multi-turn vs single-shot), albo zawęzić pilot context.

**Pros:** Honest communication z grant panelem. Fine-tune feedback loop przed WP-BR3 (RLHF for LLMs) gdzie ten sam mechanism jest centralny.

**Cons:** Jeśli H3 wymaga redefinicji, to może wpłynąć na grant scope. Negotiacja z NCBiR.

**Context:** Pilot details: 12 runs (4 models × 3 feedback modes), 10 specs each. QSE prompts za długie → Qwen API errors (3 vs 0). False positive rate w v2 symbol-map detektorze ~16% może być sufficient do miticji sygnału.

**Depends on / blocked by:** Nic — research task, można zacząć równolegle z Sprint 0.

---

## T8: Wiki staleness cleanup (3 pages)

**What:** Zaktualizować 3 pages w docs/qse-wiki/:
1. `04 Metrics/Stability.md` — dodać sekcję "Known Limitations (April 2026)" z L8 (S gameable przez namespace) i L11 (var(I)=var(1-I) mathematical invariance).
2. `11 Research/Limitations.md` — dodać L8-L11 do głównej listy (obecnie tylko L1-L7 visible w summary).
3. `01 Canon/Current Priorities.md` — wyjaśnić status archipelago detector: zintegrowany w archtest CLI? post-hoc flag? czy user musi explicit enable?

**Why:** Wiki jest źródłem prawdy dla wewnętrznej (zespół) i zewnętrznej (grant panel, partnerzy) komunikacji. Stale content na kluczowych stronach = niespójność narratywu. Recenzja grant panel może znaleźć rozbieżność.

**Pros:** Spójność źródła prawdy. Łatwiejsze onboarding nowych osób. Transparentna komunikacja limitacji.

**Cons:** Czas: ~30-60 min na każdą stronę.

**Context:** Skan repo (2026-04-18, deep read via 5 subagents). Agent pokrywający wiki zidentyfikował te 3 pages jako high-priority stale.

**Depends on / blocked by:** Nic — straightforward docs work.

---

## T9: Script sprawl verification (NIE ruszone w cleanup 2026-04-18)

**What:** Przejść przez 39 scripts w scripts/ i weryfikować case-by-case:
1. `experiment_total.py` (698 linii) — czy nadal active? Agent zgłosił jako empty ale ma treść.
2. `benchmark_parallel.py` vs `benchmark_fast.py` — czy oba potrzebne czy merge?
3. `e9_run_pilots.py` vs `e9_pilot_battery.py` — overlap, merge z --phase flag?
4. `agq_churn_analysis.py`, `agq_cochange_entropy.py` — cytowane w DOCUMENT_MAP.md, ale czy dane wyjściowe są aktualnie używane? Jeśli nie — candidate dla _obsolete.
5. `s_sensitivity_investigation.py`, `multirepo_rerun_with_detector.py` — one-offs, diagnostic. Keep as historical lub move?
6. `trl4_gate.py` w scripts (9 linii) — już przeniesione do _obsolete/scripts/ 2026-04-18.

**Why:** Agent raport miał błędy ("experiment_total.py empty" — nieprawda). Trzeba manualnie sprawdzić. 39 scripts to dużo dla maintenance.

**Pros:** Cleaner scripts/. Lower onboarding friction.

**Cons:** Ryzykowne — można usunąć coś co ktoś cytuje w papier/grant. Wymaga weryfikacji cytowań.

**Context:** Deep read (2026-04-18) pokazał różne jakości agent inference. DOCUMENT_MAP.md references 2 "abandoned" scripts — nie są abandoned.

**Depends on / blocked by:** Nic. Minimalne ryzyko jeśli każdy file weryfikowany osobno.

---

## T10: AGQ formula canonical discrepancy

**What:** Zweryfikować i zapisać **jedną** kanoniczną formułę AGQ v3c. Deep read (2026-04-18) ujawnił discrepancy:
- Research narrative (RESEARCH_LOG, wiki): `AGQ_v3c (Java) = 0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD` (pięć metryk, CD=Coupling Density)
- `artifacts/agq_v3_definition.json`: `AGQ_v3c = 0.25·M + 0.25·A + 0.25·S + 0.25·C` (cztery metryki, BEZ CD)
- `qse/archtest.py` THRESHOLDS + `qse/graph_metrics.py` — zweryfikować kod

**Why:** Grant panel będzie sprawdzał spójność definicji vs implementacji. Discrepancy = red flag.

**Pros:** Jednoznaczna definicja, easier audit.

**Cons:** Może wymagać re-kalibracji jeśli formuła używana w kodzie ≠ formuła w papierach.

**Context:** Dwa subagents (Stream A + Stream B) podały różne formuły. Nie miałem czasu zweryfikować kodu głęboko.

**Depends on / blocked by:** Nic — docs/code audit.
