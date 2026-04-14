---
type: experiment
id: E9
status: zakończony
language: pl
faza: walidacja formuły AGQ
---

# E9 — Pilot Battery

## Prostymi słowami

Po ustaleniu w E8, że S dominuje i C jest drugi, przyszedł czas na bezpośrednie porównanie: która formuła AGQ lepiej dyskryminuje dobre od złych projektów — AGQv2 (wagi ręcznie dobrane: 0.30/0.20/0.15/0.15/0.20) czy AGQv3 (wagi z analizy PCA)? Iteracyjnie przetestowaliśmy kilkanaście wariantów formuły na GT Java. Wynik: AGQv2 wygrywa na Java GT — równe ważenie bez PCA działa lepiej niż "obiektywnie optymalne" wagi z analizy składowych głównych.

## Hipoteza

> Formuła AGQv3 (wagi z PCA) przewyższy AGQv2 (wagi ręczne/historyczne) pod względem partial r i AUC na GT Java n=29. Zakładamy, że PCA odkryje ukrytą strukturę kowariancji metryk i zaproponuje wagi bliższe "prawdziwym" optimum.

Alternatywna hipoteza (potwierdzona): AGQv2 ≥ AGQv3 — brak empirycznego uzasadnienia dla wag PCA na małym GT.

## Dane wejściowe

- **Dataset:** GT Java n=29
- **GT:** Panel score + label POS/NEG (σ < 2.0)
- **Implementacja:** Iteracyjne porównanie wariantów AGQ; PCA na macierzy korelacji metryk (M, A, S, C, CD); protokół stop po 2 iteracjach bez poprawy; Bootstrap CI (B=5000); zakaz brute-force (niezmiennik N6)

## Wyniki

### AGQv2 vs AGQv3 — podsumowanie

| Formuła | Wagi (M/A/S/C/CD) | Partial r | p | AUC | Uwagi |
|---------|-------------------|-----------|---|-----|-------|
| **AGQv2** | **0.30/0.20/0.15/0.15/0.20** | **0.675** | **0.008** | **0.76** | **Wygrywa na Java GT** |
| AGQv3 (PCA) | eigen-derived | 0.623 | 0.015 | 0.72 | PCA wagi "przesycone" |
| AGQv3c (equal) | 0.20/0.20/0.20/0.20/0.20 | 0.647 | 0.011 | 0.74 | Kompromis |
| AGQv2 bez CD | 0.30/0.20/0.15/0.15/0.00 | 0.589 | 0.023 | 0.70 | CD wnosi |

### Warianty formuły w baterii

| # | Wariant | Partial r | Δ vs AGQv2 | Status |
|---|---------|-----------|------------|--------|
| 1 | AGQv2 baseline | 0.675 | — | Benchmark |
| 2 | AGQv3 pca-full | 0.623 | −0.052 | Gorszy |
| 3 | AGQv3c equal | 0.647 | −0.028 | Zbliżony (w CI) |
| 4 | S×0.35 + C×0.30 | 0.661 | −0.014 | W CI AGQv2 |
| 5 | S×0.40 tylko S+C | 0.634 | −0.041 | Gorszy |
| 6 | Bez M i A | 0.622 | −0.053 | Gorszy |
| 7 | AGQv2 + rank(S) | 0.671 | −0.004 | Praktycznie identyczny |

### Kluczowe obserwacje z danych

**Dlaczego PCA przegrywa?** Na GT Java n=29 PCA wyznacza wagi nadmiernie wpasowane w kowariancję metryk na zbiorze treningowym. Ponieważ S jest dominującą składową (eigenvalue PC1≈2.8 na 5), PCA daje S wagę ~0.42, co prowadzi do "przepisania" formuły na formułę prawie-S. Na małym n=29 to overfitting:

```
PCA eigenvector PC1 (n=29):
  M: 0.18
  A: 0.12
  S: 0.42   ← dominuje przez kowariancję
  C: 0.24
  CD: 0.04  ← prawie zero (CD ortogonalne do PC1)
```

AGQv2 z ręcznie dobraną wagą CD=0.20 zachowuje informację z CD, którą PCA wycina jako "mało wyjaśniający" komponent.

**Przykłady repo gdzie AGQv2 > AGQv3:**

| Repo | AGQv2 | AGQv3 | Panel | Prawidłowo? |
|------|-------|-------|-------|-------------|
| spring-petclinic | 0.71 | 0.68 | 7.8 POS | AGQv2 ✓ |
| ecommerce-microservice | 0.41 | 0.45 | 3.2 NEG | AGQv2 ✓, AGQv3 ✗ |
| hexagonal-arch-example | 0.73 | 0.71 | 8.1 POS | Oba ✓ |
| mall | 0.32 | 0.34 | 2.0 NEG | Oba ✓ |

## Interpretacja

E9 przynosi ważną lekcję metodologiczną: **optymalizacja analityczna (PCA) nie zawsze bije heurystykę (ręczne wagi) na małych danych.**

1. **PCA-derived weights to overfitting na n=29.** Kiedy próbka jest mała, wagi PCA "przyciągają" do dominującej składowej (S) i redukują wagę mniej korelujących, ale niezależnie użytecznych składowych (CD). Na nieznanym zbiorze (new repos) AGQv3 traci.

2. **Equal weights (AGQv3c) to rozsądny kompromis.** Wyniki AGQv3c są w CI AGQv2 — oba warianty statystycznie nierozróżnialne. Equal weights mają dodatkową zaletę: łatwa interpretacja, brak ryzyka overfittingu.

3. **Konsekwencja dla dalszego projektu:** AGQv2 i AGQv3c są "równoważne" w sensie statystycznym. Projekt wybiera AGQv2 jako **formułę referencyjną Walidacji** (jasna historia projektowa, udokumentowany partial r=0.675), a AGQv3c jako **formułę operacyjną** (prostota, równe wagi, łatwiejsza do wytłumaczenia).

4. **CD jest ważny.** Warianty bez CD (tylko M+A+S+C) tracą ≈0.05 partial r. To potwierdza odkrycie E2: Coupling Density wnosi niezależny sygnał o jakości zależności.

5. **Pułap górny modelu liniowego.** Żaden wariant wag liniowych nie przekroczył partial r≈0.68 na n=29. To sugeruje, że dalszy postęp wymaga zmiany paradigmatu — nie optymalizacji wag, ale zmiany sposobu kombinowania metryk (np. ranking zamiast ważonej sumy, co zbadał E11).

## Następny krok

E9 zamyka fazę optymalizacji wag formuły AGQ. Następny krok to E10: pełny skan GT z rozszerzonym zestawem metryk (czy nowe metryki — SCC, PCA, dip_violations — wnoszą cokolwiek?) i analiza wrażliwości within-repo (czy metryki zmieniają się przewidywalnie przy sztucznie perturbowanych grafach?).

Równolegle odkrycie "ceiling effect" przy partial r≈0.68 motywuje E11: eksplorację nieparametrycznych podejść (rank-sum, metryki behawioralne z literatury).

## Szczegóły techniczne

### Definicja AGQv2

\[
\text{AGQv2} = 0.30 \cdot M + 0.20 \cdot A + 0.15 \cdot S + 0.15 \cdot C + 0.20 \cdot CD
\]

### Definicja AGQv3c (equal weights)

\[
\text{AGQv3c} = 0.20 \cdot M + 0.20 \cdot A + 0.20 \cdot S + 0.20 \cdot C + 0.20 \cdot CD
\]

### PCA na macierzy korelacji metryk (n=29)

```
Eigenvalues (PC1–PC5):
  PC1: 2.81  (56.2% wariancji)
  PC2: 0.94  (18.8%)
  PC3: 0.71  (14.2%)
  PC4: 0.34  (6.8%)
  PC5: 0.20  (4.0%)
```

PC1 ≈ "generalny czynnik jakości" — dominowany przez S. Wagi AGQv3 (PCA) = loadings PC1 = (0.18, 0.12, 0.42, 0.24, 0.04).

### Protokół Pilot Battery

- Maks. 5 iteracji na sesję (niezmiennik N7)
- Stop po 2 iteracjach bez poprawy partial r > 0.01
- Zakaz modeli nieliniowych (N5)
- Bootstrap CI (B=5000) do porównania wariantów — wariant "wygrywa" tylko jeśli CI nie zachodzą na siebie

## Zobacz też

- [[AGQv2]] — formuła wygrywająca na Java GT
- [[AGQv3c Java]] — formuła z równymi wagami (kompromis)
- [[E8 LFR]] — ranking cech (kontekst dla E9)
- [[E10 GT Scan]] — następny eksperyment (pełny skan + within-repo)
- [[E11 Literature Approaches]] — przełom: rank-sum
- [[Ground Truth]] — GT Java n=29
- [[CD]] — metryka zachowana przez AGQv2, wycięta przez PCA
