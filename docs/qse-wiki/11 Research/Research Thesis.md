---
type: research
language: pl
---

# Teza badawcza — AGQ jako Quality Gate dla kodu AI

## Prostymi słowami

Narzędzia AI piszą kod coraz szybciej — ale nie widzą całego projektu. Jak dozorca, który sprząta pokój po pokoju, nie wiedząc, że właśnie przeniósł mebel blokujący drzwi ewakuacyjne. QSE chce być tym, który patrzy na cały budynek — nie na każdy pokój osobno — i alarmuje gdy architektura zaczyna się sypać.

## Szczegółowy opis

### Kontekst: era vibe coding

**Vibe coding** to potoczna nazwa fazy, w której narzędzia AI (GitHub Copilot, Cursor, Claude Code) generują znaczną część kodu w projekcie. Charakterystyki tej fazy:

- Pass@1 rośnie ~10pp/rok (GPT-3.5 → Claude Sonnet 4 = 77%)
- GitHub: >40% kodu enterprise z AI (2025)
- Narzędzia ewoluują: autocomplete → autonomous agent (Devin, Cursor, Claude Code)
- Brak udokumentowanego enterprise-grade systemu napisanego w całości przez AI (stan: 2026-03)

Jesteśmy na etapie „AI pisze, człowiek recenzuje" — pełna autonomia = kwestia quality gates.

### Problem: Quality drift w erze AI

AI generuje kod 10–100x szybciej niż człowiek. Każdy `import` dodany przez AI:
- Może zamknąć cykl zależności niewidoczny lokalnie
- Może przekroczyć granicę warstwy architektonicznej
- Może zwiększyć blast radius przyszłych zmian

**Cztery mechanizmy degradacji:**
1. **Brak pamięci architektonicznej:** LLM nie pamięta decyzji z poprzednich promptów
2. **Brak ownership:** nikt nie „czuje" kodu = nikt nie zauważa erozji
3. **Skala:** AI generuje 10-100x szybciej = drift 10-100x szybszy
4. **Paradoks Sabra:** lepszy model = wyższy Pass@1 = WIĘCEJ defektów strukturalnych

### Paradoks Sabra — kluczowy dowód

Sabra et al. (2025, arxiv 2508.14727) przebadali 4442 zadania Java × 5 modeli LLM z analizą SonarQube (~550 reguł).

**Główny wynik (RQ4):** „Brak bezpośredniej korelacji między Pass@1 a jakością/bezpieczeństwem generowanego kodu."

| Model | Pass@1 | Issues/zadanie |
|---|---:|---:|
| Claude Sonnet 4 | **77.04%** (najlepszy) | **2.11** (najgorszy) |
| Claude 3.7 | 72.46% | 1.60 |
| GPT-4o | 70.54% | 1.77 |
| OpenCoder-8B | 60.43% (najgorszy) | **1.45** (najlepszy) |

**Paradoks:** upgrade Claude 3.7 → Sonnet 4: Pass@1 +4.58pp, BLOCKER bugi +93%.

Rozkład defektów (wszystkie modele):
- Code smells: 90–93%
- Bugs: 5–8%
- Vulnerabilities: ~2%

Branza optymalizuje LLM pod Pass@1 = systematycznie rośnie ukryty dług techniczny.

### Luka w obecnym stosie jakości

| Warstwa | Narzędzie | Co łapie |
|---|---|---|
| Linting | ESLint, Pylint | Styl, proste błędy (per plik) |
| SAST | SonarQube, Checkmarx | Code smells, vulns (per plik) |
| Testy | Unit/Integration/E2E | Poprawność funkcjonalna |
| Code review | Człowiek | **Architektura, design, intencja** |
| Arch rules | ArchUnit (Java only) | Zależności między pakietami |

**Luka:** Code review = JEDYNA warstwa widząca architekturę. Usuń człowieka = nikt nie pilnuje makro.

### Teza główna

AGQ (*Architecture Graph Quality*) jako „Policy as a Service" może zastąpić architektoniczny aspekt code review poprzez **deterministyczne metryki grafowe + deklaratywne constraints**, umożliwiając bezpieczną autonomiczną generację kodu.

```
Dziś:   LLM → kod → CZŁOWIEK review → merge
Jutro:  LLM → kod → AGQ gate → merge (człowiek tylko przy FAIL)
```

Ratchet = score nigdy nie spada. Każdy PR ≥ poprzedni. Drift fizycznie niemożliwy.

```yaml
# qse.yaml — deklaratywna polityka jakości
gate:
  agq_min: 0.80
  max_coupling: 0.3
constraints:
  - from: "src/api/**"
    to: "src/db/**"
    type: forbidden
  - from: "src/domain/**"
    to: "src/infrastructure/**"
    type: forbidden
ratchet: true
```

---

## Pytania badawcze (RQ)

| ID | Pytanie | Cel |
|---|---|---|
| RQ1 | Czy metryki grafowe korelują z defect density w OSS? | Pearson r ≥ 0.5 |
| RQ2 | Czy AGQ wykrywa degradację niewidoczną dla SonarQube? | R² AGQ > R² SQ |
| RQ3 | Czy constraints pokrywają dominujące kategorie defektów LLM? | ≥80% Sabra categories |
| RQ4 | Czy ratchet skutecznie blokuje quality drift w CI? | % PR bez człowieka |

## Hipotezy (H)

| ID | Hipoteza | Status |
|---|---|---|
| H1 | AGQ koreluje z defect density silniej niż SonarQube Maintainability | Testowana |
| H2 | Kod generowany z AGQ gate ma niższy defect density niż bez gate | Planowana |
| H3 | Ratchet + forbidden edges redukuje code review o ≥70% | Planowana |
| H4 | AGQ adresuje ~80% defektów wykrytych w kodzie LLM (Sabra mapping) | Częściowo potwierdzona |

## Mapowanie AGQ → defekty Sabra et al.

| Defekt (Sabra) | Metryka AGQ | Pokrycie |
|---|---|---|
| Dead/Unused code (14-43% smells) | Cohesion (LCOM4), Modularity | L1 |
| Design best practices (11-22%) | Constraints, Stability | L2+L1 |
| Control-flow mistakes (14-48% bugs) | Acyclicity | L1 |
| Exception handling (11-17%) | Cohesion, Coupling | L1 |
| Path-traversal/injection (31-34% vulns) | Constraints | L2 |
| Hard-coded credentials | POZA ZAKRESEM (SAST) | — |

**Szacowane pokrycie ważone: ~80% defektów adresowalnych przez AGQ.**

## Definicja formalna — gap badawczy

Istniejące narzędzia QA operują na poziomie pliku (SonarQube) lub wymagają ludzkiego reviewera do oceny architektonicznej. W erze kodu generowanego przez AI — gdzie wolumen rośnie wykładniczo, a jakość strukturalna spada (Sabra et al.) — brakuje **deterministycznego, automatycznego quality gate na poziomie grafu zależności**, który mógłby zastąpić architektoniczny aspekt code review.

Luka ta jest potwierdzona empirycznie:
- Brak benchmarku mierzącego jakość architektoniczną kodu LLM
- Sabra et al. = jedyna praca z statyczną analizą jakości (ale tylko SonarQube, per plik)
- ArchUnit = jedyny tool z regułami architektonicznymi, ale Java-only, bez SaaS

AGQ wypełnia tę lukę.

## Zobacz też

- [[11 Research/Literature Review|Przegląd literatury]] — Sabra, Jolak, Brito i inni
- [[11 Research/Market Analysis|Analiza rynku]] — gdzie AGQ w krajobrazie narzędzi
- [[11 Research/Future Directions|Kierunki badań]] — co dalej
- [[11 Research/Limitations|Ograniczenia]] — uczciwe zastrzeżenia
- [[07 Benchmarks/Java GT Dataset|Java GT Dataset]] — empiryczne potwierdzenie AGQ
- [[08 Glossary/Blind Spot|Blind Spot]] — co SonarQube pomija
