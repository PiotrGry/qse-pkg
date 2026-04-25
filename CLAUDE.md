# QSE-PKG

**Algorytmiczny harness dla kodu generowanego przez AI.** Deterministyczny,
vendor-neutralny gate który wykrywa regresje architektoniczne — przed mergem.
Bez AI w ścieżce decyzyjnej. Czysta matematyka grafów.

## Pozycjonowanie (soft pivot, kwiecień 2026)

QSE dostarcza **architectural structural visibility**, nie predykcję jakości.
Metryki są deterministyczne, szybkie (46× szybsze niż SonarQube), language-aware.
Predykcyjna wartość względem bug rates jest pod empiryczną weryfikacją —
obecne dane wspierają strukturalną widoczność, nie kauzalną predykcję jakości.

Patrz: `docs/QSE_CLAIMS_AND_EVIDENCE.md` dla pełnego claim auditu.

## Architektura

```
qse/                          # Core (architecture-agnostic)
  graph_metrics.py            # PC, RC, AGQ components, hub_score
  gate/
    gate_check.py             # delta-based gate API (PRIMARY PRODUCT)
    hook_runner.py            # Claude Code PreToolUse hook (vendor-specific)
  scanner.py                  # AST → networkx.DiGraph
  cli.py                      # qse gate-diff / qse agq / qse discover
  agq_enhanced.py             # AGQ-z, AGQ-adj, fingerprints, churn risk
  discover.py                 # Boundary discovery
  test_quality.py             # QSE_test: assertion density, naming, isolation

qse/presets/ddd/              # DDD Extension (opt-in, legacy)
```

Rust core (`qse-core/`): 7-46× szybsze skanowanie (Python, Java, Go).

Pakiet: `pip install git+https://github.com/PiotrGry/qse-pkg.git`
CLI: `qse gate-diff --base origin/main --head HEAD`

---

## Role

Wybierz rolę odpowiednią do zadania:

| Rola | Plik | Kiedy używać |
|---|---|---|
| Analityk badawczy | `ROLE_RESEARCH.md` | interpretacja wyników, hipotezy, pipeline CI/CD, papier |
| Inżynier QSE | `ROLE_ENGINEER.md` | implementacja metryk, refaktoryzacja detektorów, walidacja |

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
