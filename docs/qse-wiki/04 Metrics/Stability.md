---
type: metric
language: pl
---

# Stability (S)

## Prostymi słowami

Stability mierzy, czy Twój system ma wyraźne "jądro" i "obrzeże" — jak armia z generałami i szeregowymi. Jądro (domain, core) jest stabilne: wiele modułów od niego zależy, samo zależy od niewielu. Obrzeże (api, ui) jest niestabilne: nic od niego nie zależy, samo zależy od wielu. Brak warstw = wszystko "podobnie ważne" = nikt nie wie co jest centrum architektury.

> ⚠️ **UWAGA KRYTYCZNA:** Stability jest najbardziej kontrowersyjną metryką QSE. Hipotezy W2 i E1 zostały **obalone**. Stability działa, ale inaczej niż zakładano.

## Szczegółowy opis

### Metryka Martina (Instability)

Stability bazuje na metryce Roberta Martina (2003) — **Instability**:

\[I = \frac{C_e}{C_a + C_e}\]

Gdzie:
- \(C_a\) (afferent couplings, fan-in) = liczba modułów *importujących* ten pakiet
- \(C_e\) (efferent couplings, fan-out) = liczba modułów *importowanych przez* ten pakiet

Interpretacja:
- \(I \approx 0\): "jądro" — wiele zależy od niego, samo nie zależy od niczego
- \(I \approx 1\): "obrzeże" — dużo importuje, nikt od niego nie zależy
- \(I \approx 0.5\): "nieuchwytny środek" — brak jasnej roli

### QSE Stability = wariancja Instability

Dobra architektura warstwowa ma **zróżnicowane** I: paczki mają I=0.0, 0.2, 0.5, 0.8, 1.0 — wyraźna hierarchia. Płaska architektura: wszystkie pakiety I≈0.5 — brak warstw.

```
Stability = min(1, Var(I_1, ..., I_k) / 0.25)
```

Normalizator 0.25 = maksymalna wariancja zmiennej binarnej (0/1).

### Tabela interpretacji

| Wartość S | Znaczenie |
|---|---|
| 1.0 | Wyraźna hierarchia: jądro, warstwy pośrednie, obrzeże |
| 0.5–1.0 | Widoczna hierarchia |
| 0.2–0.5 | Słaba hierarchia |
| 0.0–0.2 | Flat — wszystko podobnie "ważne" |

### Dane empiryczne Java GT (n=59)

| Kategoria | Średnia S | p-value |
|---|---|---|
| **POS** | **0.344** | — |
| **NEG** | **0.238** | — |
| Mann-Whitney p | **0.016 \*** | istotne |
| Partial r (kontrola rozmiaru) | +0.593 (n=29) | — |

Przy n=59: Stability jest istotna (p=0.016), najsilniejsza metryka per-komponent dla Javy przy n=29 (partial r=+0.593, p=0.001).

### KRYTYCZNA KONTROWERSJA: Paradoks DDD

Eksperyment E1 (sesja Turn 28) obalił kluczowe założenie o Stability:

**Założenie** (błędne): dobra architektura DDD ma niską instability domeny (domain jest "jądrem" = mało fan-out).

**Rzeczywistość:**

| Repo | Panel | Domain instability | Wyjaśnienie |
|---|---|---|---|
| **mall** (NEG) | 2.0 | **0.024** | CRUD POJO sink — zero logiki, nic nie importuje |
| **dddsample** (POS) | 8.25 | **0.464** | Rich domain — klasy domenowe komunikują się wewnętrznie |

**Paradoks:** dobra domena DDD ma **WYŻSZĄ** instability niż anemic model, bo:
- Klasy domenowe w DDD "rozmawiają ze sobą" (wiele fan-out wewnętrznego)
- CRUD POJO nie ma logiki → I≈0 przez definicję

Metryka Martina nie odróżni: "stabilna bo świetnie zaprojektowana" od "stabilna bo to pusty POJO". Bez semantyki kodu — tylko topologia grafu — to rozróżnienie jest niemożliwe.

### Historia i obalone wnioski

| Etap | Wniosek | Status |
|---|---|---|
| Kalibracja na BLT | S=0.55 optymalne | **BŁĘDNY** — BLT to złe GT |
| S_hierarchy p=0.155 (n=14) | "S nieistotna" | Artefakt małej próby |
| E1 (S_hierarchy) | S_hierarchy = p=0.762 ns | **OBALONY** — CRUD=DDD w hierarchii |
| n=29, partial r=+0.593 | S istotna i najsilniejsza | PASS przy odpowiednim n |
| n=59, p=0.016 | S istotna | POTWIERDZONY |

### Związek Stability a AGQ

Wcześniejsza formuła AGQ v2 miała S z wagą **0.55** — skalibrowaną na BLT. To było błędne. Po odrzuceniu BLT i przejściu na panel ekspertów:
- PCA daje equal wagi 0.20 dla wszystkich składowych
- AGQ v3c Java: waga S = **0.20**

Stability "jako waga=0.55" jest **obalone** (E1 refuted). Stability "jako składowa z wagą 0.20" jest istotna statystycznie i wchodzi do formuły.

### Problemy z implementacją

1. **Python Abstractness** — oryginalny wzór Martina wymaga abstrakcyjności klas \(A\). W Pythonie prawie zawsze A=0 (bez hierarchii ABClass). QSE używa wariantu *bez A* — wariancji czystej instability, co odpowiada zachowaniu w praktyce dla języków z duck typing.

2. **Wymaga detekcji klas abstrakcyjnych** — dla Javy: `abstract class`, `interface`. QSE Java scanner wykrywa i filtruje, co poprawia metrykę.

3. **Jolak cross-validation** — S potwierdzona niezależnie: repos z S<0.12 to prawdopodobnie te z najgorszymi "Unstable Dependencies" w papierze Jolaka. S range [0.065–0.954] pokrywa pełne spektrum.

## Definicja formalna

Instability pakietu \(p\):

\[I(p) = \frac{C_e(p)}{C_a(p) + C_e(p)}\]

Stability projektu:

\[S = \min\!\left(1,\ \frac{\text{Var}(I(p_1), \ldots, I(p_k))}{0.25}\right)\]

Gdzie \(k\) = liczba pakietów wewnętrznych, \(0.25\) = normalizator (max wariancja zmiennej U[0,1] przy binarnej koncentracji).

**Ograniczenie metodologiczne:** Metryka Martina w oryginalnej formie to \(D = |A + I - 1|\) (Distance from Main Sequence), gdzie \(A\) = abstractness. QSE pomija \(A\) i używa samej wariancji \(I\), co jest empirycznie zwalidowanym zamiennikiem.

**Walidacja statystyczna** (Java GT n=59):
- Mann-Whitney p = 0.016 \*
- Partial r = +0.593 (n=29, kontrola rozmiaru)

## Zobacz też

- [[DMS Instability]] — szczegóły metryki Martina
- [[Hierarchy]] — hierarchia jako właściwość Stability
- [[E1 Stability Hierarchy]] — eksperyment obalający S_hierarchy
- [[Conceptual Dimensions]] — kontekst czterech wymiarów
- [[Metrics Index]] — porównanie dyskryminatorów
