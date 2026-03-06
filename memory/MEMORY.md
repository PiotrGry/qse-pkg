# QSE/AGQ Memory

## Aktualny stan projektu (2026-03-06)

- **TRL 3 potwierdzone eksperymentalnie** (4 eksperymenty, 23 testy, 21 PASS / 2 known limitations)
- AGQ metryki grafowe ZAIMPLEMENTOWANE: `qse/graph_metrics.py`
  - Modularity (Louvain), Acyclicity (Tarjan), Stability (Martin + abstractness), Cohesion (LCOM4)
- Detekcja klas abstrakcyjnych: ABC, Protocol, @abstractmethod — w `qse/scanner.py`
- Constraints engine v1: forbidden edges, glob matching — w `experiments/exp4_constraints/run.py`
- **DDD przeniesione do `qse/presets/ddd/`** — detektory, metryki, pipeline, gate, config
- Core (`qse/`): scanner, graph_metrics, hybrid_graph, tracer, test_quality, cli
- DDD = opcjonalny preset, NIE czynnik walidujacy
- Eksperymenty: `experiments/exp{1-4}_*/results.json`

## Kluczowe decyzje projektowe

- AGQ jest **architecture-agnostic** — mierzy graf, nie pattern
- DDD, hexagonal, clean = presety constraints (Level 2, opt-in)
- Level 1 = zero-config, czyste metryki grafowe, bez zaloszen o architekturze
- LLM NIGDY w scoring path (AI pre-scoring: classifier, post-scoring: rekomendacje)
- Stability wymaga wykrywania klas abstrakcyjnych (ABC, Protocol) — zaimplementowane
- Constraints v1: tylko typ `forbidden`, glob na sciezkach
- **Rust core engine** (WP2): tree-sitter + petgraph + PyO3 — 25-30× szybszy od Pythona
- **HPC** do benchmarku (WP1/WP3): 100+ repo × historia git, kalibracja wag, embarrassingly parallel
- **ML abstractness classifier** (WP2): trenowany na benchmarku, pre-scoring, opcjonalny
- **Benchmark + kalibracja = 18 mies. przewagi** (prawdziwy moat, nie algorytmy)

## Teza badawcza — Quality Gate dla kodu AI

Szczegoly: `memory/research_thesis.md`

- Paradoks Sabra: lepszy Pass@1 = wiecej defektow strukturalnych
- SWE-bench Pro (2026): najlepsze modele 23% na multi-file (vs 80% single-file)
- Dowody ze LLM nie widza architektury: DependEval, Lost in Middle, CGM, SWE-bench Pro
- CGM (graph-aware adapter) = pre-generation, AGQ = post-generation, komplementarne
- RQ1-5 + H1-H5 sformulowane (w tym H5: architecture-agnosticism)

## Analiza rynku i konkurencji

Szczegoly: `memory/market_analysis.md`

- Rynek ~$2.5B (2026), CAGR 15%+, nikt nie mierzy architektury w CI
- AGQ jedyny w kwadrancie: makro + architektura + CI gate + AI code focus

## FENG SMART — wniosek B+R

Szczegoly: `memory/feng_smart_br_input.md`

- Grant 4 mln PLN, 24 mies., TRL 3 -> TRL 7-8
- WP1: Multi-architecture benchmark (6 architektur × 15+ repo = 100+)
- WP3 waliduje korelacje PER ARCHITEKTURE (nie tylko agregat)
- 7 WP, 7 kamieni milowych, 2 papery naukowe

## Pliki memory

- `feng_smart_br_input.md` — **GLOWNY DELIVERABLE** — pelny wsad merytoryczny B+R (HPC, Rust, AI)
- `research_thesis.md` — teza, paradoks Sabra, benchmarki, luka
- `market_analysis.md` — rynek, konkurencja, sizing
- `agq_metrics_explained.md` — metryki jak dla 5-latka
- `sources_analysis.md` — analiza zrodel naukowych
