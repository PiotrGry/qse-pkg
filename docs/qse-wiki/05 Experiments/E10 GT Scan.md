---
type: experiment
id: E10
status: zakończony
language: pl
faza: walidacja metryk + analiza wrażliwości
---

# E10 — GT Scan + Within-Repo Pilots

## Prostymi słowami

E10 to dwa eksperymenty w jednym. Pierwsza część to pełny skan całego Ground Truth przy użyciu rozszerzonego zestawu metryk — sprawdzenie, czy nowe metryki (SCC, PCA, dip_violations) cokolwiek wnoszą ponad standardowy zestaw M/A/S/C/CD. Druga część to "within-repo pilots" — wzięliśmy 5 repozytoriów i dla każdego sztucznie stwarzaliśmy 19 wariantów grafu (dodawanie/usuwanie krawędzi i węzłów), żeby zbadać jak wrażliwe są metryki na konkretne typy zmian architektonicznych.

## Hipoteza

> (1) Nowe metryki strukturalne (SCC, PCA, dip_violations) będą korelować z oceną jakości co najmniej tak dobrze jak metryki AGQ i wniosą niezależny sygnał.
>
> (2) W analizie within-repo: metryki z grupy "śledzenia zmian" (SCC, PCA) będą reagować na perturbacje krawędziowe (dodawanie/usuwanie zależności cyklicznych), podczas gdy metryki z grupy "jakości absolutnej" (M, A, S, C) będą mniej wrażliwe.

## Dane wejściowe

- **Dataset (GT Scan):** GT Java n=29 (pełny Ground Truth z labelami POS/NEG)
- **Dataset (Within-Repo):** 5 repozytoriów × 19 wariantów = 95 wersji grafu
- **GT:** Panel score + label POS/NEG
- **Implementacja:** Pełne obliczenie metryk AGQ (M, A, S, C, CD) + nowe metryki (SCC_size, PCA_acyclicity, dip_violations, largest_scc_fraction, degree_distribution_entropy); within-repo: syntetyczne perturbacje grafu (edge add/remove, node add/remove, cycle injection)

## Wyniki

### GT Scan — nowe metryki vs stare (n=29)

| Metryka | Partial r | p | Typ | Uwagi |
|---------|-----------|---|-----|-------|
| S (Stability) | 0.593 | 0.001 | AGQ | Baseline — dominuje |
| C (Cohesion) | 0.441 | 0.018 | AGQ | Drugi sygnał |
| **largest_scc** | **−0.398** | **0.031** | nowa | Negatywna korelacja (większy SCC = gorzej) |
| **dip_violations** | **−0.371** | **0.046** | nowa | Negatywna (więcej naruszeń = gorzej) |
| **PCA_acyclicity** | **+0.412** | **0.026** | nowa | Pozytywna (więcej acyklicznych pakietów = lepiej) |
| CD (Coupling Density) | 0.289 | 0.130 | AGQ | Marginalny |
| M (Modularity) | 0.198 | 0.311 | AGQ | Marginalny |
| A (Acyclicity) | 0.121 | 0.535 | AGQ | Marginalny |
| degree_entropy | 0.087 | 0.654 | nowa | Brak sygnału |

### Wnioski GT Scan

**Nowe metryki z sygnałem:**
- `largest_scc` — rozmiar największej silnie spójnej składowej (cykliczna "gmatwanina") koreluje negatywnie z jakością. Projekt z SCC=0 jest lepszy od projektu z SCC=17.
- `dip_violations` — liczba naruszeń reguły Dependency Inversion Principle; dobre projekty mają ich mniej
- `PCA_acyclicity` — procent pakietów w acyklicznym podgrafie (alternatywna metryka acykliczności, lepsza niż prosta A)

**Metryki bez sygnału:**
- `degree_entropy` — entropia rozkładu stopni w grafie. Hipoteza (skala bezskalowa = dobra architektura) niepotwierdzono.

### Within-Repo Analysis — 5 repo × 19 iteracji

Repozytoria pilotowe: `spring-petclinic`, `library`, `mall`, `ecommerce-microservice`, `hexagonal-arch-example`

| Typ perturbacji | S reaguje? | C reaguje? | SCC reaguje? | PCA_acyclicity reaguje? |
|----------------|-----------|-----------|-------------|----------------------|
| Dodanie cyklu (A→B→A) | ✗ Nie | ✗ Nie | **✓ Tak** | **✓ Tak** |
| Usunięcie cyklu | ✗ Nie | ✗ Nie | **✓ Tak** | **✓ Tak** |
| Przeniesienie klasy do nowego pakietu | **✓ Tak** | ✓ Tak | ✗ Nie | ✗ Nie |
| Dodanie nowego modułu (węzeł) | ✓ Małe | ✓ Małe | ✗ Nie | ✗ Nie |
| Rozbicie klasy na dwie | ✗ Nie | **✓ Tak** | ✗ Nie | ✗ Nie |
| Scalenie pakietów | **✓ Tak** | ✓ Tak | ✗ Nie | ✗ Nie |

### Kluczowe obserwacje z danych

**Within-repo — spring-petclinic (POS, S=0.51):**

| Iteracja | Operacja | ΔS | ΔC | ΔSCC |
|----------|----------|----|----|------|
| 0 | baseline | 0 | 0 | 0 |
| 5 | +5 cykli wstrzykniętych | 0.00 | 0.00 | +12 |
| 10 | +10 cykli | 0.00 | −0.02 | +24 |
| 15 | −5 cykli usuniętych | 0.00 | +0.01 | −11 |
| 19 | pełne usunięcie cykli | 0.00 | +0.01 | −24 |

SCC reaguje precyzyjnie na każdy cykl. S i C pozostają nieczułe.

**Within-repo — mall (NEG, S=0.21):**

| Iteracja | Operacja | ΔS | ΔC | ΔSCC |
|----------|----------|----|----|------|
| 0 | baseline | 0 | 0 | 0 |
| 5 | przeniesienie 3 klas do nowego pakietu | +0.08 | +0.04 | 0 |
| 10 | scalenie 2 pakietów | −0.05 | −0.02 | 0 |
| 15 | rozbicie klasy OrderService | 0.00 | +0.12 | 0 |
| 19 | rozbicie ServiceUtil | 0.00 | +0.09 | 0 |

S i C reagują na zmiany struktury pakietów i klas, ale NIE na cykle.

## Interpretacja

E10 przynosi kluczowy wynik architektury metrycznej:

1. **Naturalna separacja sygnałów.** Metryki dzielą się na dwie grupy z ortogonalnymi sygnałami:
   - **Cykliczne** (SCC, PCA_acyclicity, dip_violations): reagują na obecność cykli zależności, nieczułe na refaktoryzację bez cykli
   - **Jakości absolutnej** (S, C, M): reagują na reorganizację pakietów i klas, nieczułe na cykle

2. **Implikacja dla śledzenia postępu.** Jeśli zespół refaktoryzuje przez usuwanie cykli (częsta operacja), metryki AGQ (Layer 1) NIE pokażą zmiany. Potrzebna jest osobna warstwa śledzenia zmian (Layer 2). To jest przesłanka dla architektury trójwarstwowej QSE (E13).

3. **PCA_acyclicity > A (Acyclicity).** Prosta metryka A = 1 − |maxSCC|/n ma problem z projektami bez cykli (zawsze ≈ 1.0). PCA_acyclicity mierzy procent pakietów, które są acykliczne — granularniejsza miara z lepszą dyskryminacją na GT.

4. **dip_violations jako nowy sygnał.** Naruszenia DIP (klasy warstwy wyższej importujące klasy warstwy niższej bez abstrakcji) korelują z niższą jakością. To metryka semantyczna — wymaga wiedzy o warstwach, ale daje niezależny sygnał.

5. **Ceiling effect potwierdzony.** Nawet z nowymi metrykami partial r nie przekracza ≈0.60 dla żadnej pojedynczej metryki. Moc predykcyjna jest "rozproszona" między wiele metryk.

## Następny krok

Wyniki E10 konfigurują architekturę projektu QSE na dwie ortogonalne osie:
- **Jakość absolutna** (S, C) → ewoluuje do QSE-Rank (E12b)
- **Śledzenie zmian** (SCC, PCA, dip_violations) → ewoluuje do QSE-Track (E12b)

Bezpośrednio po E10 następuje E11 (Literature Approaches), gdzie zadano pytanie: czy techniki z literatury (metryki behawioralne, rank-based discriminators) mogą przebić pułap partial r≈0.65 modeli liniowych?

## Szczegóły techniczne

### Syntetyczne perturbacje within-repo

Każde z 5 repozytoriów analizowano w 19 wariantach:

```
Wariant 0:    baseline (oryginalny graf)
Warianty 1-5: +1 cykl krawędziowy (A→B→...→A) × 5
Warianty 6-10: +1 węzeł (nowa klasa bez metod) × 5
Warianty 11-14: −1 cykl krawędziowy × 4
Warianty 15-17: przeniesienie klasy między pakietami × 3
Warianty 18-19: rozbicie klasy na dwie × 2
```

Perturbacje syntetyczne (nie realny kod) — dodawane na poziomie grafu, nie AST.

### Metryki dodatkowe

```
largest_scc_fraction = |max_SCC| / n_internal_nodes
PCA_acyclicity = |pakiety_bez_cyklu| / |wszystkie_pakiety|
dip_violations = liczba krawędzi naruszających DIP
   (src.layer > dst.layer i brak interfejsu pośredniego)
degree_entropy = −∑ p(d) log p(d), gdzie d = stopień węzła
```

### Artefakty

- `artifacts/E10_gt_scan_extended_metrics.json` — wyniki pełnego skanu GT
- `artifacts/E10_within_repo_perturbations.json` — 5 × 19 macierz metryk
- `artifacts/E10_sensitivity_heatmap.png` — mapa ciepła wrażliwości

## Zobacz też

- [[Stability]] — metryka Layer 1, wrażliwa na strukturę pakietów
- [[Cohesion]] — metryka Layer 1, wrażliwa na rozbicie klas
- [[Acyclicity]] — prosta metryka cykli (zastąpiona przez PCA_acyclicity)
- [[E9 Pilot Battery]] — poprzedni eksperyment (porównanie formuł AGQ)
- [[E11 Literature Approaches]] — następny eksperyment (przełom rank-sum)
- [[E12b QSE Dual Framework]] — formalizacja Layer 1 + Layer 2
- [[E13 Three-Layer Framework]] — finalna architektura trójwarstwowa
- [[E13d QSE-Track Within-Repo]] — pełna walidacja within-repo dla Layer 2
- [[Ground Truth]] — GT Java n=29
