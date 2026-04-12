---
type: concept
language: pl
---

# Repozytorium (Repository)

## Prostymi słowami

Repozytorium to jednostka analizy w QSE — jeden projekt na GitHubie lub lokalnie. QSE skanuje całe repozytorium naraz i zwraca jeden wynik AGQ. To jak ocena całego budynku (nie każdej cegły osobno). Repozytorium może być małe (10 plików) lub ogromne (17 000+ plików) — QSE analizuje oba, choć wyniki małych projektów są mniej wiarygodne statystycznie.

## Szczegółowy opis

### Repozytorium jako jednostka oceny

Jednym ze "kanonicznych niezmienników" QSE jest zasada: **AGQ mierzy architekturę całego repozytorium, nie poszczególnych plików**. To jest fundamentalna różnica z narzędziami jak SonarQube (per plik).

```
qse agq /ścieżka/do/repo → AGQ: 0.714
```

Jeden wynik, jeden projekt, jeden punkt w czasie.

### Typy repozytoriów

QSE rozróżnia kilka typów repozytoriów, które mają różne właściwości metryczne:

| Typ | Opis | Przykłady | Specyfika |
|---|---|---|---|
| **Biblioteka utility** | Zestaw niezależnych narzędzi | google/guava, attrs | Niskie CD strukturalnie — CD=0.000 u guava |
| **Framework** | Architektura dostarczana innym | spring-boot, fastapi | Wysoka stabilność z powodów inżynieryjnych |
| **Aplikacja biznesowa** | Logika domenowa | dddsample, saleor | Najlepsza korelacja z panelem |
| **Monorepo** | Wiele podprojektów w jednym repo | home-assistant | Może sztucznie zawyżać metryki |
| **Platforma** | Duży system platformowy | kubernetes, airflow | Flat z uzasadnienia domenowego |

### Rozmiar repozytorium a wiarygodność metryk

Małe repozytoria (< 10 węzłów) mają problemy ze statystyką:
- Louvain może nie wykryć społeczności → Modularity=0.5 (wartość domyślna)
- Jeden cykl wpływa nieproporcjonalnie na Acyclicity
- Brak różnorodności pakietów → Stability=0 lub 1 skrajnie

QSE dokumentuje to: projekty < 10 węzłów dostają Modularity=0.5 zamiast obliczonego Q — sygnał niskiej wiarygodności.

Przykłady z benchmarku:

| Repo | Nodes | AGQ | Uwagi |
|---|---|---|---|
| attrs | 10 | 1.000 | Mały, idealny, ale małe n |
| spring-cloud-microservice | ~30 | 0.825 | Najwyższe AGQ w GT Java — małe microservices |
| home-assistant | 17595 | 0.581 | Ogromny, płaski |
| quarkus | 17596 | 0.647 | Ogromny, Java enterprise |

### Dane benchmarkowe (558 repozytoriów, kwiecień 2026)

| Język | n | AGQ mean | AGQ std |
|---|---|---|---|
| Python | 351 | 0.748 | 0.139 |
| Java | 147 | 0.735 | 0.164 |
| Go | 30 | 0.783 | 0.076 |
| TypeScript | 30 | 0.883 | 0.099 |

Różnice między językami są **strukturalne**, nie przypadkowe:
- Go nie ma cykli (ekosystem wymusza) → wyższe Acyclicity
- Java naturalnie ma więcej cykli (71% z cyklami) → niższe AGQ
- TypeScript małe projekty → zawyżone statystycznie

### AGQ-z: pozycja na tle języka

Ponieważ surowe AGQ nie jest porównywalne między językami, QSE oferuje **AGQ-z** = Z-score względem rozkładu dla danego języka:

```
AGQ-z = (AGQ − mean_język) / std_język
```

Wartości referencyjne:
- Go: mean=0.815, std=0.062
- Python: mean=0.753, std=0.062  
- Java: mean=0.627, std=0.096

Przykład: `kubernetes` AGQ=0.655 (absolutnie nie dramatyczne) ale AGQ-z=−2.58 (bottom 0.5% dla Go) — bo inne projekty Go są znacznie lepsze strukturalnie.

## Definicja formalna

Repozytorium \(R\) w sensie QSE to:

\[R = (P, L, T)\]

Gdzie:
- \(P\) = ścieżka do kodu źródłowego
- \(L \in \{\text{Python, Java, Go, TypeScript, ...}\}\) = język (wykrywany automatycznie)
- \(T\) = punkt w czasie (snapshot)

AGQ repozytorium:

\[\text{AGQ}(R) = \sum_{i} w_i \cdot m_i(G(R))\]

Gdzie \(G(R)\) = [[Dependency Graph]] zbudowany z kodu \(R\), \(m_i\) = składowe metryki, \(w_i\) = wagi zależne od języka.

## Zobacz też

- [[Module]] — pliki w repozytorium
- [[Package]] — grupy plików
- [[Dependency Graph]] — struktura grafu repozytorium
- [[Experiment]] — jak repozytorium jest używane w badaniach
- [[Expert Panel]] — ocena repozytorium przez ekspertów
