---
type: concept
language: pl
---

# Metryka grafowa (Graph Metric)

## Prostymi słowami

Metryka grafowa to taka metryka, która mierzy właściwości *relacji między modułami*, a nie samego kodu wewnątrz modułu. Zamiast pytać "czy ta funkcja jest długa?" (metryka kodu), pyta "czy ten moduł jest powiązany z za wieloma innymi?" (metryka grafowa). QSE opiera się wyłącznie na metrykach grafowych.

## Szczegółowy opis

### Co to jest metryka grafowa?

W kontekście QSE metryka grafowa to dowolna funkcja \(f: G \to \mathbb{R}\) gdzie \(G\) to [[Dependency Graph]] projektu.

Podział metryk jakości oprogramowania:

| Typ | Co mierzy | Przykłady | Poziom |
|---|---|---|---|
| **Metryki kodu** | Wewnątrz pliku/funkcji | CC, KLOC, typy błędów | Mikro (plik) |
| **Metryki obiektowe** | Klasa | CBO, WMC, LCOM | Mikro (klasa) |
| **Metryki grafowe** | Relacje między modułami | AGQ, CD, Modularity | Makro (system) |

SonarQube operuje na poziomie mikro (metryki kodu i obiektowe). QSE operuje na poziomie makro (metryki grafowe). Oba są potrzebne i wzajemnie się uzupełniają — brak korelacji między nimi (n=78, p>0.10) potwierdza że mierzą niezależne wymiary jakości.

### Metryki grafowe w QSE

| Metryka | Typ grafu | Właściwość |
|---|---|---|
| [[Modularity]] | Nieskierowany | Community structure |
| [[Acyclicity]] | Skierowany | Brak cykli (DAG) |
| [[Stability]] | Skierowany | Hierarchia instability |
| [[Cohesion]] | Graf klasy (metodowy) | Internal class structure |
| [[CD]] | Skierowany | Gęstość krawędzi |
| [[NSdepth]] | Namespace tree | Głębokość hierarchii |
| [[flatscore]] | Namespace tree | Płaskość struktury |

### Zalety podejścia grafowego

1. **Niezależność od języka** — graf importów ma tę samą semantykę w Javie, Pythonie, Go. Syntaktyczne różnice są abstrakcją skanera.

2. **Deterministyczność** — ten sam kod → ten sam graf → ten sam wynik AGQ. Brak probabilistyki (jak LLM).

3. **Szybkość** — analiza grafu jest O(V+E) dla większości algorytmów (Tarjan, Louvain). Projekt 10K modułów: < 1 sekunda.

4. **Mierzą architekturę, nie kod** — dwa projekty mogą mieć identyczne pliki ale różne grafy zależności → różne AGQ. To jest sens narzędzia.

### Ograniczenia podejścia grafowego

1. **Nie widzi semantyki** — Stability nie odróżni "stabilny bo świetnie zaprojektowany" od "stabilny bo pusty POJO". Tylko topologia grafu, bez rozumienia intencji.

2. **Nie mierzy efektów dynamicznych** — statyczna analiza nie widzi co się dzieje w runtime (dependency injection, refleksja). Np. Spring może tworzyć zależności w runtime niewidoczne w grafie statycznym.

3. **Granularność plikowa** — jeden "duży plik" z 50 klasami wygląda jak jeden węzeł. Architektura wewnątrz pliku jest niewidoczna dla grafu.

4. **Language bias** — Go nie ma klas z atrybutami → Cohesion=1.0 zawsze. Porównania między językami wymagają AGQ-z.

### Teoria grafów za QSE

Kluczowe algorytmy:

| Algorytm | Zastosowanie | Złożoność |
|---|---|---|
| **Louvain** | Community detection → Modularity | O(n log n) |
| **Tarjan SCC** | Cycle detection → Acyclicity | O(V+E) |
| **Union-Find** | LCOM4 components → Cohesion | O(α(n)) |
| **Degree centrality** | Fan-in/fan-out → Stability, CD | O(V+E) |

## Definicja formalna

Metryka grafowa AGQ to kompozyt:

\[\text{AGQ}(G) = \sum_{i=1}^{k} w_i \cdot m_i(G)\]

Gdzie \(m_i: G \to [0, 1]\) to indywidualne metryki grafowe i \(\sum_i w_i = 1\).

Każda składowa \(m_i\) jest zdefiniowana jako funkcja grafu \(G = (V, E)\) lub jego podgrafów (np. grafu klas dla LCOM4).

## Zobacz też

- [[Dependency Graph]] — graf wejściowy
- [[Modularity]] — Newman's Q
- [[Acyclicity]] — Tarjan SCC
- [[Stability]] — instability hierarchy
- [[Cohesion]] — LCOM4
- [[CD]] — density metric
