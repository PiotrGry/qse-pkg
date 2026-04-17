---
type: metric
language: pl
---

# NSdepth (Namespace Depth)

## Prostymi słowami

NSdepth mierzy, jak "głęboka" jest hierarchia pakietów/namespace'ów w projekcie. Projekt z głęboką hierarchią (np. `com.company.app.domain.model.order` = 6 poziomów) ma wyraźną strukturę organizacyjną. Projekt płaski (wszystko w `src/` lub jednym namespace'ie) nie ma tej struktury. Dla Javy NSdepth jest jednym z najsilniejszych sygnałów jakości architektury.

## Szczegółowy opis

### Czym jest namespace depth?

W zależności od języka:
- **Java**: ścieżka package declaration (`com.company.app.domain.model` = 5 poziomów)
- **Python**: głębokość katalogu od korzenia projektu (`src/domain/orders/` = 3)
- **Go**: ścieżka modułu względem root modułu

NSdepth to **znormalizowana średnia głębokość** wszystkich namespace'ów projektu:

```
NSdepth = mean_depth_namespaces / max_possible_depth
```

Wartość [0, 1], gdzie 1 = maksymalna wykorzystana głębokość w projekcie.

### Dane empiryczne (sesja Turn 36)

**Java GT (n=14, wczesny zbiór):**

| Kategoria | NSdepth (śr.) | Δ | p / partial r |
|---|---|---|---|
| **POS** | ~0.682 | — | — |
| **NEG** | ~0.597 | +0.085 | — |
| Statystyka | — | — | **partial r = +0.698, p = 0.008** |

NSdepth dla Javy jest **silniejszy niż CD** na partial Spearman (r=+0.698 vs r=+0.508). Kontekst: małe n=14 — przy n=59 efekt może się zmienić.

**Python GT (n=14, wczesny zbiór):**
- partial r = +0.433, p = 0.122 **ns**
- Python ma strukturalnie płytszą hierarchię nawet w dobrych projektach

**Wszystkie 357 repo:**
- partial r = +0.303, p = 0.124 **ns** — rozcieńcza się przy mix języków

### Dlaczego Java vs Python różnie reaguje?

Java ma **konwencję głębokiej hierachii pakietów** z natury języka:
```
com.company.app.domain.model.order  ← Java: 6 poziomów naturalne
```

Python typowo:
```
src/domain/order.py  ← Python: 3 poziomy "dobre"
```

Nawet dobre projekty Python mają mean_depth=3.7 POS vs 3.1 NEG — różnica mała, n_neg=4 za mało do potwierdzenia.

### Przykłady z ns_metrics_gt_v1.json (Java)

| Repo | Panel | NSdepth | Kategoria |
|---|---|---|---|
| VaughnVernon/IDDD_Samples | 7.75 | 0.738 | POS |
| ddd-by-examples/library | 8.50 | 0.715 | POS |
| citerus/dddsample-core | 8.25 | 0.686 | POS |
| spring-petclinic/petclinic-rest | 7.00 | 0.693 | POS |
| apache/struts | 2.50 | 0.601 | NEG |
| macrozheng/mall | 2.00 | 0.543 | NEG |
| elunez/eladmin | 2.00 | 0.571 | NEG |

### NSdepth w formule AGQ

NSdepth nie wchodzi do standardowej formuły AGQ v3c (Java ani Python). Jest metryką **uzupełniającą** w AGQ Enhanced. Powód: kombinacja (0.5·NSdepth + 0.5·AGQ_v2) na Javie: r=+0.615 p=0.025 — **gorsze od samego AGQ_v2** (r=+0.675). Dodanie NSdepth do formuły nie poprawia wyniku.

NSdepth może być użyteczny jako samodzielny sygnał w pipeline'ie Multi-Signal, ale wymaga większego n do potwierdzenia.

## Definicja formalna

Dla projektu \(P\) z listą namespace'ów \(\{ns_1, \ldots, ns_k\}\):

\[\text{mean\_depth} = \frac{1}{k} \sum_{i=1}^{k} \text{depth}(ns_i)\]

\[\text{NSdepth} = \frac{\text{mean\_depth}}{\max(\text{depth}(ns_i))}\]

Gdzie \(\text{depth}(ns)\) = liczba segmentów w ścieżce namespace (np. `com.example.domain` = 3).

**Walidacja statystyczna** (Java GT n=14):
- Partial r = +0.698, p = 0.008 \*\*
- Silniejszy niż CD na Javie przy tym n

**Python GT (n=14):**
- Partial r = +0.433, p = 0.122 ns

## Zobacz też

- [[NSgini]] — koncentracja namespace'ów (nierówność)
- [[Hierarchy]] — pojęcie hierarchii
- [[Package]] — pakiety jako namespace'y
- [[flatscore]] — komplementarna metryka dla Pythona
- [[E5 Namespace Metrics]] — eksperyment
