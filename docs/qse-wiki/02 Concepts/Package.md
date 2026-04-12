---
type: concept
language: pl
---

# Pakiet (Package)

## Prostymi słowami

Pakiet to logiczne zgrupowanie modułów (plików) w strukturze projektu. W Javie to folder `com.company.app.domain`, w Pythonie to katalog `src/domain/`. Pakiety tworzą hierarchię — jak szuflady w szafie. QSE używa pakietów do obliczenia metryki Stability: nie per plik, ale per grupę plików tworzącą logiczną warstwę.

## Szczegółowy opis

### Pakiet jako jednostka Stability

Metryka [[Stability]] jest obliczana **na poziomie pakietów**, nie plików. Powód: instability per plik jest zbyt "szumowa" — jeden plik może mieć I=0, sąsiedni I=1, a razem tworzą spójną warstwę.

```
projekt/
├── src/api/           ← pakiet "api"   (I ≈ 1.0 — obrzeże)
│   ├── controller.py
│   └── routes.py
├── src/service/       ← pakiet "service" (I ≈ 0.5 — środkowa warstwa)
│   ├── order_svc.py
│   └── user_svc.py
└── src/domain/        ← pakiet "domain" (I ≈ 0.0 — jądro)
    ├── order.py
    └── user.py
```

### Jak QSE wykrywa pakiety

Pakiety są wykrywane na podstawie **hierarchii katalogów**:

- **Java**: package declaration w pliku (`package com.example.domain;`)
- **Python**: katalog z `__init__.py` lub katalog źródłowy

Granularność: QSE używa "package-level instability" — agreguje fan-in/fan-out wszystkich plików w pakiecie przed obliczeniem \(I\).

```
I_pakiet = ΣC_e(pliki) / (ΣC_a(pliki) + ΣC_e(pliki))
```

### Przykład: pakiety w dddsample (Java, Panel=8.25)

```
dddsample pakiety i ich instability:
  cargo (domain)          I = 0.42  ← rich domain, sporo fan-out wewnętrznego
  location (domain)       I = 0.38  
  voyage (domain)         I = 0.41  
  booking (application)   I = 0.71  ← warstwa aplikacyjna, zależy od domeny
  handling (application)  I = 0.68  
  interfaces              I = 0.89  ← obrzeże
```

Widoczna hierarchia I: domain (~0.4) < application (~0.7) < interfaces (~0.9). To wysoka wariancja → wysoki Stability.

### Pakiet a "flat" architektura

W Pythonie wiele projektów ma **flat packaging** — wszystkie moduły w jednym katalogu lub dwóch poziomach. Przykład: youtube-dl (Panel=2.25) ma 895 modułów, wszystkie w depth≤2. To skutkuje:
- Niskim NSdepth
- Niskim flat_score (bo zero modułów w głębszych namespace'ach)
- Niską wariancją I (wszystko podobne) → niski Stability

Ta właściwość prowadzi do [[flatscore]] jako dedykowanej metryki dla Pythona.

### Pakiety a Louvain (Modularity)

Pakiety wykryte przez Louvain nie muszą odpowiadać strukturze katalogów. Louvain wykrywa **społeczności** w grafie importów — grupy plików które dużo się nawzajem importują. Może to być inna granularność niż katalogi.

Przykład: Louvain może wykryć że `utils/` i `helpers/` to "jedna społeczność" (dużo wzajemnych importów), chociaż są w różnych katalogach. W ten sposób [[Modularity]] i [[Stability]] mierzą różne aspekty struktury pakietowej.

## Definicja formalna

Pakiet \(p\) to zbiór modułów ze wspólnym prefiksem namespace:

\[p = \{v \in M(P) \mid \text{namespace}(v) \text{ zaczyna się od } \text{prefix}(p)\}\]

Instability pakietu:

\[I(p) = \frac{\sum_{v \in p} C_e(v)}{\sum_{v \in p} C_e(v) + \sum_{v \in p} C_a(v)}\]

Gdzie \(C_e(v)\) = fan-out modułu \(v\) (krawędzie wychodzące do modułów poza \(p\)), \(C_a(v)\) = fan-in (krawędzie przychodzące od modułów poza \(p\)).

**Uwaga:** krawędzie wewnątrz pakietu nie wliczają się do \(C_e\) ani \(C_a\) — liczymy zależności **między** pakietami, nie wewnątrz nich.

**Wariancja stabilności:**

\[\text{Stab} = \min\!\left(1,\ \frac{\text{Var}(I(p_1), \ldots, I(p_k))}{0.25}\right)\]

Normalizator 0.25 to maksymalna wariancja dla zmiennej binarnej (0/1).

## Zobacz też

- [[Module]] — pliki wewnątrz pakietu
- [[Stability]] — metryka obliczana per pakiet
- [[DMS Instability]] — Martin's Instability I
- [[Hierarchy]] — pakiety tworzą hierarchię
- [[NSdepth]] — głębokość hierarchii pakietów
