---
type: formula
status: active-experiment
language: pl
languages: [java]
components: [M, A, S, C, CD]
---

# AGQv2

## Prostymi słowami

AGQv2 to pierwsza formuła AGQ, która przyniosła istotny statystycznie wynik. Odpowiada na konkretne pytanie: skoro [[Stability]] z wagą 0.55 nie działała (bo BLT był błędnym GT), to co dodać i jak przepisać wagi? Odpowiedź: dodaj metrykę gęstości powiązań ([[CD]]), zredukuj wagę S z 0.55 do 0.15, i sprawdź na panelu ekspertów. Wynik: partial r=0.675, p=0.008 — pierwszy prawdziwy sygnał.

## Szczegółowy opis

### Wzór

```
AGQv2 = 0.30·M + 0.20·A + 0.15·S + 0.15·C + 0.20·CD
```

Pięć składowych. Dodano [[CD]] (*Coupling Density*). Waga [[Stability]] zredukowana z 0.55 do 0.15 po obaleniu W2.

### Dlaczego takie wagi — kroki projektowe

**Krok 1: Obalenie W2**
Panel GT (n=14, Java) wykazał, że [[Stability]] samodzielnie nie discriminuje POS od NEG (p=0.155). Waga S=0.55 w AGQv1 była błędna. Redukcja: S=0.55 → S=0.15.

**Krok 2: Dodanie CD**
[[CD]] (*Coupling Density*) mierzy gęstość krawędzi w grafie zależności:
```
CD = 1 − (liczba_krawędzi / możliwe_krawędzie)
```
Projekty z niską gęstością powiązań (rzadki graf) mają wyższe CD. Hipoteza: gęstość zależności koreluje z jakością architektury.

**Krok 3: Redystrybucja wag**
Zwiększono wagę M z 0.20 do 0.30 i dodano CD=0.20. Uzasadnienie: po zmniejszeniu S pojawia się miejsce dla nowego sygnału.

### Walidacja na panelu Java n=14

Eksperyment E2 (eksperymenty walidacji CD):

| Metryka | Wartość | Interpretacja |
|---|---|---|
| Partial r (po kontroli rozmiaru) | **0.675** | Umiarkowana korelacja z oceną panelową |
| p-value | **0.008** | Istotna statystycznie (< 0.01) |
| n | 14 | Panel Java, małe n |
| Wcześniejsze wyniki | p > 0.10 | Przed dodaniem CD |

To był **przełomowy moment** projektu: po raz pierwszy AGQ wykazało statystycznie istotną korelację z oceną ekspertów po kontrolowaniu za rozmiar projektu.

### Macierz korelacji składowych AGQv2 (n=357)

Z danych `correlation_matrix_v1.json`:

| Para | Pearson r | Interpretacja |
|---|---|---|
| S ↔ AGQv2 | **0.852** | Tautologia — S dominuje AGQv2 (nadmiarowość) |
| CD ↔ AGQv2 | 0.571 | CD istotnie wnosi |
| A ↔ CD | 0.267 | Nieznaczna zależność |
| M ↔ S | −0.203 | Lekka ujemna korelacja |
| M ↔ C | −0.254 | Lekka ujemna korelacja |

**Kluczowy problem:** S ↔ AGQv2 r=0.852 — Stability dominuje wynik AGQv2 prawie tautologicznie (bo S ma wagę 0.35 łącznie między AGQv1 a v2). To jeden z powodów przejścia do AGQv3c z równymi wagami.

### Zmiany wzorców na benchmarku (n=78, Python)

| Statystyka | AGQv1 | AGQv2 | Δ |
|---|---|---|---|
| Średnia AGQ | 0.6688 | 0.7935 | +0.1247 |
| Spread | 0.2863 | 0.3373 | +0.051 |
| Acyclicity średnia | 0.9767 | 0.9776 | +0.001 |
| Stability średnia | 0.3131 | 0.8113 | +0.498 |

**Uwaga:** Wzrost Stability z 0.31 do 0.81 między v1 a v2 to zmiana sposobu obliczania metryki (v2 używa `instability_variance` per węzeł), nie zmiana rzeczywistych projektów.

### AGQv2 vs AGQv1 — per repo (wybrane przykłady)

| Repo | AGQv1 | AGQv2 | Δ | Uwaga |
|---|---|---|---|---|
| pytest | 0.6667 | 0.8056 | +0.139 | Duży zysk |
| youtube-dl | 0.6437 | 0.8761 | +0.232 | Bardzo duży zysk |
| flask | 0.5577 | 0.6294 | +0.072 | Mały zysk |
| pygments | 0.8440 | 0.8540 | +0.010 | Minimalny zysk |

Projekty z dużą liczbą powiązań między modułami (niskie CD) zyskują mniej na AGQv2.

### Kontekst: AGQv2 a AGQv3c

AGQv2 ma wagi 0.30/0.20/0.15/0.15/0.20 — historycznie uzasadnione, ale nie wyznaczone przez PCA. AGQv3c (Java) upraszcza do równych 0.20 po stwierdzeniu, że eigenvalues PCA są prawie identyczne — brak empirycznego uzasadnienia dla nierównych wag.

AGQv2 pozostaje **wariantem rezerwowym** eksperymentu Java-S (lista rezerwowa po AGQv3c).

## Definicja formalna

\[
\text{AGQv2} = 0.30 \cdot M + 0.20 \cdot A + 0.15 \cdot S + 0.15 \cdot C + 0.20 \cdot CD
\]

Składowe:
- \(M\) = Modularity ∈ [0,1], Louvain → max(0, Q)/0.75
- \(A\) = Acyclicity ∈ [0,1], Tarjan → 1 − max_SCC/n_internal
- \(S\) = Stability ∈ [0,1], instability_variance per pakiet / 0.25
- \(C\) = Cohesion ∈ [0,1], 1 − mean(LCOM4−1)/max_LCOM4
- \(CD\) = Coupling Density ∈ [0,1], 1 − (edges / possible_edges)

**Wyniki walidacji:**
- Panel Java n=14: partial r=0.675, p=0.008 ✅
- Pierwszy istotny statystycznie wynik w historii projektu

**Ograniczenia:**
- Java-specific (nie testowana empirycznie na Python GT)
- Mały n=14 na panelu — wyniki wymagają replikacji
- S ↔ AGQv2 r=0.852 — problem tautologiczny (rozwiązany przez AGQv3c)

## Zobacz też

- [[AGQ Formulas]] — tabela wszystkich wersji
- [[AGQv1]] — poprzednia wersja, dlaczego S=0.55 nie działało
- [[AGQv3c Java]] — następna wersja: PCA equal weights, rozszerzony GT
- [[CD]] — nowa składowa dodana w v2
- [[Stability]] — składowa zredukowana z 0.55 do 0.15
- [[Ground Truth]] — panel ekspertów n=14
