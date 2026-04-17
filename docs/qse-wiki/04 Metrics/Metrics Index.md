---
type: index
language: pl
---

# Indeks metryk QSE

## Prostymi słowami

Ten dokument to ściągawka — wszystkie metryki QSE w jednym miejscu z danymi empirycznymi. Jeśli chcesz wiedzieć "która metryka najlepiej odróżnia dobry kod od złego", to właśnie tutaj znajdziesz odpowiedź.

## Tabela główna: metryki AGQ per-komponent dla Javy

Dane: Java GT n=59 (31 POS / 28 NEG), kwiecień 2026.

| Metryka | POS (śr.) | NEG (śr.) | Różnica | MW p | Partial r | Siła |
|---|---|---|---|---|---|---|
| [[Cohesion]] (C) | 0.393 | 0.269 | +0.124 | **0.0002 \*\*\*** | +0.479 | **Najsilniejszy** |
| [[CD]] (Coupling Density) | 0.454 | 0.299 | +0.155 | **0.004 \*\*** | +0.342 | **2. miejsce** |
| [[Acyclicity]] (A) | 0.994 | 0.974 | +0.020 | **0.030 \*** | — | **3. miejsce** |
| [[Stability]] (S) | 0.344 | 0.238 | +0.106 | **0.016 \*** | +0.593 (n=29) | **3-4. miejsce** |
| [[Modularity]] (M) | 0.668 | 0.648 | +0.020 | 0.226 ns | ns | Nieistotny sam. |
| **AGQ v3c** | **0.571** | **0.486** | **+0.085** | **0.000221 \*\*\*** | **+0.447** | **Kompozyt** |

**Kluczowy wniosek:** Modularity samodzielnie nie jest istotna (p=0.226), ale wchodzi do AGQ bo jest ortogonalna i wnosi unikalny sygnał do kompozytu.

## Metryki rozszerzone (AGQ Enhanced)

| Metryka | Co oblicza | Zastosowanie |
|---|---|---|
| [[NSdepth]] | Głębokość hierarchii namespace | Java: partial r=+0.698 p=0.008 |
| [[NSgini]] | Nierówność rozkładu namespace | ns wszędzie — informacyjna |
| [[flatscore]] | % węzłów w shallow namespace | Python: MW p=0.007 \*\* |
| [[edges]] | Surowa liczba krawędzi | Surowiec dla CD |
| [[nodes]] | Surowa liczba węzłów | Rozmiar projektu |
| [[DMS Instability]] | Instability Martina per pakiet | Składnik Stability |
| [[Graph Metric]] | Klasa wszystkich metryk grafowych | Pojęcie nadrzędne |

## Formuły AGQ

**AGQ v3c Java:**
\[\text{AGQ} = 0.20 \cdot M + 0.20 \cdot A + 0.20 \cdot S + 0.20 \cdot C + 0.20 \cdot \text{CD}\]

**AGQ v3c Python:**
\[\text{AGQ} = 0.15 \cdot M + 0.05 \cdot A + 0.20 \cdot S + 0.10 \cdot C + 0.15 \cdot \text{CD} + 0.35 \cdot \text{flat\_score}\]

## Macierz korelacji (n=357, Pearson)

| | M | A | S | C | CD |
|---|---|---|---|---|---|
| **M** | 1.00 | +0.02 | −0.20 | −0.25 | +0.18 |
| **A** | +0.02 | 1.00 | +0.09 | +0.26 | +0.27 |
| **S** | −0.20 | +0.09 | 1.00 | +0.10 | +0.13 |
| **C** | −0.25 | +0.26 | +0.10 | 1.00 | −0.08 |
| **CD** | +0.18 | +0.27 | +0.13 | −0.08 | 1.00 |

Wniosek PCA: eigenvalues prawie równe — **brak dominującego wymiaru**. Każda metryka wnosi podobny wkład do łącznej wariancji. To uzasadnia equal wagi 0.20.

## Benchmark per język (średnie, n=558 repo)

| Metryka | Python (n=351) | Java (n=147) | Go (n=30) |
|---|---|---|---|
| AGQ | 0.748 | 0.735 | 0.783 |
| Modularity | ~0.52 | ~0.63 | ~0.61 |
| Acyclicity | ~0.99 | ~0.97 | ~1.00 |
| Stability | ~0.70 | ~0.50 | ~0.72 |
| Cohesion | ~0.65 | ~0.38 | 1.00 |

**Uwaga:** Cohesion Go zawsze = 1.00 (language bias — patrz [[Cohesion]]). Nie oznacza że projekty Go są perfekcyjne.

## Kierunki sygnału per język

| Metryka | Java | Python | Go |
|---|---|---|---|
| M | + (ns) | nieznane | nieznane |
| A | + * | + (rzadko testowane) | trywialne (=1) |
| S | + * | + (ns) | nieznane |
| C | + *** | + (ns) | nieistotne (=1) |
| CD | + ** | − (odwrócony!) | nieznane |
| flat_score | – | + ** | nieznane |
| NSdepth | + ** | + (ns) | nieznane |

"−" oznacza że wyższy = gorszy (odwrócony kierunek).

## Znane ograniczenia metryk

| Metryka | Ograniczenie |
|---|---|
| Modularity | Słaby samodzielny dyskryminator (p=0.226 ns) |
| Acyclicity | Trywialna dla Go (ekosystem wymusza A≈1.0) |
| Stability | Paradoks DDD: rich domain > instability anemic POJO |
| Cohesion | Language bias: Go zawsze=1.0, Java naturalnie niskie |
| CD | Odwrócony kierunek dla Pythona |
| flat_score | Fałszywe negatywne dla "legacy monolith z hierarchią" |
| NSdepth | Słaby sygnał dla Pythona (płytka hierarchia strukturalnie) |

## Zobacz też

- [[Modularity]] — szczegóły M
- [[Acyclicity]] — szczegóły A
- [[Stability]] — szczegóły S (kontrowersje)
- [[Cohesion]] — szczegóły C (najsilniejszy dyskryminator)
- [[CD]] — szczegóły Coupling Density
- [[Conceptual Dimensions]] — cztery wymiary QSE
