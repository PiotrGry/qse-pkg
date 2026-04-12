---
type: glossary
language: pl
---

# Mann-Whitney U Test

## Prostymi słowami

Mann-Whitney to test statystyczny sprawdzający, czy dwie grupy są naprawdę różne, czy różnica to tylko przypadek. Wyobraź sobie, że mierzysz wzrost uczniów ze szkoły A i B. Mann-Whitney odpowiada: „czy szkoła A naprawdę ma wyższe dzieci, czy to losowe wahania?" W QSE: czy projekty POS (dobra architektura) naprawdę mają wyższy AGQ niż NEG, czy to przypadek?

## Szczegółowy opis

**Test Manna-Whitneya U** (inaczej: Wilcoxon rank-sum test) to nieparametryczny test statystyczny porównujący dwie niezależne grupy. Jest stosowany gdy dane nie spełniają założenia normalności (co jest typowe dla danych AGQ).

### Dlaczego nie t-test, a Mann-Whitney?

| Właściwość | t-test | Mann-Whitney |
|---|---|---|
| Zakładana rozkład | Normalny | Brak założeń |
| Typ danych | Ciągłe | Porządkowe lub ciągłe |
| Odporność na outliers | Słaba | Dobra |
| Zastosowanie w QSE | ❌ | ✅ |

AGQ przyjmuje wartości [0, 1] z nieznanym rozkładem — Mann-Whitney jest właściwym wyborem.

### Jak działa Mann-Whitney

1. Łączymy wszystkie obserwacje z obu grup i sortujemy
2. Przypisujemy rangi (1 = najniższa wartość)
3. Obliczamy statystykę U — sumę rang dla jednej z grup
4. Sprawdzamy, czy U jest istotnie różne od oczekiwanej wartości (gdyby grupy były identyczne)

Hipoteza zerowa H₀: grupy mają ten sam rozkład (brak różnicy).
Hipoteza alternatywna H₁: jedna grupa ma wyższe wartości.

### Wyniki w QSE (Java GT, n=59)

| Test | Statystyka | p-value |
|---|---:|---:|
| AGQ POS vs NEG | U = — | **p = 0.000221** |
| Acyclicity POS vs NEG | — | p = 0.030 (*) |
| Stability POS vs NEG | — | p = 0.016 (*) |
| Cohesion POS vs NEG | — | p = **0.0002 (***)** |
| Coupling Density POS vs NEG | — | p = 0.004 (**) |
| Modularity POS vs NEG | — | p = 0.226 (ns) |

p = 0.000221 dla AGQ oznacza: szansa, że różnica między POS a NEG jest przypadkowa, wynosi 0.022%. Przy standardowym progu α = 0.05 — wynik jest wysoce istotny.

### Interpretacja p-value

| p-value | Znaczenie | Symbol |
|---|---|---|
| > 0.05 | Nieistotne statystycznie | ns |
| 0.01 – 0.05 | Istotne | * |
| 0.001 – 0.01 | Wysoce istotne | ** |
| < 0.001 | Bardzo wysoce istotne | *** |

**Ważne:** istotność statystyczna ≠ istotność praktyczna. p < 0.001 mówi tylko, że różnica nie jest przypadkowa — nie jak duża jest różnica. Do tego służy **effect size** (np. Cohen's d lub AUC-ROC).

AUC-ROC = 0.767 (Java GT) = umiarkowanie silna klasyfikacja. Znacznie powyżej losowego klasyfikatora (AUC=0.5).

## Definicja formalna

Niech X = {x₁, ..., xₘ} (POS) i Y = {y₁, ..., yₙ} (NEG) będą zbiorami wartości AGQ. Statystyka U:

$$U = \sum_{i=1}^{m} \sum_{j=1}^{n} \mathbf{1}[x_i > y_j] + \frac{1}{2} \mathbf{1}[x_i = y_j]$$

Przy H₀ (brak różnicy): E[U] = mn/2. Test sprawdza czy U jest istotnie różne od E[U].

W QSE: test jednostronny (POS ma wyższy AGQ niż NEG, tj. H₁: $\bar{X} > \bar{Y}$).

## Zobacz też

- [[Partial Spearman|Partial Spearman]] — korelacja z kontrolą confounders
- [[GT|GT]] — metodologia zbioru walidacyjnego
- [[AGQ|AGQ]] — metryka poddawana testom
- [[07 Benchmarks/Java GT Dataset|Java GT Dataset]] — pełne wyniki testów
- [[Glossary for Non-Technical Readers|Statystyka prostymi słowami]]
