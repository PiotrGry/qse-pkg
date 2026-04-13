---
type: handbook
language: pl
---

# qse-archtest CLI — Narzędzie bramki architektonicznej

## Prostymi słowami

qse-archtest to narzędzie linii poleceń, które skanuje repozytorium, oblicza AGQ, klasyfikuje wynik jako green/amber/red i generuje raport z konkretnymi wskazówkami. Można go uruchomić lokalnie albo jako część CI/CD (GitHub Action). Kody wyjścia (0/1/2) umożliwiają automatyczne blokowanie merge'ów przy złej architekturze.

---

## Szczegółowy opis

### Użycie

```bash
# Java — domyślny format JSON
PYTHONPATH=qse-pkg python3 -m qse.archtest --repo ./my-project --lang java

# Python — format markdown
PYTHONPATH=qse-pkg python3 -m qse.archtest --repo ./my-project --lang python --format markdown

# Z porównaniem do main branch (fitness function FF1)
PYTHONPATH=qse-pkg python3 -m qse.archtest --repo . --lang java --main-branch-agq 0.58
```

### Kody wyjścia

| Kod | Status | Znaczenie |
|---|---|---|
| 0 | GREEN | AGQ ≥ green threshold — architektura w normie |
| 1 | AMBER | AGQ między amber a green — wymaga uwagi |
| 2 | RED | AGQ < amber threshold — poważne problemy |
| 3 | ERROR | Błąd skanowania, za mało węzłów, etc. |

### Progi (empirycznie kalibrowane)

| Język | Green ≥ | Amber ≥ | Red < |
|---|---|---|---|
| Java | 0.55 | 0.45 | 0.45 |
| Python | 0.55 | 0.42 | 0.42 |

Progi wyznaczone na podstawie rozkładów AGQ w benchmark OSS (558 repozytoriów) i walidowane na GT.

### Fitness Functions

| FF | Nazwa | Opis | Trigger |
|---|---|---|---|
| FF1 | Regression Guard | Sprawdza czy AGQ i CD nie spadły w porównaniu do main branch | AGQ drop ≥ 0.05 AND CD drop ≥ 0.05 |
| FF2 | Absolute Floor | Sprawdza czy AGQ nie spadło poniżej minimalnego progu | AGQ < red threshold |
| FF3 | Trend Monitor | Śledzi trend AGQ po wdrożeniu (wymaga historii) | — |

### Format wyjścia (JSON)

```json
{
  "repo": "./my-project",
  "lang": "java",
  "status": "amber",
  "agq_v3c": 0.487,
  "components": {
    "M": 0.65, "A": 0.99, "S": 0.22, "C": 0.31, "CD": 0.27
  },
  "thresholds": {"green": 0.55, "amber": 0.45},
  "insights": [
    "Low cohesion (C=0.31) — consider splitting large classes",
    "Low coupling density (CD=0.27) — may indicate flat structure"
  ],
  "flags": [],
  "timestamp": "2026-04-13T10:30:00Z"
}
```

### GitHub Action

Reusable action w `.github/workflows/archtest.yml`:

```yaml
# Przykład użycia w CI
name: Architecture Test
on: [pull_request]
jobs:
  archtest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ./.github/workflows/archtest
        with:
          lang: java
          mode: advisory  # advisory | blocking
```

6 wzorców użycia w `archtest-example.yml`:
1. Advisory (non-blocking PR comment)
2. Blocking (fail on red)
3. With regression guard (--main-branch-agq)
4. Multi-language (matrix)
5. Scheduled (weekly report)
6. Custom thresholds

### Architektura wewnętrzna

```
archtest.py
  ├── _scan_repo()      → wywołuje java_scanner / scanner
  ├── _compute_agq()    → AGQ v3c z graph_metrics
  ├── _classify()       → green/amber/red na podstawie progów
  ├── _insights()       → generuje wskazówki tekstowe
  ├── _ff1_check()      → regression guard vs main branch
  └── _emit()           → JSON lub Markdown output
```

Plik: `qse/archtest.py` (531 linii)

### Wymagania

- Python 3.8+
- tree-sitter, tree-sitter-java (dla Javy)
- networkx, community (python-louvain)
- scipy, numpy

---

## Definicja formalna

```
qse-archtest(repo, lang) → {status, agq, components, insights}

status = 
  if agq ≥ THRESHOLDS[lang].green → "green"
  if agq ≥ THRESHOLDS[lang].amber → "amber"
  else → "red"
  
exit_code = {"green": 0, "amber": 1, "red": 2, "error": 3}
```

## Zobacz też

- [[AGQv3c Java]] — formuła używana przez archtest
- [[Current Priorities]] — kontekst wdrożenia
- [[Architecture]] — architektura systemu QSE
