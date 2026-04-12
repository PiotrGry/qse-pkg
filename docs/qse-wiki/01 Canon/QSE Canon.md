---
type: canon
language: pl
---

# QSE Canon — kanoniczny opis projektu

## Prostymi słowami

QSE to narzędzie do mierzenia jakości architektury oprogramowania — nie jakości kodu. Mierzy strukturę systemu jako całości: czy moduły są od siebie oddzielone, czy nie ma pętli zależności, czy system ma wyraźne warstwy. To nie jest linter, nie jest SonarQube i nie jest narzędziem do code review.

---

## Szczegółowy opis

### Czym QSE JEST

**QSE (Quality Score Engine)** to otwarte narzędzie do automatycznego pomiaru jakości architektonicznej oprogramowania. Działa na podstawie [[Dependency Graph|grafu zależności]] między modułami i oblicza kompozytową metrykę **AGQ** (*Architecture Graph Quality*).

QSE:
- **Mierzy architekturę systemu** — relacje między modułami, nie treść plików
- **Produkuje interpretowalny wynik** — każda składowa ma jednoznaczne znaczenie architektoniczne
- **Działa w czasie poniżej 1 sekundy** — możliwy w pre-commit hooku i CI/CD
- **Jest deterministyczny** — ten sam kod zawsze daje ten sam wynik
- **Jest niezależny od runtime** — nie uruchamia kodu, nie wymaga zależności projektu
- **Jest empirycznie zwalidowany** — Java GT n=59, MW p=0.000221, AUC=0.767

QSE jest **komplementarny** wobec SonarQube — mierzą różne wymiary jakości i oba są potrzebne jednocześnie (brak korelacji empirycznej, n=78, p>0.10).

### Czym QSE NIE JEST

| Błędne przekonanie | Rzeczywistość |
|---|---|
| „QSE mierzy jakość kodu" | QSE mierzy jakość architektury, nie kodu. AGQ może być wysokie przy złym kodzie i vice versa. |
| „QSE zastępuje SonarQube" | Oba mierzą inne wymiary. Brak korelacji to dowód komplementarności, nie konkurencji. |
| „QSE to linter" | Linter patrzy na linie kodu. QSE patrzy na graf zależności między modułami. |
| „QSE przewiduje defekty" | AGQ jest diagnostyczny, nie predykcyjny. r²≈3–6% wariancji zmiennych procesowych. |
| „Niskie AGQ = projekt jest zły" | Niskie AGQ to sygnał ostrzegawczy, nie wyrok. Kubernetes ma AGQ-z = −2.58 i działa doskonale. |
| „Wynik AGQ można porównywać między językami" | Nie bez AGQ-z. Go ma strukturalnie wyższe AGQ z przyczyn językowych, nie jakościowych. |

Szczegóły: [[What QSE Is Not]]

### Definicja formalna AGQ

AGQ (*Architecture Graph Quality*) to kompozytowa metryka jakości architektonicznej, obliczana jako ważona suma znormalizowanych [0,1] składowych grafowych:

```
AGQ_v3c (Java) = 0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD

AGQ_v3c (Python) = 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score
```

Gdzie każda składowa ∈ [0, 1] i **1 oznacza najlepszą możliwą wartość**.

Szczegóły wzorów: [[AGQ Formulas]]

### Co mierzy każda składowa

| Składowa | Symbol | Co mierzy | Algorytm |
|---|---|---|---|
| Modularność | M | Stopień izolacji grup modułów | Louvain (Newman's Q) |
| Brak cykli | A | Brak cyklicznych zależności | Tarjan SCC |
| Warstwowość | S | Wyraźna hierarchia jądro/obrzeże | Wariancja instability |
| Spójność | C | Jednorodność klas (LCOM4) | Graf metodowy |
| Gęstość sprzężeń | CD | Rzadkość grafu zależności | fan-out / możliwe krawędzie |
| flat_score | f | Hierarchia namespace (Python) | Głębokość NS ≤ 2 |

### Ograniczenia kanoniczne

1. **Language bias**: Go ma strukturalnie cohesion=1.0 (brak hierarchii klas), Java ma strukturalnie niższe cohesion. Nie porównuj surowego AGQ między językami — używaj AGQ-z.
2. **Małe projekty**: AGQ < 50 węzłów jest zawyżone. Brak cykli w 5-plikowym projekcie jest trywialny.
3. **Kalibracja tylko na OSS-Python**: Wagi empiryczne (acyclicity=0.730) zostały wyznaczone na open-source Python. Dla projektów Java/Go/komercyjnych traktuj jako wstępne.
4. **AGQ jest diagnostyczny, nie predykcyjny**: r²≈3–6% wariancji zmiennych procesowych. To realna korelacja, ale nie determinizm.

### Niezmienniki — co NIGDY się nie zmieni

- AGQ v1 nigdy nie jest modyfikowany (historyczna referencja)
- Formuły per-język nie mogą być stosowane między językami
- [[Ground Truth]] pochodzi od panelu ekspertów, nie od metryki BLT
- Zmiany do formuły muszą przetrwać test falsyfikacji
- Brak modeli nieliniowych w AGQ Core
- Brak brute-force optymalizacji wag

Szczegóły: [[Invariants]]

---

## Definicja formalna — pozycja projektu

QSE jest **narzędziem diagnostycznym** do pomiaru jakości architektonicznej oprogramowania w kategorii *static architectural analysis*. Operuje na grafie zależności wewnętrznych modułów projektu (DAG lub skierowany graf z cyklami) i oblicza kompozytową metrykę AGQ.

**Stan walidacji (kwiecień 2026):**
- Java: n=59, MW p=0.000221, Spearman ρ=0.380, AUC-ROC=0.767 → **wysoka istotność statystyczna**
- Jolak cross-validation: 4/5 wyników potwierdzonych
- Brak walidacji na projektach przemysłowych (open-source only)
- Predyktor: nie istnieje, planowany badawczo

---

## Zobacz też
[[What QSE Is Not]] · [[Architecture]] · [[Ground Truth]] · [[Invariants]] · [[AGQ Formulas]] · [[What is QSE in Simple Words]]
