---
type: experiment
id: E8
status: zakończony
language: pl
sesja: 840eb81e, 0ffb1d34
faza: walidacja (kwiecień 2026)
---

# E8 — LFR (Large-scale Feature Ranking)

## Prostymi słowami

Mając już Ground Truth z 29 repozytoriów Java, zadaliśmy proste pytanie: która z czterech metryk (M, A, S, C) najsilniej przewiduje, czy projekt ma dobrą czy złą architekturę? Metodą statystyczną (partial Spearman r, korekta na rozmiar) zestawiliśmy każdą metrykę osobno z oceną panelu ekspertów. Wynik był jednoznaczny: Stability (S) dominuje — wyjaśnia największą część wariancji oceny jakości. Cohesion (C) jest wyraźnie na drugim miejscu. Modularity (M) i Acyclicity (A) wnoszą marginalnie.

## Hipoteza

> Poszczególne metryki (M, A, S, C) różnią się istotnie siłą predykcji oceny jakości architektonicznej. Spodziewamy się, że Stability (S) i Cohesion (C) będą silniejszymi predyktorami niż Modularity (M) i Acyclicity (A), co uzasadni ich dominującą rolę w formule AGQ.

Formalnie: rank(|partial_r(S)|) > rank(|partial_r(A)|) oraz rank(|partial_r(C)|) > rank(|partial_r(M)|) przy GT Java n=29.

## Dane wejściowe

- **Dataset:** GT Java n=29 (27 POS + NEG sklasyfikowanych według panelu ekspertów σ<2.0, z wykluczeniem repozytoriów kolekcji/archipelago)
- **GT:** Oceny panelu ekspertów: Panel score ∈ [1.0, 10.0], σ < 2.0, label = POS jeśli Panel ≥ 6.5, NEG jeśli Panel ≤ 4.5
- **Implementacja:** Obliczenie partial Spearman r między każdą metryką a Panel score, kontrolując za zmienną `log(n_classes)` jako konfundentę rozmiaru; Mann-Whitney U test dla różnicy POS vs NEG; AUC jako metryka dyskryminacyjna
- **Sesje:** 840eb81e, 0ffb1d34 (kwiecień 2026)

## Wyniki

### Ranking metryk według partial r (n=29)

| Metryka | Partial r | p-value | AUC (POS vs NEG) | Interpelacja |
|---------|-----------|---------|------------------|--------------|
| **S** (Stability) | **+0.593** | **0.001** | **0.74** | Dominuje |
| **C** (Cohesion) | **+0.441** | **0.018** | **0.68** | Drugi sygnał |
| M (Modularity) | +0.198 | 0.311 | 0.58 | Marginalny |
| A (Acyclicity) | +0.121 | 0.535 | 0.55 | Marginalny |

### Różnice median POS vs NEG

| Metryka | Mediana POS | Mediana NEG | Δ | Mann-Whitney p |
|---------|-------------|-------------|---|----------------|
| S | 0.344 | 0.238 | +0.106 | 0.016 * |
| C | 0.612 | 0.481 | +0.131 | 0.024 * |
| M | 0.523 | 0.478 | +0.045 | 0.311 ns |
| A | 0.871 | 0.832 | +0.039 | 0.535 ns |

### Kluczowe obserwacje z danych

**Przykłady repozytoriów — S i C jako dyskryminatory:**

| Repo | Label | S | C | Panel |
|------|-------|---|---|-------|
| ddd-by-examples/library | POS | 0.68 | 0.72 | 8.5 |
| spring-petclinic | POS | 0.51 | 0.65 | 7.8 |
| mall | NEG | 0.21 | 0.34 | 2.0 |
| newbee-mall | NEG | 0.21 | 0.29 | 2.5 |
| ecommerce-microservice | NEG | 0.18 | 0.40 | 3.2 |

**M i A — brak dyskryminacji:**
- Repozytoria architektury klasy NEG często mają wysoką Acyclicity (A≥0.80) — brak cykli to warunek konieczny, ale nie wystarczający dobrej architektury
- Modularity (M) jest podobna między POS i NEG, ponieważ detekcja społeczności Louvaina ma tendencję do tworzenia artificially balanced clusters niezależnie od jakości

**Paradoks A:** Projekt mall ma A=0.92 (prawie acykliczny) i Panel=2.0. Acykliczność to "higiena minimalna" — jej brak jest zły, ale jej obecność nie jest wyróżnikiem dobrego projektu.

## Interpretacja

E8 rozstrzyga kwestię hierarchii cech, która była niejasna po wcześniejszych eksperymentach E1–E7. Wcześniej w projekcie testowano czy S jest w ogóle przydatne (E1 obalił hierarchię S, E2 przyniósł CD). E8 pokazuje że:

1. **S dominuje wariancję AGQ.** Partial r=0.593 to silna korelacja. Wariancja instability (S) skutecznie oddziela projekty z wyraźną hierarchią warstwową od projektów "flat". Projekty POS mają S≈0.34 (widoczna hierarchia), NEG mają S≈0.24 (niemal flat).

2. **C jest realnym, niezależnym sygnałem.** Cohesion (C) koreluje z S umiarkowanie (r≈0.3), więc wnosi niezależną informację o jakości. Spójność klas to ortogonalny aspekt jakości — projekt może mieć dobrą hierarchię (wysokie S) ale kiepską spójność klas (niskie C), lub odwrotnie.

3. **M i A to "minimalne wymagania", nie dyskryminatory.** Acykliczność (A) jest blisko 1.0 dla większości repozytoriów — zarówno POS jak i NEG. Modularity (M) jest zbyt niestabilna analitycznie (Louvain ma element losowy, wyniki zmieniają się między uruchomieniami).

4. **Implikacja dla formuły AGQ:** Skoro M i A mają marginalny wkład, formuła z równymi wagami 0.20/0.20/0.20/0.20/0.20 (AGQv3c) może być suboptymalnie przydzielając 40% wagi metrycznym "szumom". E9 zbada czy zmiana wag poprawia wyniki.

5. **Dlaczego S, a nie C, dominuje?** S mierzy wariancję instability *na poziomie grafu zależności* — to właściwość globalna całej architektury. C mierzy spójność *na poziomie pojedynczych klas* — agregacja mniej stabilna. Projekty DDD by design mają wyraźną hierarchię stabilności (core vs infrastructure), podczas gdy dobre klasy mogą pojawiać się losowo nawet w złej architekturze.

## Następny krok

E8 ujawnia dominację S i użyteczność C. Naturalnym krokiem jest E9 (Pilot Battery): iteracyjne testowanie różnych wersji formuły AGQ (v2 vs v3) na GT, żeby sprawdzić czy zmiana wag lub formuły poprawi dyskryminację. Kluczowe pytanie E9: czy formuła z asymetrycznymi wagami (S×0.35, C×0.30) działa lepiej niż equal-weights v3?

Odkrycia E8 są też punktem wyjścia do E11, gdzie zadano pytanie odwrotne: czy zamiast ważonego kompozytu lepiej sprawdza się nieparametryczna suma rang?

## Szczegóły techniczne

### Metoda: Partial Spearman r

Partial Spearman r kontroluje za log(n_classes) — rozmiar projektu (confound):
1. Oblicz rang(metryki), rang(Panel score), rang(log(n_classes))
2. Oblicz residua rang(metryki) po regresji liniowej na rang(log(n_classes))
3. Oblicz residua rang(Panel score) po regresji liniowej na rang(log(n_classes))
4. Spearman r między residuami = partial r

**Dlaczego partial r?** Większe projekty mają tendencję do wyższych wartości zarówno metryk (więcej struktury) jak i Panel score (bardziej rozbudowane projekty przyciągają lepszych architektów). Bez korekty rozmiar "pompuje" korelacje.

### Obliczenia metryk

```
S = Stability = min(1.0, Var(I₁, ..., Iₖ) / 0.25)
   gdzie Iⱼ = fan_out(pakiet_j) / (fan_in(pakiet_j) + fan_out(pakiet_j))
   Normalizator 0.25 = max wariancja zmiennej binarnej

C = Cohesion = 1 − mean(LCOM4_i − 1) / max_lcom4_per_repo
   gdzie LCOM4_i = liczba spójnych składowych grafu metod klasy i

M = Modularity = max(0, Q_Louvain) / 0.75
   gdzie Q_Louvain = modularity score z algorytmu Louvain

A = Acyclicity = 1 − |max_SCC| / n_internal_nodes
   gdzie max_SCC = rozmiar największej silnie spójnej składowej
```

### Cytaty sesji

- Sesja 840eb81e: pierwsze uruchomienie LFR na n=29, wynik S-dominant
- Sesja 0ffb1d34: cross-check na podzbiorach, potwierdzenie dominacji S

## Zobacz też

- [[Stability]] — metryka dominująca (S)
- [[Cohesion]] — drugi dyskryminant (C)
- [[Modularity]] — metryka marginalna
- [[Acyclicity]] — metryka marginalna ("higiena minimalna")
- [[AGQv2]] — formuła testowana w E9 z wagami asymetrycznymi
- [[AGQv3c Java]] — formuła z równymi wagami, porównywana w E9
- [[Ground Truth]] — GT Java n=29 użyty w E8
- [[E7 P4 Java-S Expanded]] — poprzedni eksperyment (optymalizacja wag na n=59)
- [[E9 Pilot Battery]] — następny eksperyment (porównanie wersji AGQ)
- [[E11 Literature Approaches]] — odkrycie rank-sum jako alternatywy
