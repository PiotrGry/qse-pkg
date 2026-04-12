---
type: hypothesis
id: O4
status: otwarta
language: pl
topic: NSdepth, NSgini, Python, namespace
tested_by: E5
sesja_turn: 35-37
---

# O4 — Namespace Metrics poprawiają wyniki Pythona

## Prostymi słowami

NSdepth (głębokość hierarchii folderów) działa dobrze dla Javy (partial r=+0.698), ale słabo dla Pythona (r=+0.433 ns). Otwarte pytanie: czy istnieje metryka namespace lepsza niż flat_score dla Pythona, lub czy NSdepth można ulepszyć przez parametryzację progu głębokości?

## Co badano

> **H₁:** Metryki namespace (NSdepth, NSgini lub ich pochodne) mają partial r(Panel_Python | nodes) > 0, p < 0.05 i uzupełniają flat_score w formule AGQ v3c Python.

## Status

**OTWARTA** — częściowo zbadana (E5), ale bez zamkniętego wniosku dla Pythona.

## Wyniki E5 (stan obecny)

| Metryka | Java partial r | Java p | Python partial r | Python p |
|---|---|---|---|---|
| NSdepth | +0.698 | 0.008 ** | +0.433 | 0.122 ns |
| NSgini | ns | ns | ns | ns |
| flat_score (E6) | ns | ns | **+0.670** | **<0.01 \*\*** |

NSdepth działa dla Javy — ale Python ma strukturalnie płytszą hierarchię nawet w dobrych projektach (mean_depth = 3.7 POS vs 3.1 NEG → Δ=0.6 za mała).

## Otwarte pytania

### 1. Czy NSdepth z innym progiem działa lepiej dla Pythona?

Obecny NSdepth = max(len(fqn.split('.'))) per projekt. Możliwe ulepszenia:
- Percentyl 75 depth (zamiast max) — odporniejszy na outliery
- Mean_depth per namespace (nie per projekt)
- Threshold: depth>3 zamiast depth>2 (jak flat_score)

### 2. Czy NSgini jest bezwartościowy czy tylko nieoptymalne?

NSgini = Gini klas per namespace. Wyniki: ns wszędzie. Hipoteza dlaczego: dobre projekty też mają moduły różnej wielkości (np. `dcim/` może mieć 500 klas, `circuits/` tylko 30). Gini penalizuje naturalną heterogenność. Możliwa alternatywa: Gini tylko po **poziomach** (na tym samym poziomie hierarchii).

### 3. Combo NSdepth + flat_score

Czy dodanie NSdepth jako drugiej metryki namespace do AGQ v3c Python poprawiłoby wynik?

Wstępny test (Turn 36): Combo 0.5·NSdepth + 0.5·AGQ v2 na Javie → r=+0.615 p=0.025 — **gorsze** od samego AGQ v2 (r=+0.675). Sygnał z NSdepth rozcieńczał się w kombinacji. To może być inne dla Pythona gdzie NSdepth jest słabszy.

### 4. Metryki specyficznie pythonowe

Kandydaci których nie przetestowano:
- `__init__.py` density: ile klas per `__init__.py` — wysoka gęstość = flat namespace
- Import depth: głębokość importów w `__init__.py` (re-eksporty)
- Module heterogeneity: odchylenie standardowe rozmiarów modułów

## Warunki zamknięcia

1. n_neg_Python ≥ 15 (konieczny dla miarodajnych testów)
2. partial r(nowa_metryka, Panel_Python | nodes) > 0.55, p < 0.05
3. Nowa metryka wnosi sygnał **ortogonalny** do flat_score (r(nowa, flat_score) < 0.7)

## Powiązania

- [[E5 Namespace Metrics]] — eksperyment (NSdepth/NSgini)
- [[E6 flatscore]] — obecne rozwiązanie dla Pythona
- [[W9 AGQv3c Python Discriminates Quality]] — hipoteza o całej formule
- [[O5 Python CD Direction]] — pokrewne otwarte pytanie
- [[Hypotheses Register]] — pełna lista hipotez
