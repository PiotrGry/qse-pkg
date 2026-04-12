---
type: research
language: pl
---

# Kierunki dalszych badań

## Prostymi słowami

QSE jest na etapie TRL 3 — potwierdzono empirycznie, że metryka działa. Ale wciąż zostało wiele do zrobienia: lepsze zrozumienie danych, rozszerzenie na więcej języków, predykcja problemów zamiast tylko ich pomiaru, i walidacja na prawdziwych projektach przemysłowych.

---

## Status aktualny (kwiecień 2026)

- **TRL 3** — potwierdzono eksperymentalnie (4 eksperymenty, 23 testy, 21 PASS / 2 known limitations)
- Java GT: n=59, MW p=0.000221, AUC=0.767
- Benchmark: 558 repo (Python/Java/Go/TypeScript)
- Jolak cross-validation: 4/5 wniosków potwierdzonych

---

## Kierunek 1 — Semantyka kodu (Code Semantics)

### Problem
AGQ mierzy strukturę grafu importów — kto importuje kogo. Nie rozumie **treści** importu: czy moduł A importuje z modułu B jedną stałą konfiguracyjną czy całą logikę domenową. Dwie sytuacje są strukturalnie identyczne (jedna krawędź w grafie), ale mają zupełnie inną wagę architektoniczną.

### Propozycja
**Semantic Edge Weighting** — ważenie krawędzi grafu na podstawie analizy semantycznej:
- Ile symboli jest importowanych? (1 vs 50)
- Jakie to symbole? (stałe, typy, funkcje, klasy)
- Jak często są używane?

Technicznie: rozszerzenie skanera tree-sitter o analizę `from module import X, Y, Z` zamiast tylko `from module import`.

### Potencjalny wpływ
- Lepsze różnicowanie „prawdziwych" vs „przypadkowych" zależności
- Bardziej precyzyjna Modularity i Coupling Density
- Zmniejszenie false positives w wykrywaniu naruszeń constraints

### Stan
Koncepcja badawcza. Wymaga: (1) rozszerzenia skanera Rust, (2) nowego benchmarku z ground truth semantycznym.

---

## Kierunek 2 — Category-Aware Normalization

### Problem
Biblioteka narzędziowa (np. Guava, commons-lang) z płaską strukturą pakietów może mieć niskie AGQ nie dlatego, że jest słabo zaprojektowana, ale dlatego, że jej natura architektoniczna różni się od aplikacji domenowej. Porównywanie ich surowym AGQ jest niesprawiedliwe — jak porównywanie wzrostu niemowlęcia z dorosłym.

### Empiryczny dowód
Z benchmarku GT Java (znane problemy):
- Guava (n=1831 węzłów, AGQ=0.657): biblioteka utility, płaska struktura → niskie CD mimo dobrego projektu
- commons-lang (AGQ=0.537): podobny problem
- Mimo że są to dobrze utrzymane, renomowane projekty

### Propozycja
**Normalizacja względem kategorii projektu:**
1. Automatyczna klasyfikacja projektu (Application / Library / Tool / Domain-Rich / CRUD)
2. Osobne rozkłady AGQ per kategoria
3. AGQ-z per kategoria (zamiast AGQ-z per język)
4. Benchmark zestawów: co jest P50 dla Library? Co dla Domain-Rich?

### Dane potrzebne
- Zbiór projektów z etykietami kategorii (ręcznie lub automatycznie)
- Benchmark ≥200 repo per kategoria per język (WP1 grantu FENG)

### Stan
Zidentyfikowany problem. Planowany w WP3 (walidacja per architektura). Potrzeba: HPC + większy benchmark.

---

## Kierunek 3 — Cross-Language Unification

### Problem
Formuła AGQ v3c Java i Python są różne:
- Java: `0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD`
- Python: `0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score`

Oznacza to, że AGQ nie jest bezpośrednio porównywalny między językami. Projekt Java z AGQ=0.70 i projekt Python z AGQ=0.70 mogą mieć zupełnie różne charakterystyki.

### Propozycja
**Ujednolicona formuła cross-language:**
1. Zbadać, jakie komponenty mają podobne rozkłady w Pythonie i Javie → Acyclicity jest podobna, Stability się różni
2. Znaleźć transformację lub normalizację per-język, która pozwala na porównanie
3. Ustalić wspólny AGQ-z (z-score) calibrowany na połączonym benchmarku wszystkich języków
4. Dodać Go i TypeScript jako pełnoprawne języki (nie tylko Python/Java)

### Blokery
- Go: 30 repo w benchmarku — za mała próba do kalibracji
- TypeScript: problem z parserem (73% repo ma nodes=0)
- Python problem z Modularity (odwrócony kierunek — trwa dochodzenie)

### Stan
Aktywne badania. Wymaga: naprawy parsera TypeScript, rozszerzenia benchmarku Go, rozwiązania Python Modularity anomalii.

---

## Kierunek 4 — Warstwa Predictor (ML)

### Koncepcja
AGQ mierzy stan architektury **w danym momencie** — jest miarą retrospektywną. Warstwa Predictor to planowana warstwa ML, która łączy AGQ z danymi temporalnymi i procesowymi (historia git, częstotliwość zmian, autorzy, czas MTTR) i próbuje **przewidzieć przyszłe problemy**.

### Analogia
AGQ = zdjęcie RTG (co jest teraz). Predictor = historia medyczna + obecny stan (co się może stać).

```
Dane wejściowe Predictor:
  AGQ_t       (historia AGQ w czasie)
  Δ AGQ       (trend — rośnie czy spada?)
  hotspot     (gdzie najczęściej zmiany?)
  churn_gini  (równomierność zmian)
  team_size   (liczba aktywnych autorów)
  MTTR        (mediana czasu naprawienia bugu)

Cel:
  P(degradacja w ciągu 6 miesięcy) > threshold → alert
```

### Dane potrzebne
- Historia AGQ per repozytorium per commit (wymaga: HPC + 100+ repo × historia git)
- Benchmark longitudinalny — co najmniej 2 lata historii na repo

### Stan
Koncepcja. Wymaga WP1 (benchmark) jako infrastruktury. Planowany jako WP4 w grancie FENG.

**Ważne zastrzeżenie:** Predictor to niezależna warstwa od AGQ Core. AGQ Core pozostaje deterministyczny i bez ML. Predictor to opcjonalny dodatek.

---

## Kierunek 5 — Rozszerzenie GT i walidacja przemysłowa

### Problemy z obecnym GT
- Java GT n=59 — dobry start, ale za mały do silnych wniosków per kategoria
- Python GT n=30 — zbyt mała próba, problem kierunku
- Cały GT oparty na OSS (GitHub) — brak closed-source, przemysłowego
- Panel ekspertów jest symulowany — brak inter-rater reliability z prawdziwymi ekspertami

### Propozycje

**5a. Rozszerzenie Java GT do n≥100:**
- Dodanie 41+ repo (focus: enterprise Java, nie tylko DDD samples)
- Włącznie middleware i utility libraries z category-aware normalization

**5b. Rozszerzenie Python GT do n≥50:**
- Rozwiązanie problemu kierunku (dlaczego Modularity zachowuje się odwrotnie?)
- Włącznie projektów enterprise Python (Django apps, not just libs)

**5c. Walidacja przemysłowa (WP5):**
- Partnerstwo z firmami gotowymi udostępnić closed-source code
- Prawdziwy panel ekspertów (co najmniej 3 niezależnych architektów per repo)
- Kalibracja na danych wewnętrznych

### Stan
P0 (Java GT) i P1 (Python GT) to priorytety po grancie FENG.

---

## Kierunek 6 — Benchmark Longitudinalny (WP1 FENG)

### Cel
Zamiast single-snapshot AGQ per repo — AGQ per commit per repo dla historii 2+ lat. Pozwoli:
- Trenować Predictor
- Walidować, czy degradacja AGQ koreluje z incydentami (bugi, MTTR)
- Category-aware normalization oparta na dużej próbie

### Skala
- Plan WP1: 6 architektur × 15+ repo = 90–100 repo × historia 2 lat
- HPC (High Performance Computing): embarrassingly parallel
- Rust scanner: 7–46× szybszy od Python → konieczny dla skali

### Oczekiwany wynik
Największy publicznie dostępny longitudinalny benchmark AGQ.

---

## Plan priorytetów (roadmap)

| Priorytet | Kierunek | Warunek wstępny | Timeline |
|---|---|---|---|
| P0 | Rozszerzenie Python GT do n≥50 | — | Teraz |
| P1 | Naprawa TypeScript parser | — | Teraz |
| P2 | Category classification (heurystyczna) | — | Teraz |
| P3 | Grant FENG — WP1 Benchmark | Grant przyznany | 2026 Q3+ |
| P4 | Cross-language unification | Większy benchmark | WP1+ |
| P5 | Semantic edge weighting | Rust scanner extension | WP2+ |
| P6 | Predictor layer (ML) | Benchmark longitudinalny | WP4+ |
| P7 | Walidacja przemysłowa | Partnerzy | WP5+ |

---

## Definicja formalna — TRL progression

| TRL | Opis | Stan |
|---|---|---|
| TRL 1–2 | Koncepcja | ✅ Gotowe |
| TRL 3 | Proof of concept | ✅ Potwierdzone (2026-04) |
| TRL 4 | Walidacja w laboratorium | ⏳ GT n=59, potrzeba n=200+ |
| TRL 5 | Walidacja w środowisku | ⏳ Wymaga WP1 |
| TRL 6–7 | Demonstracja systemu | ⏳ Cel grantu FENG |
| TRL 8 | Kwalifikacja systemu | — |
| TRL 9 | Produkcja | — |

Cel grantu FENG SMART B+R: TRL 3 → TRL 7–8.

---

## Zobacz też

- [[11 Research/Research Thesis|Teza badawcza]] — pytania badawcze
- [[11 Research/Literature Review|Przegląd literatury]] — stan wiedzy
- [[11 Research/Limitations|Ograniczenia]] — co blokuje
- [[07 Benchmarks/Benchmark Index|Benchmarki]] — aktualne dane
- [[05 Experiments/Experiments Index|Eksperymenty]] — co już zrobiono
