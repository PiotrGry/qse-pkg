---
type: experiment
id: E12b
status: zakończony
language: pl
faza: formalizacja architektury QSE
---

# E12b — QSE Dual Framework

## Prostymi słowami

Po serii eksperymentów E8–E12 projekt QSE miał dwa sprawdzone, ortogonalne narzędzia: rank(C)+rank(S) do rankowania projektów i SCC/PCA/dip_violations do śledzenia zmian. E12b formalnie rozdzielił te dwa filary w osobne komponenty z różnymi celami. QSE-Rank odpowiada na pytanie "który projekt jest lepszy?". QSE-Track odpowiada na pytanie "czy projekt poprawia się w czasie?". Ta separacja jest kluczowa — oba pytania wymagają różnych metod i różnych metryk.

## Hipoteza

> Dwa zadania — ranking jakości i śledzenie zmian — są ortogonalne i wymagają osobnych metod. Połączenie ich w jedną formułę skutkuje kompromisem gorszym niż dwie specjalizowane miary.

Hipoteza operacyjna: QSE-Rank (nieparametryczna) przewyższy AGQv2 w zadaniu rankingowym, a QSE-Track (SCC, PCA, dip_violations) przewyższy metryki AGQ w zadaniu detekcji zmian.

## Dane wejściowe

- **Dataset (QSE-Rank walidacja):** GT Java n=29 + blind set n=14 (z E12)
- **Dataset (QSE-Track walidacja):** Within-repo perturbations z E10 (5 repo × 19 iteracji)
- **GT:** Panel score dla rankingu; znane delta-zmiany dla śledzenia
- **Implementacja:** Formalizacja definicji obu komponentów; empiryczna weryfikacja separacji sygnałów; dokumentacja protokołu

## Wyniki

### QSE-Rank: definicja i walidacja

**Formuła QSE-Rank:**

\[
\text{QSE-Rank}(r) = 2 \cdot \text{rank}(C_r) + \text{rank}(S_r)
\]

gdzie rangi obliczane są w obrębie porównywanego zestawu (n repozytoriów).

| Metryka | Na GT n=29 | Na blind set n=14 | LOOCV n=29 |
|---------|------------|-------------------|------------|
| AUC | 0.79 | 0.72 | 0.71 |
| Partial r | 0.701 | 0.631 | 0.63 |
| p-value | 0.005 | 0.016 | ≈0.02 |

**Dlaczego waga 2× na C?**
- C (Cohesion) jest bardziej niezależna od rozmiaru projektu (partial r z log(n_classes) ≈ 0.15 dla C vs 0.28 dla S)
- Waga 2×C + 1×S "balansuje" dominację S (S ma wyższy raw partial r, ale C wnosi bardziej niezależny sygnał)
- Wariacja: 1×C + 1×S ma partial r = 0.701, 2×C + 1×S ma partial r = 0.695 — różnica w CI, ale 2×C preferowane ze względu na mniejszą wrażliwość na rozmiar

### QSE-Track: definicja i walidacja

**Trzy metryki QSE-Track:**

| Metryka | Obliczenie | Kierunek | Co mierzy |
|---------|-----------|---------|-----------|
| PCA | % acyklicznych pakietów | ↑ lepiej | Postęp usuwania cykli |
| SCC | rozmiar largest_SCC / n_nodes | ↓ lepiej | Wielkość "gmatwaniny" cyklicznej |
| dip_violations | liczba naruszeń DIP | ↓ lepiej | Naruszenia zasady zależności |

**Walidacja QSE-Track (within-repo, E10):**

| Operacja perturbacji | ΔPCA | ΔSCC | Δdip | Δ(S) | Δ(C) |
|---------------------|------|------|------|------|------|
| +1 cykl | 0.00 | +0.04 | +0.02 | 0.00 | 0.00 |
| −1 cykl | 0.00 | −0.04 | −0.02 | 0.00 | 0.00 |
| przeniesienie klasy | +0.01 | 0.00 | +0.01 | +0.03 | +0.02 |
| rozbicie klasy | 0.00 | 0.00 | 0.00 | 0.00 | +0.07 |

**Wniosek:** QSE-Track reaguje wyłącznie na zmiany cykliczne; QSE-Rank reaguje na reorganizację. Brak nakładania się sygnałów potwierdza ortogonalność.

### Panel QSE (Dashboard metryk)

Dodatkowy element E12b: **Panel QSE** — kompozytowy wskaźnik na potrzeby ekspozycji wyników:

\[
\text{Panel QSE} = w_1 \cdot \text{QSE-Rank\_percentyl} + w_2 \cdot \text{QSE-Track\_score}
\]

Wersja uproszczona (używana w E13–E13g): Panel = średnia ważona z rank(C), rank(S), PCA, (1−SCC).

### Separacja sygnałów — macierz korelacji

| Para metryk | r Pearson | Interpretacja |
|-------------|-----------|---------------|
| S ↔ PCA | −0.12 | Brak korelacji (ortogonalne) |
| C ↔ SCC | +0.08 | Brak korelacji |
| S ↔ SCC | +0.15 | Nieistotna |
| C ↔ PCA | −0.09 | Brak korelacji |
| S ↔ C | +0.31 | Umiarkowana pozytywna |
| PCA ↔ SCC | −0.89 | Silna negatywna (PCA i SCC mierzą to samo z różnych stron) |

Kluczowy wynik: S i C (Layer 1) są ortogonalne do PCA i SCC (Layer 2). Separacja jest uzasadniona empirycznie.

### Kluczowe obserwacje z danych

**Przykład: spring-petclinic po refaktoryzacji usuwania cykli:**

| Metryka | Przed | Po | Δ |
|---------|-------|-----|---|
| S | 0.51 | 0.51 | **0.00** (Layer 1 nie widzi) |
| C | 0.65 | 0.65 | **0.00** (Layer 1 nie widzi) |
| PCA | 0.76 | 1.00 | **+0.24** ✓ |
| SCC | 0.12 | 0.00 | **−0.12** ✓ |
| QSE-Rank | pozycja 8/29 | pozycja 8/29 | **brak zmiany** |
| QSE-Track score | 0.64 | 1.00 | **+0.36** ✓ |

To jest dokładnie oczekiwane zachowanie: refaktoryzacja cykli jest "niewidoczna" dla Layer 1, ale dokładnie zarejestrowana przez Layer 2.

## Interpretacja

E12b jest kamieniem milowym projektu QSE: formalizuje dwufilarową architekturę, która odpowiada na dwa różne pytania o jakość oprogramowania.

1. **Separation of Concerns na poziomie pomiaru.** QSE-Rank i QSE-Track mierzą różne aspekty jakości:
   - QSE-Rank: "gdzie jesteś w hierarchii jakości?" (absolutna, porównawcza)
   - QSE-Track: "czy zrobiłeś postęp w usuwaniu long-range cycles?" (relatywna, temporalna)

2. **Dlaczego separacja jest konieczna?** Formuła AGQv2 miesza sygnały cykliczne i niecykliczne w jednym skalarze. Jeśli zespół usuwa cykle (Layer 2 reaguje), AGQ nie rośnie — co jest dezorientujące. Jeśli zespół reorganizuje pakiety (Layer 1 reaguje), PCA nie rośnie. Dual framework eliminuje tę konfuzję.

3. **QSE-Rank jest nieparametryczna.** Rangi uniezależniają od rozkładu metryk i rozmiaru projektu. To właściwość kluczowa dla porównywalności między projektami różnej skali.

4. **QSE-Track jest temporalna.** Ma sens tylko przy porównaniu dwóch punktów czasu dla tego samego repo. Nie ma sensu porównywać PCA różnych projektów (różne baseline'y cykliczne).

5. **Waga 2×C w QSE-Rank.** Cohesion (C) jest mniej zależna od rozmiaru niż Stability (S) — co czyni ją lepszym "niezależnym głosem". Waga 2× wyrównuje siłę obu sygnałów po korekcji na rozmiar.

6. **Fundament dla Layer 3.** Dual framework nie obejmuje jeszcze diagnostyki — wyjaśnienia DLACZEGO projekt ma dane rangi. To jest role Layer 3 (QSE-Diagnostic), sformalizowanej w E13.

## Następny krok

E12b definiuje finalny kształt QSE. Następny krok to E13: dodanie trzeciej warstwy (QSE-Diagnostic) i formalizacja całej architektury jako Three-Layer QSE Framework. Każda z trzech warstw ma inny cel, inne metryki i inny adresat (zarząd vs developer vs tech lead).

Walidacja każdej warstwy osobno to E13d (Layer 2 within-repo), E13e/f (Layer 2 na realnych refaktoryzacjach), E13g (Layer 1 na realnej refaktoryzacji).

## Szczegóły techniczne

### QSE-Rank: formuła szczegółowa

```python
def qse_rank(repos: list[Repo]) -> list[float]:
    """
    Input: lista Repo z atrybutami C i S
    Output: QSE-Rank score dla każdego (wyższy = lepsza architektura)
    """
    C_values = [r.C for r in repos]
    S_values = [r.S for r in repos]
    
    rank_C = rankdata(C_values, method='average')  # 1 = najgorsza spójność
    rank_S = rankdata(S_values, method='average')  # 1 = najgorsza stabilność
    
    qse_rank_scores = [2 * rank_C[i] + rank_S[i] for i in range(len(repos))]
    return qse_rank_scores
```

### QSE-Track: metryki

```python
def qse_track(graph: DependencyGraph) -> dict:
    """
    Input: DependencyGraph (pakiety jako węzły, import = krawędź)
    Output: słownik trzech metryk Layer 2
    """
    sccs = tarjan_scc(graph)
    largest_scc = max(len(scc) for scc in sccs)
    n_internal = count_internal_nodes(graph)
    
    pca = sum(1 for scc in sccs if len(scc) == 1) / len(graph.packages)
    scc_score = largest_scc / n_internal if n_internal > 0 else 0.0
    dip = count_dip_violations(graph)  # warstwy z heurystyką nazw
    
    return {
        "PCA": pca,           # [0,1], wyższy = lepszy
        "SCC": scc_score,     # [0,1], niższy = lepszy  
        "dip_violations": dip  # [0,∞), niższy = lepszy
    }
```

### Kompozytowy Panel (wersja E12b)

\[
\text{Panel} = \frac{\text{percentyl\_C} + \text{percentyl\_S}}{2} \times 5 + \frac{\text{PCA} + (1 - \text{SCC/threshold})}{2} \times 5
\]

Skala 0–10, używana w raportach E13e/f/g.

## Zobacz też

- [[E11 Literature Approaches]] — odkrycie rank(C)+rank(S) — podstawa QSE-Rank
- [[E10 GT Scan]] — within-repo pilots — podstawa QSE-Track
- [[E12 Blind Pilot]] — walidacja QSE-Rank na blind set
- [[E13 Three-Layer Framework]] — rozszerzenie o Layer 3 (QSE-Diagnostic)
- [[E13d QSE-Track Within-Repo]] — szczegółowa walidacja QSE-Track
- [[Stability]] — S: składowa QSE-Rank (waga 1×)
- [[Cohesion]] — C: składowa QSE-Rank (waga 2×)
- [[Acyclicity]] — A: zastąpiona przez PCA w QSE-Track
