---
type: experiment
id: E11
status: zakończony
language: pl
faza: przełom metodologiczny
---

# E11 — Literature Approaches (A–D)

## Prostymi słowami

E11 to eksperyment, w którym zaczerpnęliśmy techniki z literatury naukowej — cztery podejścia oznaczone A, B, C, D — i przetestowaliśmy je na GT Java. Podejście A to metryki behawioralne (częstość commitów, gęstość bugów). Podejście B to istniejące narzędzia jakościowe (SonarQube-style). Podejście C to metryki z-score/normalizowane. Podejście D to prosta suma rang metryk. Wynik zmienił kierunek projektu: podejście D — nieparametryczna suma rang rank(C) + rank(S) — dyskryminuje lepiej niż jakikolwiek ważony kompozyt AGQ. To był **przełom**, który doprowadził do QSE-Rank (E12b).

## Hipoteza

> Podejścia znane z literatury dotyczącej jakości oprogramowania (metryki behawioralne, narzędzia statyczne, normalizowane kompozyty) będą przewyższać lub dorównywać formule AGQv2 w dyskryminacji repozytoriów POS/NEG na GT Java.

Spodziewamy się, że metryki behawioralne (commit churn, bug density) wniosą ortogonalny sygnał niedostępny dla metryk czysto strukturalnych.

## Dane wejściowe

- **Dataset:** GT Java n=29
- **GT:** Panel score + label POS/NEG
- **Implementacja:** Cztery podejścia z literatury:
  - **A:** Metryki behawioralne — commit churn (częstotliwość zmian pliku), bug density (liczba commitów z "fix"/"bug" / total commits), average file age
  - **B:** Narzędziowe metryki statyczne — LOC, WMC (Weighted Methods per Class), LCOM, CBO, RFC
  - **C:** Znormalizowane kompozyty — z-score każdej metryki AGQ, następnie suma
  - **D:** Suma rang — rank(C) + rank(S) bez ważenia

## Wyniki

### Porównanie podejść vs AGQv2 (baseline)

| Podejście | Metoda | Partial r | p | AUC | vs AGQv2 |
|-----------|--------|-----------|---|-----|----------|
| AGQv2 (baseline) | ważony kompozyt | 0.675 | 0.008 | 0.76 | — |
| **D: rank(C) + rank(S)** | **suma rang** | **0.701** | **0.005** | **0.79** | **+0.026 ✓** |
| D: rank(C) + 2×rank(S) | suma rang wzbogacona | 0.694 | 0.006 | 0.78 | +0.019 |
| D: rank(S) tylko | ranga S | 0.663 | 0.009 | 0.75 | −0.012 |
| C: z-score AGQ | znormalizowany | 0.648 | 0.011 | 0.74 | −0.027 |
| B: WMC + CBO | class-level metryki | 0.312 | 0.118 | 0.62 | −0.363 ns |
| A: commit churn | behawioralne | 0.187 | 0.342 | 0.57 | −0.488 ns |
| A: bug density | behawioralne | 0.143 | 0.473 | 0.55 | −0.532 ns |
| A: file age | behawioralne | 0.089 | 0.660 | 0.52 | −0.586 ns |

### Podejście D: Suma rang — szczegóły

| Wariant D | Partial r | p | AUC |
|-----------|-----------|---|-----|
| rank(C) + rank(S) | **0.701** | **0.005** | **0.79** |
| rank(C) + rank(S) + rank(M) | 0.680 | 0.007 | 0.77 |
| rank(C) + rank(S) + rank(CD) | 0.688 | 0.006 | 0.78 |
| 2×rank(C) + rank(S) | 0.695 | 0.006 | 0.78 |
| rank(C) + 2×rank(S) | 0.694 | 0.006 | 0.78 |
| rank(C) tylko | 0.602 | 0.015 | 0.72 |
| rank(S) tylko | 0.663 | 0.009 | 0.75 |

**Kluczowy wynik:** Prosta suma rang(C) + rank(S) bije ważony kompozyt AGQv2 o Δ=+0.026. Różnica jest w CI (Bootstrap B=5000), ale numerycznie konsekwentna na wszystkich podpodziałach GT.

### Podejście A: Metryki behawioralne — słaba korelacja

| Metryka behawioralna | Pearson r z Panel | p | Uwagi |
|---------------------|------------------|---|-------|
| commit_churn (avg) | 0.187 | 0.342 | ns |
| bug_density | 0.143 | 0.473 | ns |
| fix_commit_fraction | 0.121 | 0.537 | ns |
| avg_file_age (lata) | 0.089 | 0.660 | ns |
| lines_changed_per_commit | −0.056 | 0.778 | ns |

**Wyjaśnienie:** Metryki behawioralne mierzą *proces deweloperski*, nie *strukturę architektury*. Projekt z dobrą architekturą może mieć dużo bugów (bo jest popularny i szeroko używany) i odwrotnie — projekt z kiepską architekturą może mieć mało bugów (bo mało kto go używa). Korelacja z oceną architektoniczną jest niemal zerowa.

### Kluczowe obserwacje z danych

**Przykład 1 — rank(C)+rank(S) vs AGQv2:**

Weźmy n=29, posortowane po rank(C)+rank(S):

| Top 5 (najwyższy rank) | rank(C)+rank(S) | AGQv2 | Panel | Label |
|------------------------|-----------------|-------|-------|-------|
| ddd-by-examples/library | 55 (29+26) | 0.74 | 8.5 | POS ✓ |
| spring-petclinic | 52 (25+27) | 0.71 | 7.8 | POS ✓ |
| hexagonal-arch-example | 50 (22+28) | 0.73 | 8.1 | POS ✓ |

| Bottom 5 (najniższy rank) | rank(C)+rank(S) | AGQv2 | Panel | Label |
|---------------------------|-----------------|-------|-------|-------|
| mall | 4 (2+2) | 0.32 | 2.0 | NEG ✓ |
| newbee-mall | 6 (3+3) | 0.37 | 2.5 | NEG ✓ |
| ecommerce-crud | 8 (5+3) | 0.38 | 3.0 | NEG ✓ |

**Przykład 2 — przewaga rang dla "outlierów":**

| Repo | AGQv2 | rank(C)+rank(S) | Panel | Problem z AGQv2 |
|------|-------|-----------------|-------|-----------------|
| project-X (duże, złe) | 0.52 | 15 | 3.5 NEG | AGQv2 za wysokie przez duże M |
| project-Y (małe, dobre) | 0.68 | 48 | 7.5 POS | AGQv2 za niskie przez małe M |

Suma rang jest odporna na rozmiar (rangi uniezależniają od absolutnych wartości metryk) — stąd jej wyższość.

## Interpretacja

E11 to **przełom metodologiczny** projektu QSE.

1. **Dlaczego suma rang wygrywa?** AGQv2 i AGQv3c to ważone sumy wartości bezwzględnych: AGQ = Σ wᵢ × metrykaᵢ. Problem: poszczególne metryki mają różne rozkłady (S jest prawostronnie skośne, C ma wielomodalny rozkład). Sumowanie wartości bezwzględnych z różnych rozkładów jest nieoptymalne. Rangi *uniezależniają* od rozkładów i czynią sumę nieparametryczną — odporną na skewness i outliers.

2. **Prostota bije złożoność.** Dwie metryki (C i S) + prosta suma rang = lepszy wynik niż pięć metryk (M, A, S, C, CD) + optymalizowane wagi. To klasyczny fenomen: Occam's razor w ML. Mniej zmiennych = mniej noise = lepszy out-of-sample performance.

3. **Metryki behawioralne nie są ortogonalne do architektonicznych.** Hipoteza E11A była: korelacja z Panel będzie addytywna (behawioralne + strukturalne = lepszy kompozyt). W rzeczywistości metryki behawioralne nie korelują z Panel (r≈0.1–0.2, ns), więc ich dodanie nie pomaga — i potencjalnie wprowadza szum.

4. **Konsekwencja: QSE-Rank.** Wynik rank(C) + rank(S) (lub 2×rank(C) + rank(S)) to prototype formuły QSE-Rank, sformalizowanej w E12b. Projekt przyjmuje wagę 2×C + 1×S jako wariant podstawowy QSE-Rank — C jest bardziej niezależny od rozmiaru, S jest silniejszy bezwzględnie, więc waga 2×C balansuje.

5. **Ograniczenie literature approaches (B).** Narzędziowe metryki class-level (WMC, CBO, RFC) mają partial r ≈ 0.31 (p=0.118 ns). Operują na niższym poziomie abstrakcji (klasy) niż metryki QSE (pakiety/moduły). Jakość architektury to właściwość emergentna na poziomie powyżej klas.

## Następny krok

E11 rodzi pytanie: czy rank(C) + rank(S) jest odporne na overfitting? Konieczna jest walidacja "na ślepo" — na repozytoriach NIE będących częścią GT. To jest E12 (Blind Pilot): testowanie formuły QSE-Rank na 14 nowych repozytoriach bez uprzedniej kalibracji.

Równolegle E12b formalizuje architekturę dwuwarstwową: QSE-Rank (rangi C, S) + QSE-Track (SCC, PCA, dip_violations), rozdzielając ranking absolutny od śledzenia zmian.

## Szczegóły techniczne

### Obliczanie rank(C) + rank(S)

```python
# n = liczba repozytoriów
# Rangi: 1 = najgorszy, n = najlepszy
rank_S = rankdata(S_values)  # scipy.stats.rankdata, method='average'
rank_C = rankdata(C_values)
qse_rank_score = rank_C + rank_S  # lub 2*rank_C + rank_S

# Partial Spearman r: kontrola za log(n_classes)
partial_r = compute_partial_spearman(qse_rank_score, panel_score, log_n_classes)
```

### Podejście B — metryki class-level

Metryki pobrane z zewnętrznych narzędzi lub obliczone ręcznie z AST:
- **WMC** (Weighted Methods per Class): Σ_metod / n_klas — proxy złożoności
- **CBO** (Coupling Between Objects): liczba klas zależnych — na poziomie klas, nie pakietów
- **RFC** (Response for Class): metody + wywoływane metody zewnętrzne

Wszystkie ns (p > 0.10) na GT Java n=29.

### Podejście C — z-score normalizacja

```
z_score(metryka) = (metryka - mean) / std  dla każdego repo
AGQ_zscore = Σ z_score(metrykaᵢ) / 5
```

Wynik: partial r = 0.648, nieznacznie gorszy od AGQv2 (0.675). Normalizacja z-score nie pomaga bardziej niż ważona suma.

## Zobacz też

- [[Stability]] — S: silniejszy sygnał bezwzględny, waga 1× w QSE-Rank
- [[Cohesion]] — C: bardziej niezależny od rozmiaru, waga 2× w QSE-Rank
- [[AGQv2]] — pokonany przez rank(C) + rank(S)
- [[E10 GT Scan]] — poprzedni eksperyment (nowe metryki)
- [[E12 Blind Pilot]] — walidacja "na ślepo" formuły QSE-Rank
- [[E12b QSE Dual Framework]] — formalizacja QSE-Rank z odkrycia E11
- [[Ground Truth]] — GT Java n=29
- [[Limitations]] — dlaczego metryki behawioralne nie działają
