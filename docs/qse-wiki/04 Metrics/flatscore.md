---
type: metric
language: pl
---

# flat_score

## Prostymi słowami

flat_score mierzy, ile procent modułów ma *głęboką* ścieżkę namespace — głębszą niż 2 poziomy. Jeśli prawie wszystkie moduły projektu siedzą na powierzchni (depth≤2), projekt jest "płaski" jak talerz. Płaski projekt nie ma hierarchii, nie ma warstw, nie ma struktury. flat_score=0 to red flag dla Pythona. Przykład: youtube-dl ma 895 modułów, wszystkie w depth≤2 — flat_score=0.000, Panel=2.25.

## Szczegółowy opis

### Problem który rozwiązuje flat_score

Dla Pythona, żadna ze standardowych metryk AGQ (M, A, S, C, CD) nie dyskryminuje skutecznie dobrej i złej architektury — CD ma nawet odwrócony kierunek. Problemem jest specyficzna patologia "flat spaghetti":

```
youtube-dl (NEG, Panel=2.25):
  895 modułów, wszystkich w src/ lub src/extractors/
  depth = 1–2 dla każdego
  flat_score = 0.000  ← czerwona flaga
  
saleor (POS, Panel=7.50):
  3763 modułów w strukturze src/saleor/domain/submodule/
  239/3763 w depth≤2
  flat_score = 0.936  ← dobra hierarchia
```

### Wzór

```
flat_ratio = (liczba_węzłów z depth ≤ 2) / n_internal
flat_score = 1 − flat_ratio
```

Wysoki flat_score (bliski 1.0) = mało modułów płaskich = głęboka hierarchia = dobra struktura.
Niski flat_score (bliski 0.0) = prawie wszystko płaskie = brak hierarchii.

### Dane empiryczne Python GT (n=23, sesja Turn 39)

| Kategoria | flat_score (śr.) | p-value |
|---|---|---|
| **POS** | **0.665** | — |
| **NEG** | **0.200** | — |
| Różnica | +0.465 | — |
| Mann-Whitney p | **0.004 \*\*** (n=23) | — |
| Partial r | +0.670 \* | — |

Po rozszerzeniu GT do n=30 (sesja Turn 50):
- MW p = 0.007 \*\*
- Partial r = +0.414, p = 0.023 \*

**flat_score to jedyna metryka z istotnym sygnałem dla Pythona** (przy kontroli rozmiaru).

### Fałszywe negatywne: legacy monolith

flat_score ma jeden znany fałszywy negatyw: **legacy monolith z głęboką hierarchią**. Przykład: buildbot (Panel=2.75) ma flat_score=0.95 — głęboka hierarchia namespace'ów, ale zła architektura.

"Typ 2" złej architektury Python: projekt ze skostniałą, głęboką hierarchią, ale bez sensownej separacji logiki. flat_score nie wykrywa tego — faworyzuje głębokość strukturalną bez oceny *sensu* hierarchii.

Dlatego [[O2 Type 2 Legacy Monolith Detection]] pozostaje otwartym pytaniem.

### flat_score w formule AGQ v3c Python

```
AGQ_Python = 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score
```

flat_score ma **najwyższą wagę** (0.35) w AGQ Python — bo jest jedyną metryką z istotnym sygnałem po kontroli rozmiaru.

### Przykłady skrajne

| Repo | flat_score | Panel | Uwagi |
|---|---|---|---|
| youtube-dl | **0.000** | 2.25 (NEG) | 895 modułów w depth≤2 |
| saleor | **0.936** | 7.50 (POS) | Głęboka hierarchia domenowa |
| zulip | ~0.40 | 6.50 (POS) | Warstwowy Django projekt |
| archivebox | ~0.15 | 3.00 (NEG) | Płaska struktura monorepo |

### Implementacja

flat_score jest obliczane w `qse/flat_metrics.py`, dostępne jako właściwość `AGQMetrics.flat_score` w `graph_metrics.py`.

Depth 2 jako próg = depth 1 to katalog root, depth 2 to pierwszy podkatalog. Moduły w depth≤2 są "powierzchniowe" — nie ma sensu logicznego zagnieżdżenia w pakietach domenowych.

## Definicja formalna

\[\text{flat\_ratio} = \frac{|\{v \in V_{\text{internal}} : \text{depth}(v) \leq 2\}|}{|V_{\text{internal}}|}\]

\[\text{flat\_score} = 1 - \text{flat\_ratio}\]

Gdzie \(\text{depth}(v)\) = głębokość modułu \(v\) w hierarchii namespace'ów (liczona od korzenia projektu).

**Zakres:** [0, 1]. flat_score=0.0 → wszystkie moduły płaskie. flat_score=1.0 → wszystkie moduły głębiej niż depth=2.

**Walidacja statystyczna** (Python GT n=30):
- Mann-Whitney p = 0.007 \*\*
- Partial r = +0.414, p = 0.023 \*

**Waga w AGQ v3c Python:** 0.35 (najwyższa spośród wszystkich składowych).

## Zobacz też

- [[NSdepth]] — głębokość hierarchii (Java)
- [[Hierarchy]] — pojęcie hierarchii w QSE
- [[O2 Type 2 Legacy Monolith Detection]] — fałszywy negatyw flat_score
- [[W10 flatscore Predicts Python Quality]] — hipoteza potwierdzona
- [[E6 flatscore]] — szczegóły eksperymentu
