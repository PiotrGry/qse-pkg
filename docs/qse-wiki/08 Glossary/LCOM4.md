---
type: glossary
language: pl
---

# LCOM4 — Lack of Cohesion in Methods 4

## Prostymi słowami

LCOM4 mierzy, czy klasa „robi jedną rzecz". Wyobraź sobie plecak: plecak szkolny (zeszyt, piórnik, kanapka) ma jeden cel — szkoła. Plecak ze zeszytem, wiertarką, marchewką i piłką ma cztery niezwiązane ze sobą sprawy — powinien być 4 plecakami. LCOM4 = ile osobnych „spraw" ma klasa. Ideał: 1.

## Szczegółowy opis

**LCOM4** (Lack of Cohesion in Methods 4) to metryka spójności klas, będąca czwartą wersją rodziny LCOM. Mierzy, jak bardzo metody w klasie są ze sobą powiązane przez wspólne atrybuty.

### Jak obliczane jest LCOM4

1. Dla każdej pary (metoda, atrybut) sprawdzamy, czy metoda używa atrybutu
2. Budujemy **graf nieskierowany**: węzły = metody, krawędź między dwoma metodami jeśli obie używają przynajmniej jednego wspólnego atrybutu
3. LCOM4 = liczba spójnych składowych (connected components) tego grafu

```
Klasa A: metody {m1, m2, m3}, atrybuty {attr1, attr2}
  m1 używa attr1
  m2 używa attr1  → m1 i m2 połączone (oba używają attr1)
  m3 używa attr2  → m3 osobna składowa

LCOM4 = 2 (dwie składowe: {m1,m2} i {m3})
→ Klasa powinna być podzielona na 2 klasy
```

**LCOM4 = 1** — idealne: wszystkie metody są powiązane (klasa spójna)
**LCOM4 > 1** — klasa robi wiele niezwiązanych rzeczy → kandydat do rozbicia

### Przekształcenie do metryki AGQ

AGQ używa odwróconego LCOM4 (znormalizowanego), aby zachować konwencję „wyższy = lepszy":

$$\text{Cohesion}_{AGQ} = 1 - \text{mean}(\text{LCOM4}_i), \quad i \in \text{klasy projektu}$$

Gdzie `mean(LCOM4)` = średni LCOM4 po wszystkich klasach projektu (po znormalizowaniu do [0, 1]).

### Wyniki empiryczne

Z Java GT (n=59):
- POS mean Cohesion: **0.393**
- NEG mean Cohesion: **0.269**
- Δ = +0.124
- Mann-Whitney p = **0.0002** (***) — najsilniejszy dyskryminator

Cohesion (C) jest najsilniejszym indywidualnym dyskryminatorem w Java GT, wyprzedzając nawet Coupling Density (CD=0.155) i Stability (S=0.106).

### Interpretacja wartości Cohesion

| Cohesion (C) | Interpretacja |
|---|---|
| 0.80 – 1.00 | Klasy bardzo spójne, każda robi jedną rzecz |
| 0.50 – 0.80 | Umiarkowana spójność |
| 0.30 – 0.50 | Wiele klas wielofunkcyjnych — typowe dla NEG Java |
| < 0.30 | Poważny problem — god classes dominują |

Wartości referencyjne z Java GT: POS~0.39, NEG~0.27. Dla porównania: benchmark Python (n=80) — mean Cohesion ≈ 0.65 (Python klasy są typowo prostsze).

### Ograniczenia LCOM4

- Wymaga informacji o metodach i atrybutach na poziomie klasy — skaner musi je wyodrębnić
- Słabo działa dla klas z tylko jedną metodą (LCOM4 zawsze = 1)
- Nie wykrywa „semantycznej" niespójności — klasa może być spójna LCOM4=1, ale i tak robić wiele rzeczy z biznesowego punktu widzenia
- W Pythonie: skaner QSE używa heurystyki dla klas bez explicite deklarowanych atrybutów

## Definicja formalna

Niech K będzie klasą z metodami M = {m₁, ..., mₙ} i atrybutami A = {a₁, ..., aₖ}. Definiujemy graf G_K = (M, E_K) gdzie:

$$E_K = \{(m_i, m_j) : \exists a \in A, \, a \in \text{uses}(m_i) \cap \text{uses}(m_j)\}$$

$$\text{LCOM4}(K) = |\text{cc}(G_K)|$$

gdzie cc(G) = liczba spójnych składowych grafu G.

Metryka Cohesion w AGQ:

$$C_{AGQ} = 1 - \frac{1}{|K_{\text{proj}}|} \sum_{k \in K_{\text{proj}}} \text{LCOM4\_norm}(k)$$

## Zobacz też

- [[AGQ|AGQ]] — LCOM4 jako składnik Cohesion (C)
- [[Louvain|Louvain]] — analogiczny algorytm grafowy dla Modularity
- [[Layer|Warstwa]] — strukturalny aspekt uzupełniający spójność
- [[Type 1 Flat Spaghetti|Typ 1 Flat Spaghetti]] — wzorzec z niską spójnością
- [[Java GT Dataset]] — empiryczne dane C
