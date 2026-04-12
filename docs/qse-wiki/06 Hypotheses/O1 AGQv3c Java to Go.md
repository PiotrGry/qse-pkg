---
type: hypothesis
id: O1
status: otwarta
language: pl
topic: Go, cross-language, AGQv3c
sesja_turn: —
---

# O1 — AGQ v3c Java przenosi się na Go

## Prostymi słowami

Formuła AGQ v3c Java (równe wagi 0.20 dla M, A, S, C, CD) była kalibrowana i walidowana wyłącznie na projektach Java. Otwarte pytanie: czy ta sama formuła działa dla Go — innego języka statycznie typowanego z podobną konwencją pakietów?

## Co badano

> **H₁:** AGQ v3c Java (= 0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD) ma partial r(Panel, AGQ | nodes) > 0, p < 0.05 na GT dla projektów Go.

## Status

**OTWARTA** — brak wystarczających danych GT dla Go.

Obecny stan:
- Benchmark zawiera ~30 repo Go, ale bez ocen GT panelu
- BLT jako GT jest obalony (nie można użyć)
- Potrzeba: panel ekspertów dla Go, n≥30, σ<2.0

## Uzasadnienie hipotezy

Go ma podobne do Javy cechy strukturalne:
- Statyczne typowanie → parser tree-sitter może wyprowadzać FQN
- Konwencja pakietów (np. `github.com/user/project/pkg/domain`) → podobna głębokość jak Java
- Explicite deklaracje importów → graf zależności spójny z Javą

Różnice które mogą wpłynąć:
- Go nie ma klas (struct + interface) → czy LCOM4 / Cohesion ma sens?
- Go preferuje płaską strukturę (bez `src/main/java/...` boilerplate)
- Go modules (go.mod) = inne definicje granic modułu

## Dane dostępne

| Dane | Status |
|---|---|
| ~30 repo Go z QSE scan | dostępne (bez GT) |
| GT panel Go | **BRAK** |
| Jolak et al. Go data | niesprawdzone |

## Warunki zamknięcia hipotezy

**POTWIERDZONA:** partial r(AGQ v3c Java, Panel_Go | nodes) ≥ 0.55, p ≤ 0.05, n ≥ 20

**OBALONA:** partial r < 0.30, p > 0.10 przy n ≥ 20; lub Δ(pos-neg) < 0.04

**Plan działania:**
1. Zebrać n≥20 projektów Go z GitHub (mix dobra/zła architektura)
2. Panel 3 ekspertów Go, σ<2.0
3. Uruchomić AGQ v3c Java na Go repo bez modyfikacji formuły
4. Jeśli p>0.10: szukać Go-specyficznych metryk (analogicznie do flat_score dla Pythona)

## Pytanie pomocnicze

Jeśli AGQ v3c Java nie działa dla Go, jakie metryki specyficzne dla Go byłyby potrzebne? Kandydaci:
- Interface ratio (Go intensywnie używa interfejsów — podobne do Acyclicity?)
- Package cohesion (Go packages są mniejsze niż Java — czy LCOM4 jest przeskalowane?)
- Module boundaries (go.mod — zewnętrzne zależności vs wewnętrzna struktura)

## Powiązania

- [[AGQv3c Java]] — formuła do przetestowania
- [[W4 AGQv2 Beats AGQv1 on Java GT]] — potwierdzony wynik na Javie
- [[Experiments Index]] — E4 (Java), analogiczne dla Go
- [[Hypotheses Register]] — pełna lista hipotez
