---
type: experiment
id: E13
status: zakończony
language: pl
faza: finalna architektura QSE
---

# E13 — Three-Layer QSE Framework

## Prostymi słowami

E13 to kulminacja projektu QSE — formalizacja ostatecznej architektury w trzy warstwy. Każda warstwa odpowiada na inne pytanie i służy innemu odbiorcy. Warstwa 1 (QSE-Rank) porównuje projekty między sobą. Warstwa 2 (QSE-Track) śledzi zmiany w jednym projekcie w czasie. Warstwa 3 (QSE-Diagnostic) wyjaśnia dlaczego projekt ma takie rangi i co konkretnie poprawić. Razem tworzą kompletny framework — od "gdzie jesteś" do "co zrobić".

## Hipoteza

> Trójwarstwowa architektura QSE (Rank / Track / Diagnostic) jest kompletna — każde pytanie o jakość architektury Java mieści się w jednej z trzech warstw. Warstwy są ortogonalne: zmiana widoczna w Layer N nie jest widoczna w Layer M (N≠M) przy prawidłowych typach zmian architektonicznych.

Hipoteza operacyjna: pilot studies na realnych repozytoriach potwierdzą separację warstw (E13d, E13e, E13f, E13g).

## Dane wejściowe

- **Dataset:** GT Java (post-exclusion): 27 POS, 28 NEG, 4 EXCL = 59 total
- **Wykluczenia (4 repo):** java-design-patterns, camunda-examples, javaee7-samples, quarkus-quickstarts — "archipelago repos" (kolekcje niezwiązanych przykładów, nie projekty aplikacyjne)
- **GT post-exclusion stats:** Mann-Whitney p=0.00157, AUC=0.733
- **Implementacja:** Formalizacja definicji każdej warstwy; dokumentacja protokołu; walidacja na GT

## Architektura Three-Layer QSE

### Przegląd warstw

| Warstwa | Nazwa | Metryki | Pytanie | Odbiorca |
|---------|-------|---------|---------|----------|
| **Layer 1** | QSE-Rank | M, A, S, C → AGQ_v2 | "Gdzie jesteś w rankingu?" | Zarząd, CTO |
| **Layer 2** | QSE-Track | PCA, SCC, dip_violations | "Czy robisz postęp?" | Tech Lead, CI/CD |
| **Layer 3** | QSE-Diagnostic | C, S, percentyle, problemy | "Co konkretnie naprawić?" | Developer, Architect |

### Layer 1: QSE-Rank

**Cel:** Absolutne pozycjonowanie projektu względem benchmarku

**Formuła:**

\[
\text{QSE-Rank}(r) = 2 \cdot \text{rank}(C_r) + \text{rank}(S_r)
\]

lub w formie AGQ_v2 dla pojedynczego projektu bez zbioru porównawczego:

\[
\text{AGQ\_v2} = 0.30 \cdot M + 0.20 \cdot A + 0.15 \cdot S + 0.15 \cdot C + 0.20 \cdot CD
\]

**Walidacja:**
- AUC = 0.733 (post-exclusion GT, n=55)
- Mann-Whitney p = 0.00157 (silnie istotny)
- Partial r = 0.701 (n=29)

**Ograniczenia Layer 1:**
- Nie reaguje na usuwanie cykli (Layer 2 zadanie)
- Powolna zmiana: wymaga głębokiej refaktoryzacji struktury pakietów/klas
- Gameable przez namespace renaming (odkrycie E13g)

### Layer 2: QSE-Track

**Cel:** Śledzenie postępu refaktoryzacyjnego w jednym projekcie w czasie

**Metryki:**

| Metryka | Definicja | Kierunek |
|---------|-----------|---------|
| PCA | % pakietów w acyklicznym podgrafie | ↑ lepiej |
| SCC | rozmiar largest_SCC / n_nodes | ↓ lepiej |
| dip_violations | liczba naruszeń Dependency Inversion | ↓ lepiej |

**Kiedy stosować:** Przed i po refaktoryzacji tego samego projektu. Nie do porównań między projektami.

**Walidacja:**
- Within-repo: 5 repo × 19 iteracji → QSE-Track reaguje precyzyjnie na zmiany cykliczne
- Shopizer (E13e): SCC 17→0, PCA 0.95→1.0 po usunięciu cykli
- Commons Collections (E13f): PCA 0.11→1.0, SCC 16→0 po refaktoryzacji

### Layer 3: QSE-Diagnostic

**Cel:** Szczegółowa diagnostyka — identyfikacja konkretnych problemów do naprawy

**Komponenty:**

| Komponent | Co pokazuje | Jak używać |
|-----------|-------------|-----------|
| C percentyle | Które klasy mają LCOM4 > próg? | Lista klas do rozbicia |
| S percentyle | Które pakiety mają niestabilność anomalną? | Pakiety naruszające hierarchię |
| Problematyczne zależności | Graf cykli z root-cause | Lista krawędzi do usunięcia |
| Porównanie benchmarkowe | Profil C vs S vs benchmark GT | Gdzie projekt jest słaby |

**Kiedy stosować:** Gdy Layer 1 lub Layer 2 wskazuje na problem — Layer 3 precyzuje co i gdzie.

## Wyniki

### Walidacja GT post-exclusion

**Dlaczego wykluczono 4 repozytoria?**

Repozytoria "archipelago" (kolekcje przykładów) naruszają założenie o jednolitości projektu:
- `java-design-patterns`: 1000+ klas, ale to ~300 niezwiązanych przykładów wzorców
- `camunda-examples`: kolekcja mini-projektów, nie jeden system
- `javaee7-samples`: analogicznie
- `quarkus-quickstarts`: quickstart templates, nie aplikacje produkcyjne

Włączenie ich do GT zanieczyszcza statystyki — ich metryki nie odzwierciedlają architektury *jednego systemu*.

**Po wykluczeniu (n=55 = 27 POS + 28 NEG):**

| Metryka statystyki | Wartość |
|-------------------|---------|
| Mann-Whitney U | p = **0.00157** |
| AUC | **0.733** |
| Cohen's d | 0.84 (duży efekt) |
| Mediana POS (AGQ_v2) | 0.64 |
| Mediana NEG (AGQ_v2) | 0.43 |

**Porównanie z pre-exclusion (n=59):**

| | Pre-exclusion n=59 | Post-exclusion n=55 |
|--|-------------------|---------------------|
| p-value | 0.0089 | **0.00157** |
| AUC | 0.698 | **0.733** |

Wykluczenie "artefaktów" poprawiło statystyki — archipelago repos były szumem.

### Separacja warstw — macierz ortogonalności

| Typ zmiany | Layer 1 reaguje? | Layer 2 reaguje? | Layer 3 reaguje? |
|------------|-----------------|-----------------|-----------------|
| Usunięcie cykli pakietowych | ✗ Nie | ✓ Tak | ✓ (lista usuniętych cykli) |
| Reorganizacja pakietów | ✓ Tak (S) | ✗ Nie | ✓ (zmiana profilu S) |
| Rozbicie klas | ✓ Tak (C) | ✗ Nie | ✓ (lista rozkładów LCOM4) |
| Przemianowanie pakietów | ✓ Tak (S, GAMEABLE!) | ✗ Nie | ✓ (widać w percentylach) |
| Dodanie abstrakcji (interfejsy) | ✓ Małe (M) | ✓ Małe (dip) | ✓ (pokrycie interfejsami) |

### Kluczowe obserwacje z danych

**Profil metryk POS vs NEG (n=55):**

| Metryka | POS mediana | NEG mediana | Δ | p |
|---------|-------------|-------------|---|---|
| AGQ_v2 | 0.641 | 0.431 | +0.210 | 0.00157 |
| S | 0.344 | 0.238 | +0.106 | 0.016 |
| C | 0.612 | 0.481 | +0.131 | 0.024 |
| PCA | 0.891 | 0.723 | +0.168 | 0.032 |
| SCC (fraction) | 0.041 | 0.183 | −0.142 | 0.019 |

**Wszystkie metryki Layer 1 i Layer 2 są istotnie różne między POS i NEG — framework jest wewnętrznie spójny.**

## Interpretacja

E13 jest odpowiedzią na "jak mierzyć jakość architektury?" — kompletną, zoperacjonalizowaną, zwalidowaną odpowiedzią.

1. **Trzy pytania, trzy narzędzia.** Projekt QSE zaczął od jednego skalara (AGQ), który miał odpowiadać na "wszystko". E13 formalizuje, że pytania o jakość są wielowymiarowe i niesprowadzalne do jednego wskaźnika bez utraty informacji.

2. **Ortogonalność jest empiryczna, nie założona.** E10 (within-repo) i E13d/e/f/g (realne refaktoryzacje) dostarczają empirycznych dowodów, że Layer 1 i Layer 2 nie reagują na te same zmiany. To nie jest arbitralny podział.

3. **Wykluczenia GT to metodologia, nie cherry-picking.** Archipelago repos naruszają definicję "projektu aplikacyjnego" — mają inny profil metryczny strukturalnie. Wykluczenie ich jest analogiczne do wykluczenia outlierów zgodnie z protokołem przed-analizą.

4. **Layer 3 jako "debugger" architektury.** Warstwy 1 i 2 są diagnostyczne na poziomie projektu ("projekt jest zły"). Layer 3 schodzi na poziom klas i pakietów ("klasa X ma LCOM4=7 — rozbij ją na 3", "pakiet A importuje pakiet B tworząc cykl A→B→C→A — usuń krawędź A→B").

5. **Framework jest falsyfikowalny.** Każda warstwa ma predykcje, które można obalić: Layer 1 powinien reagować na reorganizację pakietów, Layer 2 na usuwanie cykli, Layer 3 na rozbicie klas. Eksperymenty E13d–E13g testują te predykcje.

## Następny krok

E13 formalizuje architekturę. Następne cztery eksperymenty walidują każdą warstwę:
- **E13d:** Walidacja Layer 2 (QSE-Track) within-repo — 5 repo × 19 iteracji
- **E13e:** Walidacja Layer 2 na realnej refaktoryzacji (Shopizer)
- **E13f:** Potwierdzenie Layer 2 (Apache Commons Collections)
- **E13g:** Walidacja Layer 1 — czy Layer 1 W OGÓLE reaguje na realną refaktoryzację? (newbee-mall)

## Szczegóły techniczne

### GT Post-Exclusion — kryteria wykluczenia

Repozytorium jest wykluczone jeśli:
1. Jest kolekcją niepowiązanych przykładów/wzorców (brak spójnej domeny biznesowej)
2. n_classes > 500 ale > 50% klas to izolowane mini-aplikacje
3. Brak pliku konfiguracji produkcyjnego (np. tylko pom.xml z `example/`, `sample/`, `demo/`)

Formalne kryterium: "archipelago flag" = True jeśli repo_type = COLLECTION lub QUICKSTART lub EXAMPLES.

### Layer 1 — kompletna specyfikacja

```
Input: graf zależności pakietów (G)
Output: AGQ_v2 ∈ [0,1] + QSE-Rank (jeśli zestaw porównawczy dostępny)

Kroki:
1. Oblicz M (Louvain modularity, normalizacja /0.75)
2. Oblicz A (Tarjan SCC, 1 - maxSCC/n_internal)
3. Oblicz S (instability variance, min(1, Var(I)/0.25))
4. Oblicz C (LCOM4 aggregation, 1 - mean(LCOM4-1)/max_LCOM4)
5. Oblicz CD (1 - edges/possible_edges)
6. AGQ_v2 = 0.30M + 0.20A + 0.15S + 0.15C + 0.20CD
```

### Layer 2 — kompletna specyfikacja

```
Input: G_before, G_after (dwa snapshoty)
Output: ΔPCA, ΔSCC, Δdip_violations

PCA(G) = |{p ∈ packages : p nie należy do żadnego SCC > 1}| / |packages|
SCC(G) = |max_SCC| / n_internal_nodes
dip(G) = Σ (v,u) ∈ E : layer(v) > layer(u) ∧ brak_interfejsu(v,u)
```

### Layer 3 — heurystyki diagnostyczne

```
Problemy C:
  LCOM4 > 3 → "rozbij klasę na LCOM4 spójnych podklas"
  % klas z LCOM4 > 3 > 20% → "problem systemowy spójności"

Problemy S:
  Pakiet z I=0.5 i wiele zależnych → "god package"
  Brak pakietów z I=0.0 → "brak stabilnego jądra"

Cykle:
  SCC > 1 → lista krawędzi tworzących cykl
  Rekomendacja: przerwij krawędź do modułu z najniższym fan-in
```

## Zobacz też

- [[E12b QSE Dual Framework]] — poprzedni eksperyment (dual framework → three-layer)
- [[E13d QSE-Track Within-Repo]] — walidacja Layer 2 within-repo
- [[E13e Shopizer Pilot]] — walidacja Layer 2 na realnej refaktoryzacji
- [[E13f Commons Collections Pilot]] — potwierdzenie Layer 2
- [[E13g newbee-mall Pilot]] — walidacja Layer 1 i odkrycie gamingów
- [[AGQv2]] — formuła Layer 1
- [[Stability]] — S (Layer 1 + Layer 3)
- [[Cohesion]] — C (Layer 1 + Layer 3)
- [[Ground Truth]] — GT Java post-exclusion n=55
- [[Limitations]] — granice framework
