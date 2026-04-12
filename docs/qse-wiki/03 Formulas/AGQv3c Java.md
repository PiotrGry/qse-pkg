---
type: formula
status: credible
language: pl
languages: [java]
components: [M, A, S, C, CD]
---

# AGQv3c Java

## Prostymi słowami

AGQv3c Java to obecna najlepsza formuła dla projektów Java. Jej główna idea to równość: zamiast pozwalać jednej metryce dominować (jak S=0.55 w AGQv1 albo CD de facto dominujące przez korelację), każda z pięciu składowych dostaje wagę 0.20. To nie jest arbitralny wybór — wynika z analizy PCA, która pokazała, że żaden z pięciu wymiarów nie dominuje w danych. Wyniki na rozszerzonym zbiorze Java GT (n=59): MW p=0.000221, AUC=0.767.

## Szczegółowy opis

### Wzór

```
AGQv3c (Java) = 0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD
```

Pięć składowych z równymi wagami. Identyczny wzór co AGQv3a — wersja „c" oznacza konfigurację z klasycznym zestawem metryk (bez zastępowania A przez NSdepth jak w v3b).

### Skąd wagi — odkrycie PCA

Analiza PCA przeprowadzona na n=357 repozytoriach (benchmark) dała kluczowy wynik:

> **„All 5 eigenvalues nearly equal — PCA yields uniform 0.20 weights. No dominant dimension in feature space."**

```
PCA na n=357 repo:
  Eigenvalue 1 ≈ Eigenvalue 2 ≈ Eigenvalue 3 ≈ Eigenvalue 4 ≈ Eigenvalue 5

Interpretacja: żadna kombinacja M/A/S/C/CD nie dominuje w czystym
wymiarze wariancji. Brak uzasadnienia dla nierównych wag.
→ Wniosek: wagi równe 0.20 są empirycznie uzasadnione.
```

Wcześniejsze nierówne wagi (AGQv1: S=0.55, AGQv2: M=0.30/S=0.15) były hipotezami — PCA pokazało, że dane ich nie wspierają.

### Walidacja na rozszerzonym GT Java (n=59)

GT rozszerzony z n=29 do n=59 (kwiecień 2026): 31 POS, 28 NEG. Panel: 4 recenzentów (symulowani eksperci), ocena 1–10, etykieta POS gdy panel ≥ 6.0.

| Statystyka | Wartość | Interpretacja |
|---|---|---|
| Mann-Whitney p | **0.000221** | Wysoce istotne (p < 0.001) |
| Spearman ρ | **0.380** (p=0.003) | Umiarkowana korelacja |
| Partial r (kontrola rozmiaru) | **0.447** (p=0.0004) | Silna po kontroli |
| AUC-ROC | **0.767** | Dobra klasyfikacja POS/NEG |
| POS mean AGQ | 0.571 | |
| NEG mean AGQ | 0.486 | |
| Gap POS−NEG | 0.085 | |

Porównanie: po rozszerzeniu GT z n=29 do n=59, gap zawęził się 0.115→0.085 (oczekiwane — większa różnorodność), ale wszystkie testy istotności pozostają p<0.01.

### Dyskryminacja per składowa

Analiza per-component na rozszerzonym GT (n=59):

| Składowa | POS średnia | NEG średnia | Δ | MW p | Istotność |
|---|---|---|---|---|---|
| [[Modularity]] (M) | 0.668 | 0.648 | +0.021 | 0.226 | ns |
| [[Acyclicity]] (A) | 0.994 | 0.974 | +0.020 | 0.030 | * |
| [[Stability]] (S) | 0.344 | 0.238 | +0.106 | 0.016 | * |
| [[Cohesion]] (C) | 0.393 | 0.269 | +0.124 | **0.0002** | *** |
| [[CD]] | 0.454 | 0.299 | +0.155 | **0.004** | ** |

**Ranking siły dyskryminacji:**
1. **C (Cohesion)** — najsilniejszy: p=0.0002 ★★★
2. **CD** — drugi: p=0.004 ★★
3. **S (Stability)** — trzeci: p=0.016 ★
4. **A (Acyclicity)** — marginalny: p=0.030 ★
5. **M (Modularity)** — nieistotna: p=0.226 ns

[[Cohesion]] i [[CD]] razem stanowią kluczowe dyskryminatory jakości architektury Java. [[Modularity]] samodzielnie nie discriminuje — podobne do wniosku z kalibracji wag (M=0.00 w L-BFGS-B na OSS-Python).

### Walidacja krzyżowa: Jolak et al.

8 repozytoriów Java OSS z badania Jolak et al. (2025) przeskanowanych AGQv3c:

| Repo | AGQv3c | Wynik Jolak | Zgodność |
|---|---|---|---|
| MyPerf4J | 0.7557 | Dobra architektura | CONFIRMED ✅ |
| yavi | 0.5988 | Akceptowalna | CONFIRMED ✅ |
| light-4j | 0.4935 | Problematyczna | CONFIRMED ✅ |
| seata | 0.4875 | Problematyczna | CONFIRMED ✅ |
| sofa-rpc | 0.4864 | Problematyczna | PLAUSIBLE ~✅ |

Mean AGQv3c Jolak = 0.535 — pomiędzy GT-POS=0.571 a GT-NEG=0.486 (oczekiwane, projekty Jolak to przypadki ze środka). 4/5 wyników CONFIRMED, 1 PLAUSIBLE.

### Ograniczenia AGQv3c Java

1. **n=59 to wciąż małe GT** — wyniki wymagają replikacji na szerszym zbiorze
2. **Panel symulowany** — czterech recenzentów to symulacja, nie prawdziwi architekci
3. **Utility libraries** (Guava, commons-lang, commons-collections) — niski AGQ mimo dobrego projektowania; potrzebna normalizacja per kategorię
4. **P4 (następny krok)** — re-run Java-S experiment na n=59 GT, aby sprawdzić czy wagi 0.20 nadal optymalne

### Kontekst w hierarchii formuł

```mermaid
graph TD
    v1["AGQv1\nS=0.55 (BLT)\nPunkt bazowy"]
    v2["AGQv2\nDodano CD\nPartial r=0.675 n=14"]
    v3a["AGQv3a\nPCA równe wagi\nJava GT n=29: MW p=0.001"]
    v3c["AGQv3c Java ★\nPCA równe wagi\nJava GT n=59: MW p=0.000221\nAUC=0.767"]

    v1 -->|"obalenie W2\ndodanie CD"| v2
    v2 -->|"PCA finding\nexpansja GT"| v3a
    v3a -->|"GT n=29→59\npotwierdzenie"| v3c

    style v3c fill:#d4edda,stroke:#155724
```

## Definicja formalna

\[
\text{AGQv3c}_\text{Java} = 0.20 \cdot M + 0.20 \cdot A + 0.20 \cdot S + 0.20 \cdot C + 0.20 \cdot CD
\]

Składowe identyczne jak w AGQv2.

**Wyniki walidacji (Java GT n=59):**
- Mann-Whitney U test: p=0.000221 ✅
- Spearman ρ=0.380 (p=0.003) ✅
- Partial r=0.447 (p=0.0004) po kontroli rozmiaru ✅
- AUC-ROC=0.767 ✅
- 4/5 wyników Jolak CONFIRMED ✅

**Status:** CREDIBLE — wiarygodna formuła Java, oczekuje walidacji na szerszym GT i re-run Java-S experiment (P4).

## Zobacz też

- [[AGQ Formulas]] — tabela wszystkich wersji
- [[AGQv2]] — poprzednia wersja (partial r=0.675 n=14)
- [[AGQv3c Python]] — odpowiednik dla Pythona (inna formuła — inny problem)
- [[Cohesion]], [[CD]] — najsilniejsze dyskryminatory w Java GT
- [[Modularity]], [[Acyclicity]], [[Stability]] — pozostałe składowe
- [[Ground Truth]] — metodologia panelowa, GT Java n=59
