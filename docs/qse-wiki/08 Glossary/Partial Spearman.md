---
type: glossary
language: pl
---

# Partial Spearman — Korelacja cząstkowa Spearmana

## Prostymi słowami

Partial Spearman mówi, czy dwie rzeczy są powiązane po wyeliminowaniu wpływu trzeciego czynnika. Przykład: wzrost i waga korelują, ale ile z tej korelacji to tylko „starsi = wyżsi i ciężsi"? Partial Spearman „trzyma wiek w stałości" i sprawdza, czy wzrost i waga nadal korelują. W QSE: kontrolujemy rozmiar projektu, żeby sprawdzić, czy AGQ naprawdę koreluje z jakością, a nie tylko z tym, że większe projekty są inne.

## Szczegółowy opis

**Korelacja cząstkowa Spearmana** (*Partial Spearman correlation*) to rozszerzenie standardowej korelacji Spearmana, pozwalające **kontrolować wpływ zmiennych konfundujących** (*confounders*).

### Dlaczego potrzebna

W benchmarku QSE kluczowym confounderem jest **rozmiar projektu** (liczba węzłów/plików). Większe projekty mają tendencję do:
- Wyższej Modularity (więcej klas → łatwiejsza segmentacja)
- Niższego Coupling Density (więcej węzłów → gęstość spada)
- Niższego AGQ ogółem (skala wprowadza złożoność)

Bez kontroli rozmiaru nie wiemy, czy korelacja AGQ z jakością to efekt metryki, czy po prostu efekt rozmiaru.

### Jak obliczana

**Krok 1:** Oblicz Spearman(X, Y) — korelację AGQ z Panel Score
**Krok 2:** Oblicz Spearman(X, Z) — korelację AGQ z rozmiarem (Z = n_nodes)
**Krok 3:** Oblicz Spearman(Y, Z) — korelację Panel Score z rozmiarem
**Krok 4:** Partial Spearman = korelacja reszt regresji rang

$$r_{\text{partial}}(X, Y | Z) = \frac{r_{XY} - r_{XZ} \cdot r_{YZ}}{\sqrt{(1 - r_{XZ}^2)(1 - r_{YZ}^2)}}$$

### Wyniki w QSE (Java GT, n=59)

| Korelacja | Spearman ρ | p | Partial r | p |
|---|---:|---:|---:|---:|
| AGQ vs Panel Score | 0.380 | 0.003 | **0.447** | **0.0004** |
| Stability vs Panel Score | wysoki | istotny | 0.570 | 0.001 |

**Kluczowy wynik:** Partial r = 0.447 (p=0.0004) — po kontroli rozmiaru korelacja AGQ z jakością **rośnie** (0.380 → 0.447). Oznacza to, że rozmiar nie jest confounderem faworyzującym AGQ — wręcz trochę maskuje związek.

### Partial Spearman w eksperymencie Java-S

Eksperyment Java-S (kalibracja wag AGQ dla Java) używał partial Spearmana jako głównej miary jakości formuły. Wyniki:

| Wagi M/A/S/C/CD | Partial r | p |
|---|---:|---:|
| v3a: 0.20/0.20/0.20/0.20/0.20 | 0.675 | 0.008 |
| v3c (winner): 0.20/0.20/0.20/0.20/0.20 | **najlepszy** | p<0.01 |
| Bez Stability (S): | 0.274 | ns |

Stability jest kluczowa: bez S partial_r spada do 0.274 (nieistotne statystycznie).

### Interpretacja wartości

| |r_partial| | Siła |
|---|---|
| 0.00 – 0.20 | Bardzo słaba |
| 0.20 – 0.40 | Słaba |
| 0.40 – 0.60 | Umiarkowana |
| 0.60 – 0.80 | Silna |
| 0.80 – 1.00 | Bardzo silna |

AGQ partial r = 0.447 → **umiarkowana** korelacja (istotna statystycznie).

## Definicja formalna

Niech X, Y, Z będą zmiennymi losowymi. Partial Spearman(X, Y | Z) obliczana jest przez:

1. Obliczenie rang X → X_r, rang Y → Y_r, rang Z → Z_r
2. Regresja X_r na Z_r, wyodrębnienie reszt: ε_X = X_r - ŷ_X
3. Regresja Y_r na Z_r, wyodrębnienie reszt: ε_Y = Y_r - ŷ_Y
4. r_partial = Pearson(ε_X, ε_Y)

W praktyce QSE: Z = log(n_nodes) — logarytmowana liczba węzłów jako przybliżenie rozmiaru projektu.

## Zobacz też

- [[Mann-Whitney|Mann-Whitney]] — test dla różnic między grupami
- [[GT|GT]] — Ground Truth jako źródło Y (Panel Score)
- [[AGQ|AGQ]] — źródło X
- [[07 Benchmarks/Java GT Dataset|Java GT Dataset]] — pełne wyniki
- [[Glossary for Non-Technical Readers|Statystyka prostymi słowami]] — dla niefachowców
