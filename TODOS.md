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
