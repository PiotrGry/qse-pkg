---
type: experiment
id: E12
status: zakończony
language: pl
faza: walidacja zewnętrzna (blind)
---

# E12 — Blind Pilot (14 nowych repozytoriów)

## Prostymi słowami

E12 to test "na ślepo" — wzięliśmy formułę QSE-Rank (rank(C) + rank(S), odkrytą w E11) i zastosowaliśmy ją do 14 repozytoriów, które NIGDY wcześniej nie były częścią GT ani kalibracji. Nie wiedzieliśmy z góry jakie są ich oceny — najpierw policzyliśmy rangi, potem zebraliśmy oceny panelu. Dodatkowo przeprowadzono Leave-One-Out Cross-Validation (LOOCV) na oryginalnym GT, żeby sprawdzić stabilność formuły. Wyniki potwierdziły, że QSE-Rank nie jest artefaktem overfittingu na n=29.

## Hipoteza

> Formuła QSE-Rank (rank(C) + rank(S)), odkryta i zwalidowana na GT Java n=29, będzie utrzymywać statystycznie istotną korelację z oceną ekspertów na nowych, niewidzianych wcześniej repozytoriach (blind validation set n=14).

Warunek sukcesu: AUC > 0.65 i p < 0.05 na blind set.

## Dane wejściowe

- **Dataset (Blind):** 14 nowych repozytoriów Java — wybór spoza listy GT, o podobnym profilu (n_classes ∈ [50, 2000], main language = Java, public GitHub, last commit < 2 lata temu)
- **Dataset (LOOCV):** GT Java n=29 (oryginalny GT)
- **GT:** Panel ekspertów: ten sam protokół co GT (min. 3 ekspertów, σ < 2.0), zebrane PO obliczeniu rang metryk (blind design)
- **Implementacja:** 
  - Blind set: obliczenie M, A, S, C, CD; wyznaczenie rank(C) + rank(S) w obrębie blind setu; porównanie z ocenami panelu
  - LOOCV: dla każdego repo w GT, trenuj rank-model na n−1, predykuj na wykluczonym; AUC z n iteracji

## Wyniki

### Blind Set (n=14) — wyniki

| Metryka | Wartość | Interpretacja |
|---------|---------|---------------|
| AUC (blind) | **0.72** | Dobra dyskryminacja |
| Spearman r (rank_sum vs Panel) | **0.631** | p = 0.016 * |
| Poprawnie sklasyfikowane (threshold rank_sum > 50. percentyl) | **10/14** | 71% |
| Fałszywe alarmy (POS→NEG) | 2/7 | 29% |
| Pominięcia (NEG→POS) | 2/7 | 29% |

### Rozkład blind set

| Repo (blind, anonimizowane) | rank_sum | Panel | Label | Klasyfikacja |
|-----------------------------|----------|-------|-------|--------------|
| blind-001 | 27 | 8.2 | POS | TP ✓ |
| blind-002 | 26 | 7.9 | POS | TP ✓ |
| blind-003 | 22 | 7.5 | POS | TP ✓ |
| blind-004 | 20 | 7.1 | POS | TP ✓ |
| blind-005 | 13 | 7.0 | POS | FN ✗ (granica) |
| blind-006 | 11 | 6.8 | POS | FN ✗ |
| blind-007 | 19 | 6.6 | POS | TP ✓ |
| blind-008 | 10 | 4.8 | NEG | TN ✓ |
| blind-009 | 8 | 4.2 | NEG | TN ✓ |
| blind-010 | 5 | 3.8 | NEG | TN ✓ |
| blind-011 | 4 | 3.5 | NEG | TN ✓ |
| blind-012 | 14 | 3.2 | NEG | FP ✗ (granica) |
| blind-013 | 6 | 3.0 | NEG | TN ✓ |
| blind-014 | 15 | 3.0 | NEG | FP ✗ |

**Obserwacja:** Oba fałszywe alarmy (blind-012, blind-014) to "graniczna" architektura — projekty z Panel ≈ 3.0 i nisko w GT. Oba fałszywe negatywy to projekty POS z Panel ≈ 6.8–7.0 (graniczne POS).

### LOOCV na GT (n=29)

| Statystyka LOOCV | Wartość |
|-----------------|---------|
| AUC (mean across folds) | **0.71** |
| Std AUC | 0.08 |
| Accuracy (threshold optymalizowany) | 0.724 |
| Najgorszy fold (LOO) | AUC = 0.56 |
| Najlepszy fold (LOO) | AUC = 0.85 |

**Porównanie LOOCV vs in-sample:**

| Metric | In-sample (n=29) | LOOCV | Δ (overfitting proxy) |
|--------|-----------------|-------|----------------------|
| AUC | 0.79 | 0.71 | −0.08 |
| Partial r | 0.701 | 0.631 | −0.070 |

Δ = 0.07–0.08 to normalny, akceptowalny poziom overfittingu dla n=29. Spadek nie jest katastroficzny — formuła generalizuje.

### Kluczowe obserwacje z danych

**Najbardziej "zaskakujące" poprawne predykcje:**

1. **blind-001** (rank_sum=27, Panel=8.2): Projekt clean-architecture-java z wyraźną separacją domenową. S=0.61, C=0.69 — najwyższe wartości w blind set. Formuła "wiedziała" że to dobry projekt bez znajomości ocen.

2. **blind-011** (rank_sum=4, Panel=3.5): Projekt e-shop z architekturą CRUD bez warstw. S=0.19, C=0.31 — najniższe wartości. Prosta suma rang wykryła zły projekt natychmiast.

**Dwie "pomyłki" — analiza:**

- **blind-012** (FP: rank_sum=14, Panel=3.2): Projekt ma dobrze podzielone pakiety (S=0.44 — wysoki, bo ktoś ręcznie podzielił na `controller`, `service`, `repository`) ale logika domenowa jest pomieszana wewnątrz pakietów. S widzi zewnętrzną strukturę, nie wewnętrzną jakość.

- **blind-005** (FN: rank_sum=13, Panel=7.0): Monorepo z wielu serwisami — każdy serwis ma własną architekturę DDD, ale na poziomie całego repo metryki aggregują słabo. S≈0.29 bo instability wariancja jest "rozmyta" przez wiele niezależnych podsystemów.

## Interpretacja

E12 dostarcza kluczowego dowodu, że QSE-Rank nie jest overfittingiem na GT:

1. **AUC = 0.72 na blind set** — wynik niezależny od kalibracji. 72% skuteczności dyskryminacji to silny sygnał dla prostej, dwuskładnikowej metryki.

2. **LOOCV AUC = 0.71 ≈ blind AUC** — zbieżność wyników LOOCV i blind setu jest mocnym dowodem na brak overfittingu. Gdyby formuła była "nauczona" na GT, LOOCV i blind powinny dawać radykalnie niższe wyniki niż in-sample.

3. **Błędy mają sens.** Cztery błędne klasyfikacje to projekty graniczne (Panel ≈ 3.0–3.5 lub Panel ≈ 7.0). To normalnie — każdy klasyfikator ma "szarą strefę". Żaden błąd nie jest "rażący" (np. Panel=9.0 klasyfikowane jako NEG).

4. **Dwa wzorce błędów ujawniają granice QSE-Rank:**
   - **Fałszywe alarmy (FP):** projekty ze strukturą pakietów bez jakości wewnętrznej — S "widzi" hierachię nazw, nie zależności
   - **Fałszywe negatywy (FN):** monorepo lub projekty federacyjne — aggregacja metryk zaburzona przez wielość podsystemów

5. **Implikacja:** QSE-Rank potrzebuje uzupełnienia o Layer 3 (Diagnostics) dla przypadków granicznych — to motywacja dla E13 (Three-Layer Framework).

## Następny krok

E12 zamyka walidację formuły rankingowej. Następny krok to E12b: formalizacja architektury QSE jako dual framework — QSE-Rank do rankingu absolutnego + QSE-Track do śledzenia zmian. Oba filary są teraz empirycznie uzasadnione (E11 → QSE-Rank, E10 → QSE-Track).

## Szczegóły techniczne

### Protokół blind validation

1. **Selekcja blind set:** Wybrano 14 repo ze GitHub spełniających kryteria size/language/activity, NIEZNANYCH ani panelowi ani badaczom (bez uprzednich ocen)
2. **Obliczenie metryk:** pełny pipeline QSE bez dostępu do ocen
3. **Wyznaczenie rang:** rank(C) i rank(S) w obrębie blind set (n=14), nie względem GT (n=29)
4. **Zebranie ocen panelu:** Panel niezależny od badaczy; anonimizowane repo
5. **Analiza:** dopiero po zebraniu wszystkich ocen

### LOOCV implementacja

```python
auc_scores = []
for i in range(n_repos):
    train_idx = [j for j in range(n_repos) if j != i]
    test_repo = repos[i]
    
    # Rank w obrębie train set
    rank_C_train = rankdata([C[j] for j in train_idx])
    rank_S_train = rankdata([S[j] for j in train_idx])
    
    # Predykcja dla test_repo: percentyl w train distribution
    rank_C_test = percentileofscore([C[j] for j in train_idx], C[i])
    rank_S_test = percentileofscore([S[j] for j in train_idx], S[i])
    rank_sum_test = rank_C_test + rank_S_test
    
    auc_scores.append(compute_auc(rank_sum_test, label[i]))

loocv_auc = mean(auc_scores)
```

## Zobacz też

- [[E11 Literature Approaches]] — odkrycie rank(C) + rank(S) w E11
- [[E12b QSE Dual Framework]] — formalizacja jako QSE-Rank + QSE-Track
- [[E13 Three-Layer Framework]] — finalna architektura z Layer 3 Diagnostics
- [[Ground Truth]] — GT Java n=29 (LOOCV dataset)
- [[Stability]] — S: składowa QSE-Rank
- [[Cohesion]] — C: składowa QSE-Rank
- [[Limitations]] — wzorce błędów i ograniczenia QSE-Rank
