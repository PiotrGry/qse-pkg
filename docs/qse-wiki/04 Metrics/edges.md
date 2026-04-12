---
type: metric
language: pl
---

# edges (krawędzie grafu)

## Prostymi słowami

"edges" to surowa liczba zależności (importów) między modułami projektu. Każdy `import` lub `use` tworzy jeden strzałkę w grafie. Im więcej krawędzi przy tej samej liczbie modułów — tym gęstsze sprzężenie, tym trudniejsza refaktoryzacja.

## Szczegółowy opis

### Krawędzie jako dane surowe

`edges` (lub `n_graph_edges`) to liczba krawędzi w grafie zależności po filtrowaniu modułów zewnętrznych. To surowiec wejściowy do obliczenia:
- **CD** (edges/nodes ratio → normalizacja)
- **Acyclicity** (Tarjan SCC na grafie krawędzi)
- **Modularity** (Louvain na grafie krawędzi)

### Interpretacja liczby krawędzi

Sama liczba krawędzi bez kontekstu rozmiaru projektu jest prawie bez wartości diagnostycznej:

- 500 krawędzi w projekcie 100 modułów = ratio 5.0 = gęste sprzężenie
- 500 krawędzi w projekcie 500 modułów = ratio 1.0 = luźne sprzężenie

Dlatego QSE używa **edges/nodes ratio** i normalizowanego **CD**, a nie surowych krawędzi.

### Dane przykładowe z Jolak (jolak_scan_results.json)

| Repo | n_files | n_graph_edges | ratio | CD approx |
|---|---|---|---|---|
| light-4j | 894 | 7235 | 8.09 | 0.00 (>6) |
| seata | 2816 | 24413 | 8.67 | 0.00 (>6) |
| sofa-rpc | 1204 | 9402 | 7.81 | 0.00 (>6) |
| MyPerf4J | 259 | 1506 | 5.81 | 0.03 |
| yavi | 472 | 2939 | 6.23 | 0.00 (>6) |
| zip4j | 129 | 1311 | 10.16 | 0.00 (>6) |

Uwaga: `n_graph_edges` z Jolak zawiera zarówno krawędzie wewnętrzne jak i do węzłów FQN (pośrednich). Ratio do obliczeń CD używa tylko krawędzi wewnętrznych.

### Krawędzie a typy projektów

Z benchmarku Java (147 projektów):
- Projekty z małą liczbą krawędzi per węzeł (<2.0): często biblioteki utility, małe projekty
- Projekty z ratio 2–4: typowe aplikacje — dobre i złe architektury
- Projekty z ratio >6: prawie wyłącznie złe architektury (tangled)

### n_graph_edges vs n_internal_edges

QSE rozróżnia:
- `n_graph_edges`: wszystkie krawędzie w grafie (w tym do węzłów FQN)
- `n_internal_edges`: tylko krawędzie między węzłami wewnętrznymi projektu (po filtrowaniu)

Do obliczenia CD używane są `n_internal_edges` i `n_internal_nodes`.

## Definicja formalna

\[|E_{\text{internal}}| = |\{(u, v) \in E : u \in V_{\text{internal}} \land v \in V_{\text{internal}}\}|\]

Ratio:
\[\text{ratio} = \frac{|E_{\text{internal}}|}{|V_{\text{internal}}|}\]

Używane bezpośrednio w:
\[\text{CD} = \max\!\left(0, 1 - \frac{\text{ratio}}{6.0}\right)\]

## Zobacz też

- [[nodes]] — liczba węzłów
- [[CD]] — metryka zbudowana na ratio edges/nodes
- [[Dependency Graph]] — graf krawędzi i węzłów
- [[Coupling]] — konceptualna strona sprzężenia
