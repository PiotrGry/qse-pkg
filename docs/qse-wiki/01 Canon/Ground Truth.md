---
type: canon
language: pl
---

# Ground Truth — dane empiryczne i walidacja

## Prostymi słowami

Ground Truth (GT) to zaufany punkt odniesienia, który służy do sprawdzenia czy formuła AGQ rzeczywiście odróżnia dobre projekty od złych. Działa jak „złoty standard": najpierw eksperci oceniają repozytoria (czy architektura jest dobra czy zła), potem sprawdzamy, czy AGQ zgadza się z ich oceną. To jedyny sposób żeby wiedzieć, że metryka nie jest przypadkowa.

---

## Szczegółowy opis

### Metodologia panelu ekspertów

Panel składa się z 4 symulowanych recenzentów, każdy z inną perspektywą:
1. **Puryst architektoniczny** — rygorystycznie ocenia zgodność z zasadami SOLID i wzorcami
2. **Pragmatyk** — bierze pod uwagę kontekst biznesowy i dziedzinę projektu
3. **Ekspert metryk** — patrzy przez pryzmat znanych metryk architektonicznych
4. **Praktyk przemysłowy** — priorytet: łatwość utrzymania i onboardingu nowych developerów

**Protokół:**
- Każdy ekspert ocenia repozytorium w skali **1–10**
- Panel score = **średnia 4 ocen**
- Wymaganie zgodności: **σ ≤ 2.0** (niezgodność powyżej tego progu → wykluczenie z GT)
- Label: panel score **≥ 6.0 → POS** (dobra architektura), **< 6.0 → NEG** (zła architektura)

---

## Java Ground Truth (n=59)

### Kluczowe statystyki

| Właściwość | Wartość |
|---|---|
| Łączna liczba repozytoriów | 59 |
| Pozytywne (POS) | 31 |
| Negatywne (NEG) | 28 |
| Śr. AGQ v3c dla POS | 0.571 |
| Śr. AGQ v3c dla NEG | 0.486 |
| Gap (POS − NEG) | 0.085 |
| **Mann-Whitney U p-value** | **0.000221** |
| **Spearman ρ** | **0.380 (p=0.003)** |
| Partial r (kontrola rozmiaru) | 0.447 (p=0.0004) |
| **AUC-ROC** | **0.767** |

> **Interpretacja AUC=0.767:** Model losowy ma AUC=0.500. AUC=0.767 oznacza, że w 76.7% przypadków gdy losowo wybierzemy jedno POS i jedno NEG repozytorium, AGQ poprawnie je uszereguje (POS > NEG). To solidny wynik dla metryki architektonicznej.

### Skład GT

```
Original GT (n=29)          Expansion batch (n=30)
  15 POS, 14 NEG              16 POS, 14 NEG
  plik: gt_java_final_fixed   plik: gt_java_candidates.json
  .json                       
                            ↓ merged (commit b336496, kwiecień 2026)
                            
Expanded GT (n=59) — gt_java_expanded.json
  31 POS, 28 NEG
  Gap: 0.115 → 0.085 (zawężenie oczekiwane z większą różnorodnością)
  Wszystkie testy istotności: p<0.01 ✓
```

### Strict Protocol GT (n=38)

Zaostrzone filtry panelowe eliminujące „szarą strefę" (repos z panel score bliskim progu 6.0):

| Filtr | Wartość |
|---|---|
| Panel score POS | ≥ 7.0 |
| Panel score NEG | ≤ 3.5 |
| Sigma (zgodność panelu) | < 2.0 |
| Zakres nodes | 100–5000 |
| **Wynik:** | **n=38 (20 POS, 18 NEG)** |

Wyniki na strict GT:

| Statystyka | Strict GT (n=38) | Full GT (n=59) |
|---|---|---|
| Partial r | **0.507** (p=0.001) | 0.447 (p=0.0004) |
| MW p-value | **0.0004** | 0.000221 |
| C partial r | **0.571** (p=0.0002) | — |
| S partial r | **0.410** (p=0.011) | — |

**Kluczowy wniosek:** Strict GT daje silniejsze wyniki (partial_r=0.507 vs 0.447), potwierdzając że „szara strefa" repos (panel 3.5–7.0) rozmywa sygnał. C jest najsilniejszą pojedynczą składową (partial_r=0.571).

Plik: `artifacts/gt_java_strict_v3.json`

### Per-komponent dyskryminacja (GT n=59)

| Składowa | Śr. POS | Śr. NEG | Δ | MW p | Istotność |
|---|---|---|---|---|---|
| Modularity (M) | 0.668 | 0.648 | +0.021 | 0.226 | ns |
| Acyclicity (A) | 0.994 | 0.974 | +0.020 | 0.030 | * |
| Stability (S) | 0.344 | 0.238 | +0.106 | 0.016 | * |
| Cohesion (C) | 0.393 | 0.269 | +0.124 | 0.0002 | *** |
| Coupling Density (CD) | 0.454 | 0.299 | +0.155 | 0.004 | ** |

**Kluczowy wniosek:** C i CD to najsilniejsze indywidualne dyskryminatory (*** i **). M samo w sobie jest nieistotne statystycznie (ns) — co tłumaczy jego wagę 0.20 w v3c zamiast wyższej.

### Znane problemy Java GT

**Problem 1: Utility libraries**

Repozytoria takie jak Guava, commons-lang, commons-collections dostają **niskie AGQ mimo dobrego projektu**. Powód: płaska struktura pakietów → niskie CD. Panel ekspertów poprawnie je oznacza jako POS, ale metryki same dają wynik NEG.

Planowane rozwiązanie: normalizacja uwzględniająca kategorię projektu (utility vs aplikacja).

**Problem 2: Małe NEG repozytoria**

Projekty takie jak shopping-cart, training-monolith: prosta struktura zawyża M i CD. Metryki same wskazałyby POS, panel ekspertów poprawnie oznacza NEG (ze względu na intencję projektu, nie jego rozmiar).

**Problem 3: Django false-negative**

Django dostaje NEG mimo uznanej dobrej architektury. Przyczyna techniczna: skaner wymaga lepszego wykrywania wewnątrz-pakietowego (intra-package detection). Zadanie P3 — zbadane, deferred.

---

## Python Ground Truth (n=30)

### Kluczowe informacje

- Plik: `artifacts/python_deepdive_results.json`
- **n=30** (13 POS, 17 NEG)
- Formuła: AGQ v3c Python ze składową **flat_score** (waga 0.35)

### Problem odwróconego kierunku (kluczowy!)

W standardowych metrykach (M, A, S, C, CD) dla Pythona obserwowano **odwrócony kierunek korelacji** — wyższe wartości nie odpowiadały lepszej architekturze. To jest znany efekt dla projektów Python, który wynika z charakterystyki przestrzeni nazw.

**Rozwiązanie: flat_score**

```
flat_score = 1 − flat_ratio
flat_ratio = % węzłów z głębokością namespace ≤ 2

youtube-dl:  895/895 węzłów na depth≤2 → flat_score = 0.000 (flat spaghetti)
saleor:     239/3763 węzłów na depth≤2 → flat_score = 0.936 (dobra hierarchia)
```

flat_score jest **jedynym sygnałem dla Pythona który nie jest odwrócony**:
- MW p=0.007 (dwustronna istotność)
- Partial r = +0.484 (p=0.007, po kontroli rozmiaru) — **zaktualizowane na większym zbiorze**
- Kierunek poprawny: POS repos mają wyższy flat_score

```
AGQ_v3c (Python) = 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score
```

### Dwa typy złej architektury Python

| Typ | Przykład | flat_score | Panel score | AGQ wykrywa? |
|---|---|---|---|---|
| Typ A: Flat spaghetti | youtube-dl, faker, PyGithub | ≈ 0.000 | < 3.0 | ✅ Tak |
| Typ B: Legacy monolith z hierarchią | buildbot, Medusa, SickChill | ≈ 0.950 | < 3.0 | ❌ Nie |

buildbot (panel=2.75) ma flat_ratio=0.054 — lepszy niż większość POS repozytoriów. Zbudowany na Twisted (2005) z głęboką hierarchią pakietów, ale fatalną architekturą wewnętrzną (god modules, mixed concerns). flat_score go nie wykrywa — potrzeba metryki semantycznej (rozmiar pliku, fan-out god modules).

### God-module metryki (Type E — kwiecień 2026)

Zbadano metryki god-module dla Pythona: god_ratio, max_fan_out, avg_file_size. Wynik:
- **Kierunek poprawny** (POS < NEG, zgodnie z oczekiwaniem)
- **Żadna nie osiąga istotności statystycznej** (p > 0.10)
- **buildbot false negative potwierdzona** (flat_score=0.946)
- Rekomendacja: god-module metryki jako eksperymentalna flaga, **nie** jako składowa formuły

---

## Jolak Cross-Validation (8 repozytoriów)

### Cel

Niezależna walidacja skanera Java QSE na repozytoriach przebadanych przez zewnętrznych badaczy (Jolak et al., 2025). Jolak et al. oceniali repozytoria Java ręcznie — możemy sprawdzić czy QSE zgadza się z ich wnioskami.

### Wyniki

| Właściwość | Wartość |
|---|---|
| Liczba repozytoriów | 8 |
| Narzędzie skanowania | czysty Python Java scanner (tree-sitter-java) |
| Średnia AGQ v3c | 0.535 |
| GT-POS średnia (dla porównania) | 0.585 |
| GT-NEG średnia (dla porównania) | 0.470 |
| **Wyniki Jolak potwierdzone** | **4/5 POTWIERDZONE, 1 PRAWDOPODOBNE** |

Wartość 0.535 leży dokładnie **pomiędzy** GT-POS (0.585) a GT-NEG (0.470) — tak jak oczekiwano dla nieznanego zbioru repozytoriów z mieszaną jakością.

### Obserwacja CD gap

Repozytoria Jolak: CD = 0.316 (vs GT-NEG CD = 0.380). Sugeruje, że GT może niedobrze reprezentować enterprise middleware — repozytoria enterprise mają gęstsze połączenia między modułami.

### Szerokie zróżnicowanie Stability

Stability (S) zmienia się w szerokim zakresie [0.065–0.954] w repozytoriach Jolak:
- Sentinel: S = 0.065
- motan: S = 0.111
- sofa-rpc: S = 0.116

To potwierdza, że S jest czułą miarą hierarchii architektonicznej i dobrze różnicuje repozytoria.

---

## Definicja formalna — statystyki walidacji

### Test Mann-Whitney U

Test nieparametryczny (nie zakłada rozkładu normalnego): czy dwie grupy (POS i NEG) mają różne mediany AGQ?

```
H₀: rozkład AGQ dla POS = rozkład AGQ dla NEG
H₁: rozkład AGQ dla POS > rozkład AGQ dla NEG (jednostronny)

Wynik Java GT (n=59): U = 624.0, p = 0.000221

p = 0.000221 << α = 0.05 → odrzucamy H₀
```

### AUC-ROC (Area Under Curve)

AUC mierzy zdolność modelu do rozróżniania klas. Dla binarnego klasyfikatora:
- AUC = 0.500 → model losowy (rzut monetą)
- AUC = 0.767 → QSE poprawnie uszeregowuje POS > NEG w 76.7% par

### Partial Spearman

Korelacja Spearmana z kontrolą zmiennej confoundingowej (rozmiar projektu w węzłach):

```
Partial r = 0.447 (p=0.0004)

Interpretacja: nawet po usunięciu efektu rozmiaru, 
AGQ koreluje z oceną ekspertów z r=0.447
```

---

## Zobacz też
[[QSE Canon]] · [[Invariants]] · [[Experiments Index]] · [[Hypotheses Register]] · [[Scanner]]
