---
type: metric
language: pl
---

# Coupling Density (CD)

## Prostymi słowami

Coupling Density mierzy "gęstość sieci połączeń" — ile importów przypada na jeden moduł. Projekt z CD=0.7 ma ok. 1-2 importy per plik — moduły są luźno powiązane, każdy zajmuje się swoją sprawą. Projekt z CD=0.2 ma 4-5 importów per plik — każdy moduł "zna" wiele innych modułów, zmiana jednego pociąga zmiany w wielu.

## Szczegółowy opis

### Wzór

```
CD = 1 − clip(edges/nodes / 6.0,  0.0,  1.0)
```

Równoważnie:

```
CD = 1 − min(1, ratio/6.0)
gdzie ratio = |E| / |V_internal|
```

Skąd 6.0? To empiryczny próg — powyżej 6 krawędzi per węzeł projekty są konsekwentnie oznaczane jako złe przez panel ekspertów.

Wysoki CD (bliski 1.0) = niskie sprzężenie = dobra architektura.
Niski CD (bliski 0.0) = gęste sprzężenie = zła architektura (dla Javy).

### Tabela interpretacji

| Wartość CD | Ratio approx | Jakość (Java) |
|---|---|---|
| 1.0 | 0 | Brak krawędzi — za mały lub błąd skanowania |
| 0.7–0.9 | 0.6–1.8 | Luźne sprzężenie — dobra architektura |
| 0.4–0.7 | 1.8–3.6 | Umiarkowane — do monitorowania |
| 0.2–0.4 | 3.6–4.8 | Gęste sprzężenie — potencjalne problemy |
| 0.0–0.2 | 4.8–6.0+ | Krytyczne — "big ball of mud" |

### Dane empiryczne Java GT (n=59)

| Kategoria | Średnia CD | p-value |
|---|---|---|
| **POS** | **0.454** | — |
| **NEG** | **0.299** | — |
| Różnica | +0.155 | — |
| Mann-Whitney p | **0.004 \*\*** | drugi dyskryminator |

CD jest **drugim najsilniejszym dyskryminatorem** po Cohesion (p=0.004 vs p=0.0002). Partial r = +0.342, p=0.069 (kontrola rozmiaru) — słabszy po kontroli, ale MW test istotny.

### Dlaczego CD nie jest biasowane na DDD

Wcześniejszy zarzut: "CD faworyzuje DDD bo DDD ma luźne warstwy". Zbadane eksperymentalnie (sesja Turn 22-23):

| Kategoria | Ratio (średnia) | n |
|---|---|---|
| DDD-POS | 2.62 | 4 |
| non-DDD-POS | 2.32 | 9 |
| NEG | 3.89–4.25 | varies |

Mann-Whitney DDD vs non-DDD: p=0.40 → **brak biasu**. Hexagonal, CQRS-lite, layered z interfejsami mają podobny ratio do DDD — bo dobrze zrobiona architektura w każdym wzorcu utrzymuje luźne sprzężenia.

### Kierunek sygnału per język (kluczowy problem)

**Java:** wyższy ratio → NEG (p=0.034 przy n=13)

**Python:** sygnał **odwrócony** — wyższy ratio często → POS.

Wyjaśnienie mechanizmu (sesja Turn 36):
- Java złe projekty: "tangled imports, god classes" → dużo krawędzi
- Python złe projekty: "flat spaghetti" (youtube-dl: 895 modułów, brak struktury) → *mało* krawędzi między namespace'ami

Z tego powodu w AGQ v3c Python CD ma wagę **0.15** (niższą) i uzupełniany jest przez **flat_score** (waga 0.35).

### Związek z Acyclicity

Z macierzy korelacji (n=357): r(A, CD) = 0.267 — częściowa redundancja. Oba mierzą brak silnych powiązań: A przez brak cykli, CD przez niską gęstość. Jednak empirycznie CD wnosi dodatkowy sygnał (discriminates p=0.004 dla Javy gdzie A p=0.030 — oba istotne, ale mierzą różne aspekty).

### Jolak cross-validation

Jolak repos mają gęstsze coupling: CD≈0.316 vs GT-NEG=0.380. Sugeruje że nasz GT nie reprezentuje "enterprise middleware" — złożonych systemów mikroserwisowych z natury gęstym coupligniem.

## Definicja formalna

\[\text{CD} = 1 - \min\!\left(1,\ \frac{|E_{\text{internal}}|}{|V_{\text{internal}}| \cdot 6.0}\right)\]

Gdzie:
- \(|E_{\text{internal}}|\) = liczba krawędzi wewnętrznych (między modułami własnymi projektu)
- \(|V_{\text{internal}}|\) = liczba węzłów wewnętrznych (własne moduły projektu)
- 6.0 = empiryczny próg "krytycznego" ratio

Alternatywnie: \(\text{ratio} = |E| / |V|\), \(\text{CD} = \max(0, 1 - \text{ratio}/6)\).

**Waga w formule AGQ:**
- AGQ v3c Java: \(w_{\text{CD}} = 0.20\)
- AGQ v3c Python: \(w_{\text{CD}} = 0.15\)

**Walidacja statystyczna** (Java GT n=59):
- Mann-Whitney p = 0.004 \*\*
- Partial r = +0.342, p=0.069 (kontrola rozmiaru)
- Drugi najsilniejszy dyskryminator per-komponent

## Zobacz też

- [[Coupling]] — pojęcie sprzężenia
- [[edges]] — surowe krawędzie grafu
- [[nodes]] — surowe węzły grafu
- [[Graph Metric]] — klasa metryk grafowych
- [[Metrics Index]] — porównanie wszystkich metryk
- [[E2 Coupling Density]] — eksperyment walidacyjny CD
