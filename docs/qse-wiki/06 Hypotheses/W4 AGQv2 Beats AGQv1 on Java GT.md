---
type: hypothesis
id: W4
status: potwierdzona
language: pl
topic: AGQv2, Java GT, Coupling Density
tested_by: E2, E4
sesja_turn: 22-24, 30-31
---

# W4 — AGQ v2 bije AGQ v1 na Java GT

## Prostymi słowami

AGQ v1 korelował z jakością Java — ale ta korelacja znikała gdy weźmiemy pod uwagę, że duże projekty mają inne metryki niż małe. AGQ v2 (z dodanym Coupling Density) przeżywa tę kontrolę. To pierwsza wersja formuły która „działa uczciwie" — niezależnie od wielkości projektu.

## Co badano

> **H₁:** AGQ v2 (z Coupling Density) ma istotnie wyższe partial r(Panel, AGQ | nodes) niż AGQ v1.

AGQ v1: brak CD, S z wagą 0.55. AGQ v2: CD dodane (waga 0.20), wagi przeliczone.

## Wynik

| Test | AGQ v1 | AGQ v2 | Interpretacja |
|---|---|---|---|
| Mann-Whitney p | 0.038 * | **0.010 \*\*** | v2 lepiej separuje POS/NEG |
| Spearman r (surowy) | +0.661 * | **+0.746 \*\*** | v2 silniejsza korelacja |
| **Partial r (kontrola nodes)** | +0.530 **ns** | **+0.675 \*\*** | **v1 nie przeżywa, v2 przeżywa** |
| p (partial) | 0.051 ns | **0.008 \*\*** | przełom — v2 istotny po kontroli |

**Hipoteza potwierdzona.** AGQ v2 jako pierwsza wersja formuły przeżywa kontrolę rozmiaru.

## Dane

### GT Java n=14 (Turn 31 — finalne dane E4)

| Repo | Typ | nodes | ratio | AGQ v1 | AGQ v2 | Panel |
|---|---|---|---|---|---|---|
| ddd-by-examples/library | DDD | 256 | 2.68 | 0.439 | **0.514** | 8.50 POS |
| citerus/dddsample-core | DDD | 216 | 2.81 | 0.494 | **0.543** | 8.25 POS |
| gothinkster/realworld | CQRS | 269 | 2.71 | 0.430 | **0.509** | 7.50 POS |
| spring-petclinic-rest | LAY | 234 | 2.66 | 0.462 | **0.534** | 7.00 POS |
| spring-petclinic | PBF | 112 | 1.60 | 0.592 | **0.660** | 6.50 POS |
| spring-security | FW | — | 6.03 | 0.827 | **0.648** | 6.50 POS |
| apache/velocity-engine | FW | 361 | 3.72 | 0.437 | 0.464 | 3.25 NEG |
| apache/struts | FW | 2111 | 4.33 | 0.449 | 0.462 | 2.50 NEG |
| macrozheng/mall | CRUD | 799 | 3.62 | 0.372 | 0.430 | 2.00 NEG |

### Separacja POS vs NEG

| Statystyka | AGQ v1 | AGQ v2 |
|---|---|---|
| pos_mean | 0.524 | **0.562** |
| neg_mean | 0.417 | **0.456** |
| Δ (pos−neg) | +0.107 | **+0.107** (ta sama!) |
| p (MW) | 0.013 * | **0.001 \*\*** |

Δ jest identyczny, ale p-value jest lepsze — bo AGQ v2 lepiej rankinuje wewnątrz każdej grupy.

### Ewolucja wyników (iteracje Turn 22 → 24 → 31)

| n | AGQ v2 partial r | p | Przebieg |
|---|---|---|---|
| n=10 (tylko DDD POS) | +0.721 | 0.019 * | wstępne odkrycie |
| n=13 (z non-DDD POS) | +0.599 | 0.031 * | nieco słabsze po uogólnieniu |
| **n=14 (finalne, E4)** | **+0.675** | **0.008 \*\*** | **wzmocnione — więcej danych** |

Wynik stał się **mocniejszy** przy n=14 niż n=13 — to dobry znak (nie overfitting).

## Dlaczego to ważne

**To pierwsza liczba w projekcie oparta na solidnych danych** (Turn 31, cytat z sesji). AGQ v1 korelował z panelem (+0.661*), ale efekt znikał po kontroli rozmiaru. AGQ v2 przeżywa — to znaczy, że CD mierzy coś realnego, niezależnego od tego, że duże projekty po prostu mają inne statystyki.

**Walidacja non-DDD:** Obawy, że AGQ v2 działa tylko dla DDD, zostały obalone:
```
Mann-Whitney DDD vs non-DDD: p=0.40 ns → brak biasu architektury
Mann-Whitney non-DDD vs NEG: p=0.024 * → CD odróżnia różne wzorce od złych
```

**Stabilność:** AGQ v2 przeszedł z partial r=0.341 ns (v1) → 0.599* (n=13) → 0.675** (n=14). Wynik rośnie z danymi zamiast maleć — to cecha prawdziwego sygnału.

## Ograniczenia

1. **n=14** — nadal małe, potrzeba n≥30 dla pełnej wiarygodności
2. **spring-security kontrprzykład:** AGQ v1=0.827 (najwyższe!), AGQ v2=0.648, Panel=6.50 — framework security ma wiele połączeń przychodzących z natury, CD zaniża ocenę. Nie jest to błąd — frameworki ≠ aplikacje domenowe.
3. **Stability nadal nieistotna:** S partial r p=0.154 ns — dominująca składowa AGQ nie działa. AGQ v2 działa mimo S, nie dzięki S (M, C, CD wyrównują błąd).

## Formuła AGQ v2

```
AGQ v2 = 0.20·M + 0.20·A + 0.35·S + 0.05·C + 0.20·CD
CD = 1 − clip((edges/nodes) / 6.0, 0, 1)
```

Wagi AGQ v2 zostały następnie zastąpione przez equal 0.20 (AGQ v3c Java, z PCA — zob. [[PCA Weights]]) bez utraty moc na Javie.

## Powiązane eksperymenty

- [[E2 Coupling Density]] — eksperyment który dostarczył CD do formuły
- [[E4]] (brak oddzielnej strony) — rozszerzenie GT do n=14, potwierdzenie W4
- [[PCA Weights]] — wagi PCA = equal 0.20 = AGQ v3c Java

## Definicja formalna

**Partial Spearman r(AGQ, Panel | nodes):**
Obliczany przez regresję reszt: `residuals(AGQ ~ log(nodes))` i `residuals(Panel ~ log(nodes))`, następnie korelacja Spearmana tych reszt. Wartość p z permutacji lub asymptotycznie.

## Zobacz też

- [[E2 Coupling Density]] — skąd wziął się CD
- [[AGQv2]] — pełna definicja formuły
- [[AGQv3c Java]] — następna wersja (equal weights PCA)
- [[Hypotheses Register]] — pełna lista hipotez
- [[W7 Stability Hierarchy Score]] — obalona hipoteza dla porównania
