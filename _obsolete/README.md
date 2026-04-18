# _obsolete

Katalog rzeczy nieaktualnych, przeniesionych tutaj zgodnie z regułą:
**"nie usuwaj, tylko przenieś"**.

## Zawartość

| Path | Skąd przeniesione | Dlaczego | Data |
|---|---|---|---|
| `root_duplicates/TRL4_WEEKEND.md` | `TRL4_WEEKEND.md` (root) | Duplikat identyczny z `artifacts/archive/TRL4_WEEKEND.md` | 2026-04-18 |
| `docs_wiki_legacy/` (6 MD) | `docs/wiki/` | Stara wiki — aktualna jest `docs/qse-wiki/` (Obsidian vault, 133 MD) | 2026-04-18 |
| `templates_ddd_scaffold/` | `templates/ddd_scaffold/` | Pusty DDD project skeleton. DDD out of main flow. | 2026-04-18 |
| `scripts/trl4_gate.py` | `scripts/trl4_gate.py` | 9-linowy stub duplikat `qse/trl4_gate.py` (285 linii) | 2026-04-18 |

## Pending moves (zależne od Sprint 0)

- `qse/presets/ddd/` — oznaczony jako DEPRECATED w `__init__.py`. Physical move
  wymaga decouple'u `qse/cli.py:9-11` + `qse/trl4_gate.py:21-22` + 3 plików
  testowych + 1 scripta. Patrz TODOS.md T6.

## Reguła dotycząca tego katalogu

**Nie usuwaj plików z _obsolete bez świadomej decyzji.** To archiwum "chcę to mieć
na wszelki wypadek", nie "nieużywane, skasować". Jeśli coś nie zostało ruszone
przez 12+ miesięcy, można rozważyć usunięcie — ale z weryfikacją że nikt już tego
nie przywoła.
