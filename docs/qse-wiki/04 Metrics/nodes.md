---
type: metric
language: pl
---

# nodes (węzły grafu)

## Prostymi słowami

"nodes" to liczba modułów (plików) w projekcie po odfiltrowaniu bibliotek zewnętrznych. To rozmiar projektu w sensie QSE. Mały projekt (10 węzłów) i duży projekt (10000 węzłów) mają inne właściwości statystyczne metryk — dlatego QSE normalizuje większość metryk względem n.

## Szczegółowy opis

### Węzły jako miara rozmiaru

`nodes` (lub `n_internal`) = liczba własnych plików projektu po filtrowaniu:
- Usunięte: biblioteki systemowe (stdlib)
- Usunięte: biblioteki zewnętrzne (third-party)
- Pozostałe: tylko własny kod projektu

Ta liczba jest główną miarą rozmiaru w QSE i pojawia się w denominatorze każdej znormalizowanej metryki.

### Wpływ rozmiaru na metryki

| Rozmiar | Acyclicity | Modularity | Uwagi |
|---|---|---|---|
| < 10 węzłów | Nieistotna (brak cykli trywialny) | Domyślnie 0.5 | Za mały do analizy |
| 10–100 | Wiarygodna | Wiarygodna | Standardowy projekt |
| 100–1000 | Wiarygodna | Wiarygodna | Duży projekt |
| > 1000 | Wiarygodna | Louvain wolniejszy | Enterprise scale |

### Dane z benchmarku (558 repo, kwiecień 2026)

| Język | Mediana n_internal | Min | Max | Przykład max |
|---|---|---|---|---|
| Python | ~300 | 2 | 17595 | home-assistant |
| Java | ~800 | 9 | 17596 | quarkus |
| Go | ~200 | 10 | 3604 | ruff |
| TypeScript | ~150 | 10 | 2000 | varies |

### Kontrola rozmiaru w analizach

Rozmiar projektu jest potencjalnym **confoundem**: duże projekty mają więcej możliwości na cykle i tangled imports. Dlatego analizy statystyczne QSE używają **partial Spearman** — korelacji po kontroli logarytmu rozmiaru:

```
partial_r(metric, quality | log(nodes))
```

Przykład (Turn 36): AGQ ma raw r=0.661\* z panelem, ale partial r=+0.599 — część korelacji wynika z rozmiaru.

### n_internal vs n_graph_nodes

- `n_internal`: własne pliki projektu (filtrowane)
- `n_graph_nodes`: wszystkie węzły w grafie (włącznie z pośrednimi FQN dla Javy)

Do metryk używany jest `n_internal`. `n_graph_nodes` to rozmiar surowego grafu przed filtracją.

### Size-adjusted AGQ (AGQ-adj)

AGQ-adj to wersja AGQ znormalizowana względem rozmiaru projektu:
- Małe projekty (< 50 modułów) mają strukturalnie zawyżone AGQ
- AGQ-adj kalibruje do bazowej linii 500 węzłów
- Koreluje silniej z metrykami procesowymi: r=+0.236 dla AGQ-adj vs hotspot_ratio

## Definicja formalna

\[|V_{\text{internal}}| = |\{v \in \text{files}(P) : v \notin \text{stdlib} \cup \text{third\_party}\}|\]

Używane w denominatorze:
- Acyclicity: \(|SCC_{\max}| / |V_{\text{internal}}|\)
- CD: \(|E_{\text{internal}}| / (|V_{\text{internal}}| \cdot 6.0)\)

## Zobacz też

- [[edges]] — krawędzie grafu
- [[Dependency Graph]] — struktura grafu
- [[CD]] — używa nodes w mianowniku
- [[Acyclicity]] — używa nodes w normalizacji
- [[Module]] — co to jest węzeł/moduł
