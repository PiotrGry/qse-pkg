---
type: experiment
status: zakończony
language: pl
---

# E7 — P4 Java-S Expanded GT (n=59)

## Prostymi słowami

Eksperyment P4 sprawdzał, czy wagi formuły v3c (equal 0.20) są nadal najlepsze po rozszerzeniu Ground Truth z 29 do 59 repozytoriów. Przetestowano 18 wariantów wag. Żaden nie pokonał v3c poza marginesem błędu. Kluczowe odkrycie: wcześniej obserwowana monotonność S (im więcej wagi na S, tym lepsze wyniki) okazała się artefaktem małego zbioru — na n=59 zniknęła całkowicie.

---

## Szczegółowy opis

### Cel

Czy v3c z równymi wagami 0.20 jest optymalna na rozszerzonym GT (n=59), czy rozszerzony zbiór ujawni lepszą konfigurację wag?

### Protokół

- Maximum iteracji: 5 (niezmiennik N7)
- Stop po 2 kolejnych iteracjach bez poprawy
- Brak modeli nieliniowych (N5)
- Brak brute-force (N6)
- Bootstrap CI (B=5000) do porównania wariantów
- Split-half stability test

### Warianty testowane (18 konfiguracji)

Warianty od C_boost (wagi na C i CD) po S_boost (waga na S) i mixed. Pełna tabela posortowana po partial_r:

| # | Wariant | Wagi (M/A/S/C/CD) | Partial r | p | AUC | CI width |
|---|---|---|---|---|---|---|
| 1 | C_boost | 10/10/20/30/30 | **0.484** | 0.0001 | 0.789 | 0.330 |
| 2 | S10_C30_CD20 | 20/20/10/30/20 | 0.472 | 0.0002 | 0.785 | 0.362 |
| 3 | S12_C28_CD20 | 20/20/12/28/20 | 0.471 | 0.0002 | 0.779 | 0.357 |
| 4 | S08_C32_CD20 | 20/20/08/32/20 | 0.471 | 0.0002 | 0.780 | 0.370 |
| 5 | M15_A15_C25_CD25 | 15/15/20/25/25 | 0.468 | 0.0002 | 0.786 | 0.332 |
| 6 | S15_C25 | 20/20/15/25/20 | 0.466 | 0.0002 | 0.779 | 0.351 |
| 7 | S05_C35_CD20 | 20/20/05/35/20 | 0.464 | 0.0002 | 0.774 | 0.379 |
| 8 | M15_A10_S20_C25_CD30 | 15/10/20/25/30 | 0.458 | 0.0003 | 0.780 | 0.336 |
| 9 | **v3c** | **20/20/20/20/20** | **0.447** | **0.0004** | **0.767** | **0.332** |
| 10 | S25_M15_A15 | 15/15/25/20/25 | 0.445 | 0.0004 | 0.778 | 0.318 |
| 11 | S10_C25_CD25 | 20/20/10/25/25 | 0.444 | 0.0004 | 0.768 | 0.377 |
| 12 | S15_CD25 | 20/20/15/20/25 | 0.436 | 0.0006 | 0.772 | 0.354 |
| 13 | S30_M15_A10_C20_CD25 | 15/10/30/20/25 | 0.436 | 0.0006 | 0.766 | 0.307 |
| 14 | S15_M25 | 25/20/15/20/20 | 0.433 | 0.0006 | 0.767 | 0.365 |
| 15 | S25_C15 | 20/20/25/15/20 | 0.421 | 0.0009 | 0.756 | 0.319 |
| 16 | S10_CD30 | 20/20/10/20/30 | 0.410 | 0.0013 | 0.759 | 0.387 |
| 17 | S30_C10 | 20/20/30/10/20 | 0.391 | 0.0022 | 0.740 | 0.310 |

### S Monotonicity — ZŁAMANA

Na n=29 obserwowano silną monotoniczność: im wyższa waga S, tym wyższy partial_r (ρ=1.00).

Na n=59: **ρ=0.00 (p=1.00)** — kompletny brak monotoniczności. Krzywa wagi S ma kształt odwróconego U z peakiem przy S=0.20 i spadkami po obu stronach.

```
Waga S:  0.05  0.08  0.10  0.12  0.15  0.20  0.25  0.30
         ──────────────────────────────────────────────────
Trend:   ↗     ↗     ↗     ↗     ~peak  v3c   ↘     ↘
```

**Interpretacja:** S na n=29 miała artefaktycznie silny sygnał. Na n=59 z większą różnorodnością repozytoriów, S jest istotna (p=0.016) ale nie dominująca. Inverted-U oznacza, że S=0.20 jest blisko optymalnej wagi.

### Split-half stability

Losowy podział GT na dwie połówki (B=1000):

| Wariant | Δ partial_r (median) | Stabilny? |
|---|---|---|
| v3c | 0.17 | ❌ |
| C_boost | 0.19 | ❌ |
| Wszystkie warianty | >0.15 | ❌ |

**Wniosek:** Żaden wariant nie jest stabilny w split-half. Krajobraz optymalizacji jest płaski — różnice między wariantami są mniejsze niż szum z podziału danych.

### Strict Protocol GT (n=38)

Dodatkowa analiza na zaostrzonym GT (panel≥7.0/≤3.5, σ<2.0, 100≤nodes≤5000):

| Wariant | Partial r (strict) | p |
|---|---|---|
| v3c | 0.507 | 0.001 |
| C_boost | 0.560 | <0.001 |
| C (sama) | 0.571 | 0.0002 |
| S (sama) | 0.410 | 0.011 |

Na strict GT oba warianty silniejsze, ale C_boost nadal w CI v3c.

### Wnioski

1. **v3c POTWIERDZONE** — brak dowodów na istnienie lepszego wariantu (na n=59)
2. **S monotonicity to artefakt** — zniknęła z rozszerzeniem GT
3. **Krajobraz płaski** — dalszy tuning wag na n=59 to overfitting na szum
4. **C i CD kluczowe** — warianty z wyższą wagą C/CD mają numerycznie lepsze wyniki (ale w CI)
5. **Zamknąć optymalizację wag** — v3c equal 0.20 jest rekomendacją finalną

### Artefakty

- `artifacts/java_s_p4_results.json` — pełne wyniki 18 wariantów
- `artifacts/java_s_p4_selfreview.json` — self-review protokołu
- `artifacts/gt_java_strict_v3.json` — strict protocol GT (n=38)

---

## Definicja formalna

```
H₀: ∃ wagi w ≠ (0.20, 0.20, 0.20, 0.20, 0.20) takie że partial_r(w) > partial_r(v3c) + CI_width

Wynik: NIE ODRZUCONO H₀ — brak dowodów na lepszy wariant
Status: v3c confirmed, wagi zamrożone
```

## Zobacz też

- [[AGQv3c Java]] — formuła potwierdzona tym eksperymentem
- [[Ground Truth]] — GT n=59 i strict n=38
- [[Experiments Index]] — indeks wszystkich eksperymentów
- [[Stability]] — metryka S, której monotonicity została złamana
- [[Cohesion]], [[CD]] — najsilniejsze dyskryminatory
