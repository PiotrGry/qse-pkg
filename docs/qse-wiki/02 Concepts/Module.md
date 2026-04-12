---
type: concept
language: pl
---

# Moduł (Module)

## Prostymi słowami

Moduł w QSE to jeden plik z kodem — jeden `*.py`, jeden `*.java`, jeden `*.go`. Wyobraź sobie każdy plik jako osobny pojemnik: co wchodzi do środka (importy) i co wychodzi (eksportowane klasy/funkcje). Graf zależności QSE to mapa tych pojemników i połączeń między nimi.

## Szczegółowy opis

### Moduł jako węzeł grafu

W QSE moduł odpowiada granularności **pliku** — jeden plik = jeden węzeł w grafie zależności. Ta decyzja projektowa wynika z praktyki: skanery tree-sitter pracują na plikach, i większość "importów" jest deklarowana na poziomie pliku.

```
module = plik kodu źródłowego (po filtrowaniu zewnętrznych)
```

Typy modułów w systemie QSE:

| Typ | Opis | Przykład |
|---|---|---|
| **Wewnętrzny** | Plik projektu, wchodzi do grafu | `src/domain/order.py` |
| **Zewnętrzny** (stdlib) | Biblioteka systemowa, filtrowany | `os`, `java.util` |
| **Zewnętrzny** (third-party) | Zewnętrzna biblioteka, filtrowany | `requests`, `spring` |

Tylko moduły wewnętrzne wchodzą do grafu jako węzły. Importy do modułów zewnętrznych są ignorowane.

### Granularność: plik vs. klasa vs. pakiet

QSE świadomie wybiera granularność **pliku**, a nie klasy czy pakietu:

- **Plik** — naturalna jednostka importu w większości języków; plik = kontekst `import` / `use` / `include`
- **Klasa** — za drobna; tysiące węzłów spowalnia algorytmy, a importy są i tak per-plik
- **Pakiet** — za gruby; gubi wewnętrzną strukturę pakietu, niespójna z tym co widzi programista

Wyjątek: metryka Stability używa **pakietów** (grup plików) do obliczenia instability — ale zbudowanych na podstawie grafu plikowego.

### Moduł jako kontener klas

Jeden moduł (plik) może zawierać wiele klas. Cohesion (LCOM4) jest obliczana **per klasa**, ale agregowana **per projekt** — więc moduł jest transparentny dla Cohesion.

```
plik order.py
├── klasa Order      → LCOM4 obliczone
├── klasa OrderItem  → LCOM4 obliczone
└── klasa OrderEvent → LCOM4 obliczone
```

### Właściwości modułu w grafie

Dla każdego węzła-modułu \(v\) QSE oblicza:

| Właściwość | Opis | Znaczenie |
|---|---|---|
| **fan-in** \((C_a)\) | Liczba modułów importujących v | "Ile zależy od mnie?" |
| **fan-out** \((C_e)\) | Liczba modułów importowanych przez v | "Od ilu zależę?" |
| **instability** \(I\) | \(C_e / (C_a + C_e)\) | Rola w hierarchii |
| **przynależność do SCC** | Czy v jest w cyklu? | Dla Acyclicity |
| **przynależność do klastra** | Wynik Louvain | Dla Modularity |

### Liczba modułów w benchmarku

Dane z benchmarku (kwiecień 2026, 558 repozytoriów):

| Język | Mediana n_internal | Min | Max |
|---|---|---|---|
| Python | ~300 | 2 | 17595 |
| Java | ~800 | 9 | 17596 |
| Go | ~200 | 10 | 3604 |
| TypeScript | ~150 | 10 | 2000 |

Przykłady skrajne:
- **attrs (Python)**: 10 modułów — AGQ=1.000 (mały, idealny)
- **home-assistant (Python)**: 17595 modułów — AGQ=0.581 (duży, płaski)
- **quarkus (Java)**: 17596 modułów — AGQ=0.647

## Definicja formalna

Moduł wewnętrzny projektu \(P\):

\[M(P) = \{f \in \text{files}(P) \mid f \notin \text{stdlib}(L) \cup \text{third\_party}(P)\}\]

Gdzie \(L\) = język projektu, \(\text{third\_party}(P)\) = biblioteki zewnętrzne wykryte z pliku zależności (`requirements.txt`, `pom.xml`, `go.mod`).

Instability modułu (używana w Stability):

\[I(v) = \frac{|\{u : (v, u) \in E\}|}{|\{u : (v, u) \in E\}| + |\{u : (u, v) \in E\}|}\]

Moduł z \(I = 0\): stabilne centrum — nic nie importuje, wiele od niego zależy.
Moduł z \(I = 1\): niestabilne obrzeże — dużo importuje, nikt nie zależy.

## Zobacz też

- [[Dependency Graph]] — graf zbudowany z modułów
- [[Package]] — grupowanie modułów
- [[Stability]] — używa instability per moduł
- [[Cohesion]] — obliczana per klasa w module
- [[DMS Instability]] — szczegóły metryki Martina
