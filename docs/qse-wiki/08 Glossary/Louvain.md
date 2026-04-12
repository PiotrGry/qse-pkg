---
type: glossary
language: pl
---

# Louvain — Algorytm wykrywania społeczności

## Prostymi słowami

Louvain to algorytm, który patrząc na sieć połączeń, automatycznie znajduje „grupy" — węzły, które bardziej rozmawiają ze sobą niż z resztą. Jak w szkole: automatycznie znajdzie paczki przyjaciół na podstawie tego, kto z kim rozmawia. W kodzie: która klasa z którą „rozmawia" (importuje).

## Szczegółowy opis

**Algorytm Louvaina** (Blondel et al., 2008) to zachłanny algorytm wykrywania społeczności w grafach, używany w QSE do obliczenia metryki **Modularity (M)**.

### Jak działa Louvain

**Faza 1 — Optymalizacja lokalna:**
1. Każdy węzeł zaczyna w swojej własnej społeczności
2. Dla każdego węzła próbujemy przenieść go do sąsiedniej społeczności
3. Przenosimy, jeśli zmiana maksymalizuje przyrost Q (Newman's Modularity)
4. Powtarzamy aż nie ma korzystnych przesunięć

**Faza 2 — Agregacja:**
1. Każda społeczność staje się nowym „super-węzłem"
2. Wracamy do Fazy 1 na skompresowanym grafie

Iterujemy do zbieżności. Złożoność: prawie liniowa O(n log n) dla rzadkich grafów.

### Newman's Modularity Q

Louvain maksymalizuje Q — miarę jakości podziału na społeczności:

$$Q = \frac{1}{2m} \sum_{ij} \left[A_{ij} - \frac{k_i k_j}{2m}\right] \delta(c_i, c_j)$$

gdzie:
- $A_{ij}$ — macierz sąsiedztwa
- $k_i$ — stopień węzła i
- $m$ — łączna liczba krawędzi
- $\delta(c_i, c_j)$ — 1 jeśli i i j w tej samej społeczności

Q ∈ [-0.5, 1]: Q = 0 → losowy graf, Q = 1 → idealna separacja.

### Przekształcenie do metryki AGQ

$$\text{Modularity}_{AGQ} = \max(0, Q) / 0.75$$

(wartości Q > 0.75 są rzadkie w praktyce, dlatego używamy 0.75 jako normalizacji).

### Wyniki empiryczne

Modularity (M) jest **najsłabszym** dyskryminatorem w GT Java:
- POS mean M = 0.668, NEG mean M = 0.648, Δ = +0.021
- Mann-Whitney p = 0.226 — **nieistotna statystycznie**

Oznacza to, że sama Modularity nie wystarcza do odróżnienia dobrych od złych architektur. Jednak jest użyteczna w połączeniu z innymi metrykami (AGQ composite).

### Zastosowanie w QSE discover

```bash
qse discover /projekt --output-constraints .qse/arch.json
```

`qse discover` używa Louvaina do automatycznego wykrywania klastrów w grafie zależności i generowania pliku z regułami architektonicznymi. W ten sposób QSE może automatycznie „nauczyć się" struktury projektu bez ręcznej konfiguracji.

### Cechy algorytmu Louvain

| Właściwość | Wartość |
|---|---|
| Typ | Zachłanny, heurystyczny |
| Złożoność | O(n log n) dla rzadkich grafów |
| Deterministyczny? | Zależnie od implementacji — QSE używa deterministycznego seeda |
| Liczba społeczności | Automatycznie określana przez algorytm |
| Wymagany parametr k | Nie — w przeciwieństwie do k-means |

## Definicja formalna

Niech G = (V, E, w) będzie ważonym grafem nieskierowanym (krawędziom przypisano wagi = liczba importów). Louvain szuka partycji C = {C₁, ..., Cₖ} maksymalizującej Q:

$$\text{Louvain}: \arg\max_{C} Q(C)$$

przez iteracyjną optymalizację lokalną (faza 1) i hierarchiczną agregację (faza 2).

## Zobacz też

- [[AGQ|AGQ]] — M jako komponent AGQ
- [[Tarjan SCC|Tarjan SCC]] — algorytm dla Acyclicity
- [[LCOM4|LCOM4]] — algorytm dla Cohesion
- [[Repository Types|Typy repozytoriów]] — LAYERED/CLEAN klasyfikacja
