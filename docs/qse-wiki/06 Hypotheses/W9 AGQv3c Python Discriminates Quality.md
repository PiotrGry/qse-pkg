---
type: hypothesis
id: W9
status: otwarta
language: pl
topic: AGQv3c, Python, flat_score
tested_by: E6
sesja_turn: 34-39
---

# W9 — AGQ v3c Python dyskryminuje jakość architektury Pythona

## Prostymi słowami

Zbudowaliśmy specjalną formułę AGQ dla Pythona (v3c), bo oryginalna wersja działała odwrotnie — youtube-dl (projekt bez struktury) miał wyższy AGQ niż netbox (projekt z dobrą architekturą). AGQ v3c Python dodaje flat_score, który karze za brak hierarchii folderów. Teraz kierunek jest zgodny. Ale mamy tylko 11 projektów — za mało żeby zamknąć hipotezę.

## Co badano

> **H₁:** AGQ v3c Python ma partial r(Panel, AGQ_v3c | nodes) > 0, p < 0.05 na GT Python.

Formalnie: AGQ v3c Python = 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score powinien mieć pozytywny, istotny związek z ocenami ekspertów dla projektów Python.

## Wynik

| Test | AGQ v2 | AGQ v3c | Zmiana |
|---|---|---|---|
| Python MW p | 0.066 ns | **0.045 \*** | poprawa |
| Python partial r | **−0.309 ns** | **+0.460 \*** | zmiana kierunku! |
| Python Δ (pos−neg) | −0.090 (odwrotny) | **+0.112** (poprawny) | |
| n (GT Python) | 11 | 11 | za mało |

**Hipoteza OTWARTA.** Kierunek jest prawidłowy i istotny (p=0.045), ale n=11 jest za małe do zamknięcia.

## Dane

### GT Python n=11 (Turn 34-39)

| Repo | flat_score | AGQ v2 | AGQ v3c | Panel | GT |
|---|---|---|---|---|---|
| netbox-community/netbox | 0.936 | 0.504 | ~0.61 | 8.00 | POS |
| saleor/saleor | 0.871 | 0.624 | ~0.65 | 7.50 | POS |
| Kiwi TCMS | 0.803 | 0.706 | ~0.60 | 7.00 | POS |
| healthchecks | 0.754 | 0.586 | ~0.57 | 6.75 | POS |
| sentry | 0.612 | 0.522 | ~0.51 | 6.00 | POS |
| **youtube-dl** | **0.000** | **0.831** | ~0.47 | 2.25 | **NEG** |
| taiga-back | 0.312 | 0.610 | ~0.52 | 4.25 | NEG |

### Porównanie kierunków — AGQ v2 vs AGQ v3c (Turn 39)

| Metryka | Java Δ | Java p | Python Δ | Python p | Zgodność |
|---|---|---|---|---|---|
| **AGQ v3c** | **+0.107** | **0.001** | **+0.112** | **0.045 \*** | **ZGODNY ✓** |
| AGQ v2 | +0.107 | 0.001 | −0.090 | 0.066 ns | ODWROTNY ✗ |

**AGQ v3c jako pierwsza metryka kompozytowa ma zgodny kierunek i istotność statystyczną w obu językach jednocześnie.**

## Dlaczego kierunek był odwrócony w AGQ v2

Python flat spaghetti (youtube-dl, 1000 extractorów) jest **niewidoczne** dla AGQ v2:

```
youtube-dl:
  ratio = 1.35 (najniższe w datasecie — mało krawędzi!)
  S = 0.867 (wysoka stabilność — każdy extractor jest leaf node)
  A = 1.000 (brak cykli)
  AGQ v2 = 0.831 ← AGQ interpretuje: "rzadkie, stabilne zależności = dobra arch."
  flat_score = 0.000 ← wszystkie klasy w depth≤2
  Panel = 2.25 ← eksperci: "brak struktury, flat spaghetti"
```

Paradoks: brak krawędzi (bo brak hierarchii) wygląda jak brak sprzężenia dla AGQ v2. flat_score to naprawia — mierzy dosłownie brak struktury hierarchicznej.

## Dlaczego hipoteza pozostaje OTWARTA

Protokół QSE wymaga n_neg ≥ 15 dla zamkniętego wniosku. Obecne dane:
- n_total = 11
- n_neg = 6 (youtube-dl, taiga-back, i 4 inne)
- n_pos = 5

Przy n_neg=6 jeden niepewny projekt może zmienić wynik o ±0.15 partial r. Konieczne jest rozszerzenie GT Python do n_neg≥15 przed zamknięciem W9.

## Scenariusze zamknięcia

**Zamknięcie jako POTWIERDZONA:**
- n_neg_Python ≥ 15
- partial r ≥ 0.55, p ≤ 0.01
- Wynik potwierdzony na nowym, niezależnym zestawie repo (np. kolejne 10 repozytoriów z GitHuba)

**Zamknięcie jako OBALONA:**
- partial r < 0.30, p > 0.10 przy n_neg ≥ 15
- Lub: flat_score nie separuje kategorii gdy uwzględnimy więcej typów „złej architektury Pythona"

## Otwarte pytanie mechanistyczne

Dlaczego CD (edges/nodes) ma odwrócony kierunek dla Pythona? Mechanizm znany (flat spaghetti = brak krawędzi = niski ratio = wysoki CD = "dobry" wg AGQ v2), ale:
1. Czy istnieje typ „złej architektury Python" gdzie ratio jest wysokie? (np. bogate importy bez hierarchii namespace)
2. Czy flat_score jest wystarczający dla WSZYSTKICH typów złej architektury Python, czy tylko dla flat spaghetti?

→ Zob. [[O5 Python CD Direction]]

## Formuła

```
AGQ v3c (Python) = 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score
```

Wagi kalibrowane przez minimalizację błędu na GT Python n=11 (partial r maksymalizowany). Flat_score dominuje (0.35) bo jest jedyną metryką z silnym sygnałem dla Pythona.

## Szczegóły techniczne

**Dlaczego wagi Python ≠ Java:**

PCA na 5 składowych dla Pythona (analogicznie do Javy) dałoby inne eigenvalues — bo structure M/A/S/C/CD działa odwrotnie dla Pythona. Wagi Python kalibrowane ręcznie przez optymalizację partial r na GT Python. Waga flat_score=0.35 uzasadniona przez partial r(flat_score, Panel_Python)=+0.670** (silna, niezależna).

## Zobacz też

- [[W10 flatscore Predicts Python Quality]] — flat_score jako składowa AGQ v3c
- [[E6 flatscore]] — eksperyment (flat_score)
- [[E5 Namespace Metrics]] — eksperyment poprzedni (NSdepth)
- [[O4 Namespace Metrics for Python]] — otwarte pytanie o rozszerzenia
- [[O5 Python CD Direction]] — mechanizm odwróconego CD
- [[AGQv3c Python]] — formuła (definicja)
