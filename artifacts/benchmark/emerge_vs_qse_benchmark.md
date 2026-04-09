# Benchmark: QSE AGQ vs Emerge - walidacja krzyżowa modularity

**Data:** 2026-03-21
**Dane:** `artifacts/benchmark/emerge_vs_qse_comparison.json`
**Skrypt:** `scripts/compare_emerge.py`

---

## 1. Cel eksperymentu

Walidacja krzyżowa metryki **modularity** algorytmu QSE/AGQ z niezależnym narzędziem open-source **Emerge** (glato/emerge, ~1k stars, Python).

Oba narzędzia implementują algorytm Louvain community detection na grafie zależności. Porównanie pozwala odpowiedzieć na pytania:

1. Czy QSE poprawnie buduje graf zależności? (convergent validity)
2. Czy sam Louvain Q wystarcza do predykcji jakości, czy potrzeba composite score?
3. Jak dalece definicja grafu wpływa na wartość modularity?

---

## 2. Metodologia

### Narzędzia

| | QSE/AGQ | Emerge 2.0.7 |
|---|---|---|
| Algorytm | Louvain na digraph importów (wewnętrznych + zewnętrznych) | Louvain na digraph importów (tylko pliki w source dir) |
| Normalizacja Q | `max(0, Q) / 0.75` | Raw Q |
| Węzły | Moduły (dotted paths, w tym external) | Pliki (.py w source dir) |
| Krawędzie | Import statements (AST, bez `__init__.py`) | Import statements (regex/AST) |
| Output | Q + acyclicity + stability + cohesion → AGQ | Q + fan-in/fan-out + SLOC |

### Próbka

16 repozytoriów Python z benchmarku AGQ (Python-80), dobranych z pełnego rozkładu AGQ:
- Zakres AGQ: 0.651 (thefuck) - 0.838 (yt-dlp)
- Zakres wielkości: 54 nodes (httpcore) - 1337 nodes (yt-dlp)
- Emerge files: 18 (requests) - 1128 (yt-dlp)

### Procedura

1. Shallow clone (`--depth 1`) każdego repo
2. Uruchomienie Emerge z konfiguracją: `file_scan: [dependency_graph, fan_in_out, louvain_modularity]`
3. Ekstrakcja `louvain-modularity-dependency-graph` z JSON output
4. Porównanie z QSE raw Q (`modularity_normalized * 0.75`) z benchmarku `agq_enhanced_python80.json`

---

## 3. Wyniki

### 3.1 Tabela porównawcza

```
Repo               Em Q  QSE Q   Diff  Em f  QSE n   Acy  Stab   Coh    AGQ  Fingerprint  Hotspot
thefuck           0.470  0.415 -0.055   210    273  1.00  0.71  0.34  0.651 LOW_COHESION    0.000
uvicorn           0.390  0.378 -0.013    40    117  1.00  0.76  0.59  0.712      LAYERED    0.137
nox               0.380  0.367 -0.013    21     90  1.00  0.69  0.72  0.724     MODERATE    0.109
requests          0.400  0.609 +0.209    18     67  1.00  0.65  0.45  0.728     MODERATE    0.191
sanic             0.390  0.289 -0.101   132    322  1.00  0.96  0.59  0.733      LAYERED    0.135
glances           0.470  0.386 -0.084   150    203  1.00  0.93  0.51  0.740      LAYERED    0.124
paramiko          0.390  0.374 -0.016    44    133  1.00  0.90  0.58  0.745      LAYERED    0.091
scrapy            0.290  0.339 +0.049   177    417  1.00  0.97  0.59  0.754      LAYERED    0.113
luigi             0.410  0.412 +0.002   102    270  1.00  0.91  0.58  0.760      LAYERED    0.063
poetry            0.380  0.417 +0.037   191    428  1.00  0.92  0.60  0.770      LAYERED    0.141
httpcore          0.200  0.428 +0.228    31     54  1.00  1.00  0.56  0.782      LAYERED    0.081
httpx             0.310  0.465 +0.155    23     70  1.00  0.81  0.70  0.783      LAYERED    0.068
scikit-learn      0.340  0.503 +0.163   635   1176  0.99  0.82  0.70  0.795      LAYERED    0.104
textual           0.360  0.430 +0.070   246    523  1.00  0.99  0.65  0.803      LAYERED    0.098
mako              0.600  0.493 -0.107    33     87  1.00  0.90  0.69  0.813      LAYERED    0.125
yt-dlp            0.240  0.467 +0.227  1128   1337  1.00  0.87  0.86  0.838      LAYERED    0.058
```

### 3.2 Korelacje

| Para metryk | r | n | Interpretacja |
|---|---|---|---|
| **Emerge Q vs QSE Q (raw)** | **+0.063** | 16 | Brak korelacji |
| **Emerge Q vs QSE AGQ** | **-0.311** | 16 | Słaba negatywna |
| **Emerge Q vs hotspot_ratio** | **+0.448** | 15 | Umiarkowana pozytywna (wyższe Q = więcej hotspotów!) |
| **QSE AGQ vs hotspot_ratio** | **-0.547** | 15 | Umiarkowana negatywna (wyższy AGQ = mniej hotspotów) |

### 3.3 Statystyki zbiorcze

| Metryka | Wartość |
|---|---|
| Mean Emerge Q | 0.376 |
| Mean QSE Q (raw) | 0.423 |
| Mean diff (QSE - Emerge) | +0.047 |

### 3.4 Faza 2: Fan-out vs QSE metryki

```
Repo             FO avg FO max  FO ratio  Stab   Coh    AGQ
mako               1.35     12     8.89   0.90   0.69  0.813
requests           1.89     22    11.64   0.65   0.45  0.728
thefuck            2.01     19     9.45   0.71   0.34  0.651
glances            2.17     32    14.75   0.93   0.51  0.740
nox                2.19     27    12.33   0.69   0.72  0.724
uvicorn            2.24     25    11.16   0.76   0.59  0.712
luigi              2.50     29    11.60   0.91   0.58  0.760
paramiko           2.55     36    14.12   0.90   0.58  0.745
httpx              2.67     23     8.61   0.81   0.70  0.783
sanic              2.89     58    20.07   0.96   0.59  0.733
poetry             3.29     39    11.85   0.92   0.60  0.770
textual            3.87     89    23.00   0.99   0.65  0.803
scrapy             4.24     36     8.49   0.97   0.59  0.754
yt-dlp             4.27   1009   236.30   0.87   0.86  0.838
httpcore           4.67     17     3.64   1.00   0.56  0.782
scikit-learn       5.12     44     8.59   0.82   0.70  0.795
```

#### Fan-out avg vs QSE metryki

| Para | r | t | df | p |
|---|---|---|---|---|
| FO avg vs QSE stability | **+0.462** | +1.95 | 14 | <0.10 |
| FO avg vs QSE modularity | -0.033 | -0.12 | 14 | n.s. |
| FO avg vs QSE cohesion | +0.384 | +1.56 | 14 | n.s. |
| FO avg vs QSE AGQ | **+0.505** | +2.19 | 14 | **<0.05** |

#### Fan-out max vs QSE metryki

| Para | r | t | df | p |
|---|---|---|---|---|
| FO max vs QSE stability | +0.053 | +0.20 | 14 | n.s. |
| FO max vs QSE modularity | +0.136 | +0.52 | 14 | n.s. |
| FO max vs QSE cohesion | **+0.579** | +2.66 | 14 | **<0.05** |
| FO max vs QSE AGQ | +0.486 | +2.08 | 14 | <0.10 |

#### Fan-out vs churn (external validation)

| Para | r | t | df | p |
|---|---|---|---|---|
| FO avg vs hotspot_ratio | -0.411 | -1.62 | 13 | n.s. |
| FO max vs hotspot_ratio | -0.408 | -1.61 | 13 | n.s. |
| FO avg vs churn_gini | +0.181 | +0.66 | 13 | n.s. |

#### Confound: efekt wielkości repo

| Para | r | t | df | p |
|---|---|---|---|---|
| QSE nodes vs FO avg | **+0.673** | +3.41 | 14 | **<0.05** |
| QSE nodes vs FO max | **+0.713** | +3.80 | 14 | **<0.05** |
| QSE nodes vs QSE stability | +0.129 | +0.49 | 14 | n.s. |

---

## 4. Analiza i interpretacja

### 4.1 Dlaczego Emerge Q i QSE Q nie korelują? (r=0.06)

Pomimo identycznego algorytmu (Louvain), narzędzia budują **fundamentalnie różne grafy**:

1. **Różna populacja węzłów**: QSE włącza moduły zewnętrzne (stdlib, third-party) jako węzły grafu. Emerge skanuje wyłącznie pliki w source directory. Dla httpcore: Emerge widzi 31 plików, QSE 54 moduły.

2. **Różna granularność krawędzi**: QSE parsuje import statements do dotted module paths; Emerge rozwiązuje do plików. To zmienia strukturę community detection.

3. **Louvain jest niestabilny**: Algorytm Louvain jest heurystyczny i niedeterministyczny - drobne zmiany w grafie mogą istotnie zmienić wartość Q. Przy różnych definicjach grafu Q może być całkowicie rozbieżne.

**Wniosek**: Raw Louvain Q **nie jest metrą porównywalną między narzędziami**. Sam algorytm jest identyczny, ale Q zależy od definicji grafu, nie tylko od struktury kodu.

### 4.2 Fan-out: co mierzy i jak się ma do QSE stability

**Kluczowy wynik fazy 2**: Emerge avg fan-out koreluje istotnie z QSE AGQ (**r=+0.505, p<0.05**) oraz marginalnie z QSE stability (r=+0.462, p<0.10). Emerge max fan-out koreluje z QSE cohesion (**r=+0.579, p<0.05**).

Kierunek jest **pozytywny** - wyższy fan-out = wyższy AGQ/stability/cohesion. To jest kontraintuicyjne (spodziewalibyśmy się, że "więcej zależności = gorsze"). Wyjaśnienie: **confound wielkości repo**. Fan-out avg silnie koreluje z liczbą węzłów (r=+0.673, p<0.05) - większe repo mają naturalnie wyższy fan-out. Natomiast QSE stability **nie koreluje** z wielkością repo (r=+0.129, n.s.).

To oznacza:
1. **Emerge fan-out jest confounded przez wielkość projektu** - nie można go interpretować bez normalizacji na rozmiar
2. **QSE stability jest size-invariant** - to ważna przewaga, bo stability mierzy variance instability per pakiet, nie bezwzględną liczbę zależności
3. **Fan-out i stability mierzą różne rzeczy**: fan-out = ile modułów importujesz, stability = jak zróżnicowane są role pakietów (stabilne jądro vs niestabilne adaptery). Oba są użyteczne, ale nie wymienne

Fan-out nie koreluje istotnie z churn (r=-0.41, n.s.) ani z churn_gini (r=+0.18, n.s.), co potwierdza, że sam fan-out bez normalizacji nie jest dobrym predyktorem maintenance outcomes.

### 4.3 Korelacje z hotspot_ratio - wyniki i zastrzeżenia

Na podpróbce 16 repo (Emerge subset) zaobserwowano:

| Metryka | r | t | p | Kierunek |
|---|---|---|---|---|
| Emerge Q vs hotspot_ratio | +0.448 | 1.805 | <0.10 (marginalnie) | Wyższe Q = więcej hotspotów |
| QSE AGQ vs hotspot_ratio | -0.547 | -2.353 | <0.05 | Wyższy AGQ = mniej hotspotów |

Spearman (odporny na outliers): Emerge rho=+0.457, AGQ rho=-0.532.

Usunięcie outliera (mako, Emerge Q=0.6) nie zmienia trendu: r=+0.495.

#### ZASTRZEŻENIE: kontekst pełnego benchmarku

Te korelacje dotyczą **podpróbki 16 repo** wybranych do testu Emerge. Na pełnym benchmarku Python-80 korelacje są **znacznie słabsze**:

| Metryka | r (n=16 Emerge subset) | r (n=77 Python-80) | r (n=234 cross-language) |
|---|---|---|---|
| QSE modularity (raw Q) vs hotspot | - | -0.133 (n.s.) | -0.066 (n.s.) |
| QSE AGQ vs hotspot | -0.547 (p<0.05) | -0.127 (n.s.) | +0.067 (n.s.) |
| QSE AGQ-adj vs hotspot | - | - | +0.143 (p<0.05) |

**Interpretacja**: Silna korelacja na n=16 jest prawdopodobnie artefaktem doboru próbki. Na pełnym benchmarku (n=77, n=234) ani sam Louvain Q, ani AGQ nie korelują istotnie z hotspot_ratio. Jedyna istotna korelacja cross-language to AGQ-adj vs hotspot (r=+0.14, p<0.05) - słaba i w odwrotnym kierunku niż oczekiwano.

Wcześniej zweryfikowane korelacje cross-language (z MEMORY.md) dotyczą **poszczególnych składowych**, nie composite AGQ:
- acyclicity vs hotspot_ratio: r=+0.223, p=0.001
- stability vs hotspot_ratio: r=+0.180, p=0.006

Te korelacje są pozytywne (wyższa acyclicity/stability = więcej hotspotów), co jest **kontraintuicyjne** i wymaga dalszej analizy.

### 4.3 Wartość porównania: czym QSE się różni od Emerge

Niezależnie od predykcyjności, porównanie ujawnia fundamentalną różnicę scope'u:

| Wymiar | Emerge | QSE |
|---|---|---|
| Modularity (Louvain Q) | tak | tak |
| Fan-in / Fan-out | tak (per-file) | w grafie, ale nie eksponowane |
| SLOC | tak | nie |
| Acyclicity (SCC) | **nie** | tak |
| Stability (instability variance) | **nie** | tak |
| Cohesion (LCOM4) | **nie** | tak |
| Composite score | **nie** | tak (AGQ) |
| Cross-language normalization | **nie** | tak (AGQ-z) |
| Architectural fingerprint | **nie** | tak |

QSE dostarcza **4 ortogonalne wymiary** vs 1 u Emerge. Czy ten composite score predykuje lepiej niż sam Q - na dużej próbce efekt jest słaby i wymaga dalszych badań.

### 4.4 Ablacja składowych AGQ na podpróbce

- **Acyclicity**: prawie wszędzie = 1.0 (Python repos rzadko mają cykle) - nie różnicuje w tej próbce
- **Stability**: zakres 0.65–1.00 - różnicuje dobrze
- **Cohesion**: zakres 0.34–0.86 - najwyższy spread, silnie różnicuje
- **Modularity**: zakres 0.29–0.61 (raw) - różnicuje

---

## 5. Wnioski

### Co potwierdza ten benchmark

1. **Louvain Q nie jest porównywalny między narzędziami** (r=0.06) - definicja grafu decyduje o wartości, nie tylko struktura kodu
2. **QSE mierzy więcej**: 4 wymiary architektoniczne vs 1 u Emerge (+ fingerprint, AGQ-z, ChurnRisk)
3. **Emerge daje per-file fan-in/fan-out**, czego QSE nie eksponuje - potencjalne ulepszenie

### Czego NIE potwierdza (uczciwie)

1. ~~QSE AGQ predykuje hotspoty lepiej niż sam Louvain Q~~ - na podpróbce n=16 efekt jest widoczny (r=-0.55 vs r=+0.45), ale na pełnym benchmarku n=77/234 korelacje AGQ vs hotspot są bliskie zeru
2. Predykcyjność architektonicznych metryk grafowych dla maintenance outcomes **pozostaje otwartym pytaniem badawczym** - to centralna hipoteza grantu, nie potwierdzona konkluzja

### Dla grantu - co można bezpiecznie cytować

> "Cross-validation with independent tool Emerge (n=16 Python repos) confirms that Louvain modularity values are graph-definition dependent (r=0.06 between tools despite identical algorithm), motivating the need for standardized graph construction methodology. QSE extends single-metric tools like Emerge with three additional architectural dimensions (acyclicity, stability, cohesion), providing richer characterization of software structure."

### Otwarte pytania

1. Dlaczego acyclicity i stability korelują **pozytywnie** z hotspot_ratio? (Hipoteza: confounding - większe, bardziej dojrzałe repo mają zarówno lepszą architekturę, jak i więcej hotspotów)
2. Czy per-file breakdown AGQ (zamiast jednego score per repo) poprawi predykcyjność?
3. Czy dodanie Emerge-style fan-in/fan-out jako feature poprawi korelacje?

### Ograniczenia

- n=16 (tylko Python) - wyniki wymagają replikacji na Java/Go z Emerge
- Shallow clones mogą wpływać na Emerge (brak pełnej historii git)
- Emerge v2.0.7 - nowsze wersje mogą mieć inny parser
- QSE benchmark pochodzi z 2026-03-08; wersje repo mogą się różnić
- Podpróbka 16 nie jest losowa - wybrana co 5-ty z posortowanego AGQ, co może wprowadzać bias

---

## 6. Reprodukcja

```bash
# Instalacja
pip install emerge-viz

# Klonowanie repo
git clone --depth 1 https://github.com/<owner>/<repo>.git /tmp/<repo>

# Emerge
emerge -c <config.yaml>

# QSE (z benchmarku)
# Dane w artifacts/benchmark/agq_enhanced_python80.json

# Pełny skrypt porównawczy
python3 scripts/compare_emerge.py \
    --repos-dir /tmp/emerge-test \
    --benchmark artifacts/benchmark/agq_enhanced_python80.json \
    --repos httpx,scrapy,requests,nox,scikit-learn
```
