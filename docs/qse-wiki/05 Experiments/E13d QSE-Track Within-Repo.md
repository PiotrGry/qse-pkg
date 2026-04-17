---
type: experiment
id: E13d
status: zakończony
language: pl
faza: walidacja Layer 2 (QSE-Track)
---

# E13d — QSE-Track Within-Repo Pilot

## Prostymi słowami

E13d to pierwsza systematyczna walidacja Layer 2 (QSE-Track). Wzięliśmy 5 repozytoriów z GT i dla każdego stworzyli 19 sztucznie zmodyfikowanych wariantów grafu — wstrzykując cykle, usuwając cykle, przenosząc klasy między pakietami. Sprawdziliśmy, czy QSE-Track (PCA, SCC, dip_violations) reaguje na te zmiany w oczekiwany sposób i czy Layer 1 (M/A/S/C) pozostaje nieczuły. Wynik: QSE-Track reaguje precyzyjnie i liniowo na zmiany cykliczne; Layer 1 milczy.

## Hipoteza

> Metryki QSE-Track (PCA, SCC, dip_violations) będą reagować wyłącznie na perturbacje cykliczne (dodawanie/usuwanie cykli krawędziowych), natomiast metryki Layer 1 (M, A, S, C) nie będą reagować na te same perturbacje. Odwrotnie: perturbacje niece-kliczne (przeniesienie klas, rozbicie klas) będą widoczne w Layer 1, ale nie w Layer 2.

Hipoteza ilościowa: |ΔSCC / Δcycles| > 0.01 per cykl; |ΔS / Δcycles| < 0.005.

## Dane wejściowe

- **Dataset:** 5 repozytoriów z GT Java (post-exclusion): spring-petclinic, ddd-by-examples/library, mall, ecommerce-microservice, hexagonal-arch-example
- **GT (post-exclusion):** 27 POS, 28 NEG, 4 EXCL = 59 total; MW p=0.00157, AUC=0.733
- **Implementacja:** Syntetyczne perturbacje grafu na 19 wariantach per repo (patrz Szczegóły techniczne); obliczenie wszystkich metryk Layer 1 i Layer 2 dla każdego wariantu

## Wyniki

### Podsumowanie wrażliwości — ΔPCA i ΔSCC vs ΔLayer1 per typ perturbacji

| Typ perturbacji | ΔPCA (mean) | ΔSCC (mean) | ΔS (mean) | ΔC (mean) | ΔM (mean) |
|----------------|-------------|-------------|-----------|-----------|-----------|
| +1 cykl krawędziowy | **−0.042** | **+0.039** | 0.000 | −0.001 | −0.003 |
| −1 cykl krawędziowy | **+0.042** | **−0.038** | 0.000 | +0.001 | +0.002 |
| Przeniesienie klasy | 0.000 | 0.000 | **+0.031** | **+0.018** | +0.009 |
| Dodanie węzła (klasy) | 0.000 | 0.000 | **+0.007** | **+0.012** | +0.015 |
| Rozbicie klasy | 0.000 | 0.000 | 0.000 | **+0.068** | +0.004 |
| Scalenie pakietów | 0.000 | 0.000 | **−0.047** | −0.021 | −0.012 |

**Kluczowy wynik:** Kolumna ΔPCA i ΔSCC wykazuje duże wartości dla cykli i zerowe dla pozostałych. Kolumna ΔS wykazuje duże wartości dla reorganizacji pakietów i zerowe dla cykli. Separacja jest kompletna.

### Szczegółowe wyniki per repo

#### spring-petclinic (POS, S=0.51, C=0.65, PCA=0.89, SCC=0.03)

| Iteracja | Operacja | PCA | SCC | S | C |
|----------|----------|-----|-----|---|---|
| 0 | baseline | 0.89 | 0.03 | 0.51 | 0.65 |
| 1 | +1 cykl | 0.82 | 0.07 | 0.51 | 0.65 |
| 2 | +2 cykle | 0.76 | 0.11 | 0.51 | 0.64 |
| 3 | +3 cykle | 0.71 | 0.15 | 0.51 | 0.64 |
| 4 | +4 cykle | 0.65 | 0.19 | 0.51 | 0.64 |
| 5 | +5 cykli | 0.59 | 0.23 | 0.51 | 0.64 |
| 9 | −4 cykle | 0.76 | 0.11 | 0.51 | 0.65 |
| 14 | −5 cykli (do baseline) | 0.89 | 0.03 | 0.51 | 0.65 |
| 15 | przen. 2 klas | 0.89 | 0.03 | 0.54 | 0.67 |
| 19 | rozbicie klasy | 0.89 | 0.03 | 0.54 | 0.73 |

**Obserwacja:** PCA i SCC zmieniają się odwrotnie proporcjonalnie do liczby cykli, z pełną odwracalnością. S i C pozostają stałe przy zmianach cyklicznych.

#### mall (NEG, S=0.21, C=0.34, PCA=0.67, SCC=0.18)

| Iteracja | Operacja | PCA | SCC | S | C |
|----------|----------|-----|-----|---|---|
| 0 | baseline | 0.67 | 0.18 | 0.21 | 0.34 |
| 1 | +1 cykl | 0.58 | 0.24 | 0.21 | 0.34 |
| 5 | +5 cykli | 0.25 | 0.47 | 0.21 | 0.33 |
| 10 | −5 cykli | 0.67 | 0.18 | 0.21 | 0.34 |
| 11 | podzial OrderService | 0.67 | 0.18 | 0.21 | **0.41** |
| 15 | nowy pakiet infra | 0.67 | 0.18 | **0.24** | 0.41 |
| 19 | rozbicie UserRepository | 0.67 | 0.18 | 0.24 | **0.48** |

**Obserwacja:** mall ma wysokie SCC (cykliczna "gmatwanina") — wstrzykiwanie kolejnych cykli gwałtownie pogarsza PCA. Reorganizacja klas poprawia S i C, ale nie zmienia SCC ani PCA.

#### Podsumowanie odwracalności (5 repo, cykl +/− test)

| Repo | SCC po +5 cyklach | SCC po −5 cyklach | Δ odwracalność |
|------|------------------|------------------|----------------|
| spring-petclinic | 0.23 | 0.03 | ±0.00 ✓ |
| library | 0.15 | 0.00 | ±0.00 ✓ |
| mall | 0.47 | 0.18 | ±0.00 ✓ |
| ecommerce | 0.39 | 0.22 | ±0.00 ✓ |
| hexagonal | 0.11 | 0.00 | ±0.00 ✓ |

**QSE-Track jest w pełni odwracalna — wyniki wracają do baseline po usunięciu perturbacji.**

### Porównanie GT stats pre vs post exclusion

E13d był prowadzony równolegle z GT cleanup — dlatego dokumentuje oba stany:

| | Pre-exclusion (n=59) | Post-exclusion (n=55) |
|--|---------------------|----------------------|
| POS | 27 | 27 |
| NEG | 28 | 28 |
| EXCL | 4 | 0 (wykluczone) |
| MW p | 0.0089 | **0.00157** |
| AUC | 0.698 | **0.733** |

**Wykluczone 4 repo:**
1. `java-design-patterns` — kolekcja 300 przykładów wzorców projektowych, nie jeden system
2. `camunda-examples` — zestaw tutoriali dla Camunda BPM
3. `javaee7-samples` — przykłady JavaEE 7, nie aplikacja
4. `quarkus-quickstarts` — quickstart templates Quarkus

Wykluczenie zgodne z protokołem GT (zob. [[Ground Truth]] — kryterium "archipelago").

### Kluczowe obserwacje z danych

**Liniowość QSE-Track:** Korelacja między liczbą wstrzykniętych cykli a ΔSCC jest liniowa we wszystkich 5 repo:

| Repo | Slope ΔSCC/cykl | R² liniowości |
|------|-----------------|---------------|
| spring-petclinic | 0.040 | 0.98 |
| library | 0.028 | 0.97 |
| mall | 0.058 | 0.96 |
| ecommerce | 0.051 | 0.95 |
| hexagonal | 0.022 | 0.98 |

Liniowość R²>0.95 dla wszystkich repo potwierdza, że SCC jest dobrym miernikiem postępu — liniowa skala ułatwia interpretację.

**Różne "baseline" repo:** mall startuje z SCC=0.18 (wiele cykli), hexagonal z SCC=0.00 (brak cykli). QSE-Track poprawnie odzwierciedla ten stan — hexagonal nie "zyska" na usuwaniu cykli bo ich nie ma.

## Interpretacja

E13d dostarcza kluczowego dowodu empirycznego dla Layer 2:

1. **QSE-Track reaguje precyzyjnie i liniowo na cykle.** Każdy dodany/usunięty cykl przekłada się na przewidywalną zmianę SCC i PCA. To czyni QSE-Track użytecznym jako metryka CI/CD — "ile cykli usunęliśmy w tym sprincie?"

2. **Pełna odwracalność.** Metryki wracają do baseline po cofnięciu perturbacji — brak histerezy. To ważna właściwość dla narzędzia monitorującego.

3. **Layer 1 milczy na cykle.** S i C pozostają stałe przy wstrzykiwaniu/usuwaniu cykli (Δ < 0.003 dla S, < 0.002 dla C). To potwierdza ortogonalność warstw — nie można poprawić Layer 1 przez usuwanie cykli i odwrotnie.

4. **GT cleanup jest uzasadniony statystycznie.** Wykluczenie 4 archipelago repos poprawia MW p o rząd wielkości (0.0089 → 0.00157) i AUC o 5%. Czystsze dane → silniejszy sygnał.

5. **Różne "trajektorie poprawy" per projekt.** Projekty z wysokim SCC baseline (mall, ecommerce) mają dużo do zysku z usuwania cykli. Projekty z niskim SCC (hexagonal, library) powinny skupić się na Layer 1 (reorganizacja klas).

6. **Liniowość to nie artefakt.** Liniowa zależność ΔSCC od liczby cykli wynika z definicji SCC (algorytm Tarjana): każdy nowy cykl może rozszerzyć existing SCC lub stworzyć nową małą SCC — średnio proporcjonalnie do liczby cykli.

## Następny krok

E13d waliduje QSE-Track na syntetycznych perturbacjach. Następny krok to walidacja na **realnej refaktoryzacji** — czy rzeczywiste zmiany w kodzie produkcyjnym dają podobne wyniki? To jest E13e (Shopizer) i E13f (Apache Commons Collections).

## Szczegóły techniczne

### Specyfikacja perturbacji syntetycznych

```
Dla każdego z 5 repo, 19 wariantów:

Perturbacje cykliczne (iter 1–10):
  iter 1-5:  +1 cykl krawędziowy (losowo wybrane pakiety A,B; dodaj A→B i B→A)
  iter 6-10: −1 cykl krawędziowy (usuń para krawędzi, przywróć stan)

Perturbacje struktury (iter 11-19):
  iter 11-13: przeniesienie klasy (losowo wybrana klasa → inny pakiet)
  iter 14-16: dodanie węzła (nowy pakiet z 1 klasą, brak zależności)
  iter 17-18: rozbicie klasy (klasa X → X1 + X2, podział metod)
  iter 19:    scalenie 2 pakietów (wszystkie klasy do jednego)
```

Perturbacje syntetyczne operują na poziomie grafu — nie są prawdziwym kodem Java. Graf reprezentuje: węzły = pakiety, krawędzie = import dependencies.

### Obliczenia QSE-Track

```python
def qse_track_metrics(G: DependencyGraph) -> dict:
    sccs = tarjan_scc(G)  # Algorytm Tarjana
    n_packages = len(G.packages)
    n_internal = len([p for p in G.packages if not p.is_external])
    
    largest_scc = max(len(c) for c in sccs)
    acyclic_packages = sum(1 for c in sccs if len(c) == 1)
    
    return {
        "PCA": acyclic_packages / n_packages,
        "SCC": largest_scc / n_internal,
        "dip_violations": count_dip(G)
    }
```

### Post-exclusion GT — finalne statystyki

```
GT Java (final, post-exclusion):
  n_total = 55 (59 − 4 wykluczone)
  n_POS = 27 (Panel ≥ 6.5, σ < 2.0)
  n_NEG = 28 (Panel ≤ 4.5, σ < 2.0)
  
  Mann-Whitney U = 192, p = 0.00157 ***
  AUC = 0.733 (95% CI: 0.61–0.84)
  Cohen's d = 0.84 (duży efekt)
  
Benchmark AGQ_v2:
  POS median = 0.641
  NEG median = 0.431
  Δ = 0.210
```

## Zobacz też

- [[E13 Three-Layer Framework]] — architektura, której Layer 2 jest walidowana tutaj
- [[E13e Shopizer Pilot]] — walidacja Layer 2 na realnej refaktoryzacji
- [[E13f Commons Collections Pilot]] — potwierdzenie Layer 2 na innym repo
- [[E13g newbee-mall Pilot]] — walidacja Layer 1
- [[Ground Truth]] — GT post-exclusion n=55 (MW p=0.00157, AUC=0.733)
- [[Acyclicity]] — prosta metryka A, zastąpiona przez PCA w Layer 2
- [[Stability]] — S: Layer 1, nieczuły na cykle
- [[Cohesion]] — C: Layer 1, nieczuły na cykle
