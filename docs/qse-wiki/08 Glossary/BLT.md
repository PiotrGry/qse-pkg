---
type: glossary
language: pl
---

# BLT — Bug Lead Time

## Prostymi słowami

BLT to czas od momentu, gdy błąd pojawia się w kodzie, do momentu, gdy zostaje naprawiony i wdrożony. Wyobraź sobie fabrykę: BLT to czas od powstania wadliwego produktu do jego naprawy na linii produkcyjnej. Im gorsza architektura, tym trudniej znaleźć i naprawić błąd — BLT rośnie.

## Szczegółowy opis

**Bug Lead Time (BLT)** to metryka procesowa opisująca cykl życia błędu w projekcie oprogramowania. Mierzona jest jako różnica czasu między:
1. Momentem wprowadzenia błędu do kodu (commit introducing the bug)
2. Momentem zamknięcia zgłoszenia lub wdrożenia naprawki (fix commit / issue closed)

BLT pojawia się w kontekście QSE jako **zmienna zależna** w walidacji hipotezy H1: jeżeli AGQ mierzy rzeczywistą jakość architektoniczną, powinien korelować z metrykami maintainability, do których zalicza się BLT.

### Dlaczego BLT jest trudne do zmierzenia

- Wymaga mapowania commitów naprawczych (bugfix commits) na zgłoszenia błędów (issues/PRs)
- Historia git musi być wystarczająco długa (co najmniej 1-2 lata)
- Identyfikacja commitów wprowadzających błąd wymaga `git blame` lub narzędzi jak `SZZ algorithm`
- W benchmarku iter6 (n=558): dane BLT dostępne tylko dla **391 repo** (z 558)

### Metryki pochodne używane w QSE

| Metryka | Opis |
|---|---|
| `bugfix_ratio` | Odsetek commitów oznaczonych jako bugfix |
| `mean_files_per_fix` | Średnia liczba plików zmienianych przy jednej naprawce |
| `pct_cross_package_fixes` | % naprawek wymagających zmian w wielu pakietach |
| `median_close_time_days` | Mediana czasu od zgłoszenia do zamknięcia (dni) |
| `blast_radius` | Liczba pakietów/modułów dotkniętych jedną zmianą |

### Wyniki empiryczne QSE vs BLT

Z benchmarku OSS-30 (n=29 z danymi BLT):

| Para | Spearman | p | Siła |
|---|---:|---:|---|
| AGQ vs bugfix_ratio | -0.196 | 0.308 | ns |
| AGQ vs mean_files_per_fix | -0.225 | 0.280 | ns |
| Stability vs pct_cross_package_fixes | +0.483 | 0.015 | ** |
| Cohesion vs mean_files_per_fix | -0.405 | 0.045 | * |

**Wniosek:** Bezpośrednia korelacja AGQ z BLT jest słaba na małej próbie. Jednak komponenty (zwłaszcza S i C) wykazują istotne korelacje z miarami pokrewnymi (blast radius, files per fix). Wymagana większa próba.

### Blast Radius jako substytut BLT

**Blast radius** (promień rażenia zmiany) to alternatywna miara mierzalna bez mapowania issue→commit:
- Dla każdego commitu: ile plików/pakietów zostało zmienionych?
- Hipoteza: zła architektura → większy blast radius (zmiana jednego modułu wymaga zmian w wielu innych)
- Wynik: T6 PASS — |r_s(AGQ, pct_cross_pkg)| = 0.3132 vs |r_s(AGQ, bugfix_ratio)| = 0.1961

## Definicja formalna

$$\text{BLT} = t_{\text{fix}} - t_{\text{intro}}$$

gdzie $t_{\text{intro}}$ to czas introdukcji błędu (commit introducing bug) a $t_{\text{fix}}$ to czas naprawienia.

W praktyce QSE: `median_close_time_days` = mediana (data zamknięcia issue − data otwarcia issue) per repozytorium, obliczona na danych z GitHub API.

**Hipoteza H1:** $r(\text{AGQ}, \text{BLT}) > r(\text{SonarQube Maintainability}, \text{BLT})$. Status: badana, brak wystarczającej próby.

## Zobacz też

- [[AGQ|AGQ]] — główna metryka
- [[07 Benchmarks/Benchmark 558|Benchmark 558]] — dane benchmarkowe z BLT
- [[07 Benchmarks/Java GT Dataset|Java GT Dataset]] — walidacja
- [[11 Research/Research Thesis|Teza badawcza]] — hipotezy H1-H5
- [[Partial Spearman|Partial Spearman]] — metoda korelacji używana w analizie
