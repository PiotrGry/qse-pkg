# QSE — Quality Score Engine
## Wniosek grantowy — opis projektu
### Wersja do EU / NCBiR / NCN

---

## 1. Wprowadzenie — problem który rozwiązujemy

### 1.1 Era AI i nowe zagrożenia dla jakości oprogramowania

Sztuczna inteligencja rewolucjonizuje tworzenie oprogramowania. Narzędzia takie jak GitHub Copilot, Cursor czy Claude Code generują dziś ponad 46% kodu w plikach gdzie są aktywnie używane (GitHub, 2023)¹. Programista opisuje w języku naturalnym co chce osiągnąć, a AI pisze kod w ciągu sekund.

Problem polega na tym, że **AI optymalizuje pod kątem "działa teraz", nie "będzie działać za rok"**. Kod wygenerowany przez AI przechodzi testy jednostkowe, nie zawiera oczywistych błędów, ale systematycznie niszczy wewnętrzną strukturę systemu — jego architekturę.

Wyobraźmy sobie firmę budującą oprogramowanie bankowe. Po roku używania AI do generowania kodu:

- Moduł odpowiedzialny za płatności zaczął importować dane z modułu użytkowników (których nie powinien dotykać)
- W systemie pojawiły się cykliczne zależności — moduł A potrzebuje modułu B, moduł B potrzebuje modułu A — co sprawia że zmiana jednego wymaga zmiany drugiego
- Klasy stały się "god objects" — jeden obiekt robi 20 różnych rzeczy zamiast jednej

Żadne powszechnie stosowane narzędzie tego nie wykrywa. SonarQube (lider rynku) sprawdza jakość kodu na poziomie pliku — błędy, czytelność, luki bezpieczeństwa, duplikaty. **Nie mierzy struktury systemu jako całości — modularity, acyclicity, stability ani cohesion.**

### 1.2 Czym jest "dobra architektura" — dla niespecjalisty

Wyobraźmy sobie budynek. Dobry budynek ma:

- **Niezależne pomieszczenia** — łazienka nie musi "wiedzieć" co dzieje się w kuchni
- **Jasne wejścia i wyjścia** — drzwi są tam gdzie powinny być, nie ma dziur w ścianach
- **Hierarchię** — piwnica nie opiera się na dachu

W oprogramowaniu przekłada się to na cztery mierzalne właściwości:

- **Niezależne moduły** (modularity) — zmiana w module płatności nie powinna wymuszać zmian w module raportowania
- **Brak cykli** (acyclicity) — moduł A może zależeć od B, ale B nie może zależeć od A
- **Warstwy** (stability) — "jądro" systemu jest stabilne, zmiany zachodzą na "obrzeżach"
- **Skupienie** (cohesion) — każda klasa robi jedną rzecz i robi ją dobrze

---

¹ *"GitHub Copilot for Business is now available"*, GitHub Blog, 14 lutego 2023. https://github.blog/news-insights/product-news/github-copilot-for-business-is-now-available/

---

## 2. QSE — nasze rozwiązanie

### 2.1 Co to jest QSE

**QSE (Quality Score Engine)** to system który automatycznie mierzy jakość architektoniczną oprogramowania, klasyfikuje jej wzorzec oraz egzekwuje reguły architektoniczne w procesie wytwarzania oprogramowania (CI/CD). Działa dla **Python, Java i Go** z jednego interfejsu.

System QSE jest zbudowany w trzech konceptualnie odrębnych warstwach:

**AGQ Core** stanowi fundament: cztery kalibrowane metryki grafowe (modularity, acyclicity, stability, cohesion) agregowane do jednego score'u z empirycznie wyznaczonymi wagami. Warstwa zaprojektowana pod kątem interpretowalności i stabilności — każda składowa ma jednoznaczne znaczenie architektoniczne, wynik końcowy można wyjaśnić deweloperowi w terminach grafu zależności. AGQ Core jest deterministyczny, szybki (mediana <1s) i niezależny od warstw wyższych.

**AGQ Enhanced** rozszerza Core o kontekst i klasyfikację: normalizację per-język (AGQ-z, AGQ-adj), klasyfikację wzorca architektonicznego (Fingerprint), ocenę powagi cykli (CycleSeverity) i szacunek ryzyka procesowego (ChurnRisk). Warstwa ta dodaje wartość diagnostyczną bez modyfikowania AGQ Core — jej wyjścia są pochodnymi Core'u, nie osobnym modelem.

**Predictor** (warstwa planowana badawczo) jest konceptualnie odrębny od obu powyższych. Jego zadaniem nie jest obliczanie score'u architektonicznego, lecz szacowanie prawdopodobieństwa przyszłych zdarzeń procesowych. Przyjmuje jako wejście cechy z AGQ Core i Enhanced, uzupełnione o cechy temporalne, procesowe i boundary features. Wymaga osobnego datasetu z etykietami procesowymi, osobnego pipeline'u walidacji i osobnych metryk jakości — niezależnych od metryk AGQ.

```
┌─────────────────────────────────────────────────────────┐
│  WARSTWA 3 (planowana): Predictor                       │
│  Model predykcji ryzyka utrzymaniowego                  │
│  Wejście: AGQ + cechy temporalne/procesowe/boundary     │
├─────────────────────────────────────────────────────────┤
│  WARSTWA 2: AGQ Enhanced + Policy-as-a-Service          │
│  AGQ-z, Fingerprint, CycleSeverity, ChurnRisk, AGQ-adj  │
│  Quality Gate, qse discover                             │
├─────────────────────────────────────────────────────────┤
│  WARSTWA 1: AGQ Core (Scanner + Metrics)                │
│  Modularity, Acyclicity, Stability, Cohesion            │
│  Rust tree-sitter — Python, Java, Go — 7-46× szybszy    │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Jak działa — krok po kroku

**Krok 1: Skanowanie kodu**

```bash
$ qse agq /ścieżka/do/projektu
```

System wykrywa język automatycznie (zlicza pliki `.py/.java/.go`) i używa skanera Rust opartego na tree-sitter — 7–46× szybszego niż tradycyjne podejście oparte na interpreterze języka. Obsługuje wszystkie trzy języki z jednego silnika.

**Krok 2: Graf wewnętrznych zależności**

QSE buduje graf gdzie węzły = moduły źródłowe, krawędzie = importy. Kluczowe: filtrujemy węzły zewnętrzne (stdlib, biblioteki third-party) — cykl przez `os` czy `java.util` nie jest architektonicznym problemem. Liczymy tylko zależności między własnymi modułami projektu.

**Krok 3: Cztery metryki AGQ**

(szczegóły w sekcji 3)

**Krok 4: Pięć metryk Enhanced**

Na podstawie czterech bazowych QSE oblicza pięć dodatkowych wymiarów:

| Metryka | Co daje | Przykład |
|---|---|---|
| **AGQ-z** | Percentyl w danym języku — usuwa language bias | jackson: 5.3%ile Java |
| **Fingerprint** | Wzorzec architektoniczny (klasyfikacja na podstawie acyclicity, cohesion i stability) | [CLEAN], [LAYERED], [FLAT], [MODERATE], [LOW_COHESION], [TANGLED], [CYCLIC] |
| **CycleSeverity** | Powaga cykli: NONE / LOW / MEDIUM / HIGH / CRITICAL | HIGH = 15% klas w pętli |
| **ChurnRisk** | Ryzyko nierównego rozkładu zmian | CRITICAL → pilna refaktoryzacja |
| **AGQ-adj** | Score skorygowany o rozmiar projektu | małe i duże repo porównywalne |

**Krok 5: Wynik z wyjaśnieniem**

```
# Zamiast suchego "AGQ=0.46 FAIL":
AGQ GATE PASS  agq=0.4618  M=0.57 A=0.85 St=0.26 Co=0.16  lang=Java
  [TANGLED]  z=-1.61 (5.3%ile Java)  cycles=HIGH (15% klas w cyklach)
  → Projekt jest w dolnych 5% repozytoriów Java
  → 15% klas uwięzionych w cyklach zależności — HIGH priority fix
  → Wzorzec TANGLED: niska spójność + cykle = architektoniczny dług

# Versus dobry projekt:
AGQ GATE PASS  agq=0.8760  lang=Go
  [CLEAN]  z=+0.95 (82.8%ile Go)  cycles=NONE
  → Strukturalnie czysty: zero cykli, wysoka spójność, wyraźne warstwy
```

**Krok 6: Policy-as-a-Service — automatyczne reguły**

```bash
$ qse discover /ścieżka/do/repo --output-constraints .qse/arch.json
$ qse agq . --constraints .qse/arch.json
# Każdy PR sprawdzany czy respektuje granice architektoniczne
```

**Krok 7: Integracja z CI/CD**

QSE zwraca wynik w poniżej 1 sekundy dla typowych projektów, co umożliwia integrację jako pre-commit hook lub krok w pipeline CI/CD — bez spowalniania procesu wytwarzania.

---

## 3. Metryki AGQ — wyjaśnienie

### 3.1 Modularity — "czy moduły są naprawdę niezależne?"

**Co mierzy**

Czy system dzieli się na grupy modułów które intensywnie komunikują się wewnętrznie, ale rzadko z innymi grupami.

**Analogia**

Wyobraź sobie miasto. Dobra dzielnica mieszkalna ma dużo wewnętrznych połączeń (ulice, chodniki między budynkami), ale tylko kilka głównych dróg łączących ją z innymi dzielnicami. Jeśli każda ulica w mieście łączy się z każdą inną — to chaos, nie dzielnice.

**Jak obliczamy**

Używamy algorytmu Louvain — ten sam który stosuje się do wykrywania "społeczności" w sieciach społecznych. Obliczamy stosunek połączeń wewnątrz grup do połączeń między grupami (Newman's Q).

- **Wynik 0:** Wszystkie moduły łączą się ze wszystkimi — brak struktury ("big ball of mud")
- **Wynik 1:** Moduły tworzą wyraźne, izolowane grupy — idealna modularność

Normalizacja: maksymalne Q w zbiorze 240 repo wyniosło 0.80. Stosujemy: `max(0, Q) / 0.75`.

---

### 3.2 Acyclicity — "czy nie ma błędnych pętli zależności?"

**Co mierzy**

Czy istnieją cykliczne zależności — sytuacje gdzie A zależy od B, B od C, C od A.

**Analogia**

Wyobraź sobie firmę gdzie dział kadr czeka na decyzję finansową, finanse czekają na plan HR, a HR czeka na decyzję finansową. Nikt nic nie zrobi. W kodzie — zmiana w A wymusza zmianę w B, która wymusza zmianę w C, która wymusza zmianę w A.

**Jak obliczamy**

Algorytm Tarjana (Strongly Connected Components) z teorii grafów. Szukamy największego "splotu" w grafie zależności wewnętrznych modułów.

- **Wynik 0:** Cały system jest jedną wielką pętlą
- **Wynik 1:** Brak jakichkolwiek cykli — każda zależność idzie "w dół"

**Znaczenie empiryczne**

Metryka ta uzyskała najwyższą wagę w kalibracji empirycznej (szczegóły w sekcji 4.1). Jest to zgodne z niezależnymi badaniami: Gnoyke et al. (JSS 2024) wykazali, że zależności cykliczne najsilniej korelują z defektami spośród wszystkich architektonicznych code smells.

---

### 3.3 Stability — "czy architektura ma wyraźne warstwy?"

**Co mierzy**

Stopień w jakim moduły systemu pełnią wyraźnie różne role architektoniczne — jedne są "jądrem" (stabilnym), inne są "obrzeżem" (zmieniającym się).

**Analogia**

Wyobraź sobie armię. Generałowie są stabilni — wielu oficerów raportuje do nich, oni sami raportują do niewielu. Żołnierze są niestabilni — raportują do oficerów, ale nikt do nich nie raportuje. Dobrze zorganizowana armia ma wyraźną hierarchię. Kiepska armia — wszyscy raportują do wszystkich, żaden stopień nie ma jasnej roli.

**Jak obliczamy**

Dla każdego pakietu obliczamy I (Instability) = `wychodzące_importy / (wychodzące + przychodzące)`. Pakiet "jądra" ma I≈0, pakiet "obrzeża" ma I≈1. Mierzymy wariancję I między pakietami — im wyższa, tym wyraźniejsza hierarchia warstw.

- **Wynik 0:** Wszystkie pakiety mają podobną instability — brak warstw
- **Wynik 1:** Wyraźna separacja jądra od obrzeża

**Uwaga metodologiczna**

Oryginalny wzór Martina (Distance from Main Sequence, 1994) wymaga danych o abstrakcji klas, które w praktyce są niedostępne (w Pythonie prawie zawsze A=0). Nasz wzór oparty na wariancji instability jest empirycznie zwalidowanym zamiennikiem.

---

### 3.4 Cohesion — "czy każda klasa robi jedną rzecz?"

**Co mierzy**

Czy metody w klasie faktycznie współpracują (dzielą dane), czy są przypadkowymi sąsiadami w tym samym pliku.

**Analogia**

Dobra klasa to jak dobry pracownik — ma jedno stanowisko pracy, wszystkie jego narzędzia służą do jednego celu. Zła klasa to "człowiek-orkiestra" — ma biurko, stół operacyjny i stanowisko kierowcy tira jednocześnie.

**Jak obliczamy**

LCOM4 (Lack of Cohesion of Methods v4) — liczymy ile "wysp" tworzą metody klasy jeśli połączymy te które dzielą atrybuty. Klasa z LCOM4=1 to jeden spójny byt. Klasa z LCOM4=5 powinna być podzielona na 5 mniejszych klas.

- **Wynik 0:** Klasy są zbiorami niezwiązanych metod
- **Wynik 1:** Każda klasa jest spójną jednostką

**Language bias**

Go zawsze osiąga cohesion=1.0, Java średnio 0.38. To nie wynik jakości kodu — Go strukturalnie nie ma wielodziedziczenia (interfejsy zamiast hierarchii klas), więc LCOM4=1 zawsze. Java ma złożone hierarchie → niższe cohesion jest normą dla tego języka. Dlatego porównanie cross-language wymaga normalizacji per-język (metryka AGQ-z).

---

### 3.5 QSE_test — "czy testy są dobrej jakości?"

QSE_test jest zaimplementowany i mierzy pięć wymiarów jakości zestawu testów:

**1. Assertion density**
Średnia liczba asercji (sprawdzeń) per test. Test z 0 asercjami niczego nie weryfikuje — wykonuje kod bez sprawdzania wyników.

**2. Test-to-code ratio**
Stosunek linii kodu testowego do linii kodu produkcyjnego. Niska wartość może wskazywać na niewystarczające pokrycie.

**3. Naming quality**
Procent testów z opisową nazwą — np. `test_should_reject_invalid_payment` zamiast `test_1`. Opisowe nazwy stanowią dokumentację i ułatwiają diagnozę błędów.

**4. Isolation score**
Procent testów korzystających z mocków, patchów lub fixtures (izolacja od zewnętrznych systemów — bazy danych, HTTP, filesystem). Testy bez izolacji są niestabilne i wolne.

**5. Coverage potential**
Proxy: procent klas domenowych które mają co najmniej jeden test. Nie wymaga uruchomienia coverage tool.

```
QSE_test = mean(powyższych 5 metryk) ∈ [0, 1]
```

---

## 4. Wyniki eksperymentalne

### 4.0 Benchmark 240 repozytoriów — podsumowanie cross-language

Benchmark architektoniczny cross-language: **240 w pełni sklonowanych repozytoriów** (Python-80, Java-79, Go-81) z pełną historią git.

**Statystyki zbiorcze:**

| Język | n | Średnie AGQ | Cohesion śr. | Acyclicity śr. | % z cyklami |
|---|---|---|---|---|---|
| Go | 81 | **0.815** | **1.000** | **1.000** | **0%** |
| Python | 80 | 0.753 | 0.647 | 0.999 | 4% |
| Java | 79 | **0.627** | **0.379** | 0.973 | **71%** |

**Rozkład wzorców Fingerprint (240 repo):**

| Wzorzec | Total | Python | Java | Go | Interpretacja |
|---|---|---|---|---|---|
| LAYERED | 68 | 57 | 4 | 7 | Warstwowa architektura |
| CLEAN | 51 | 2 | 2 | **47** | Strukturalnie czysty — Go dominuje |
| LOW_COHESION | 44 | 4 | **40** | 0 | Klasy robią za dużo — Java |
| MODERATE | 40 | 12 | 11 | 17 | Bez wyraźnych patologii |
| FLAT | 23 | 5 | 8 | 10 | Brak hierarchii warstw |
| TANGLED | 9 | 0 | **9** | 0 | Cykle + niska spójność — Java |
| CYCLIC | 5 | 0 | **5** | 0 | Cykle bez innych patologii |

**Uwaga interpretacyjna:** Wzorzec FLAT (brak warstw) pojawia się najczęściej u projektów z najniższym AGQ-z w każdym języku (`home-assistant`, `avro`, `kubernetes`). Należy jednak odróżnić FLAT jako defekt architektoniczny od FLAT jako świadomą decyzję projektową — duże projekty platformowe (kubernetes, grafana) mogą mieć płaską strukturę z uzasadnienia domenowego, nie z zaniedbania. AGQ-z pozwala odróżnić te przypadki przez porównanie w obrębie języka i rozmiaru.

**Statystycznie istotne korelacje cross-language (n=234, Spearman):**

| Para | r_s | p-value |
|---|---|---|
| acyclicity vs hotspot_ratio | +0.223 | **0.001** |
| stability vs hotspot_ratio | +0.180 | **0.006** |
| AGQ-adj vs churn_gini | -0.154 | **0.018** |
| AGQ-adj vs hotspot_ratio | +0.236 | **<0.001** |

AGQ skorygowany o rozmiar projektu (AGQ-adj) wykazuje silniejszą korelację z metrykami procesu wytwarzania niż surowe AGQ — usunięcie bias rozmiaru wzmacnia sygnał architektoniczny. Efekty są statystycznie istotne lecz umiarkowane (r²≈3–6%), co wskazuje na ortogonalność metryk architektonicznych i procesowych, a nie na bezpośrednią predykcję.

---

### 4.1 Benchmark Python OSS-80

**Zbiór danych:** 80 repozytoriów Python, pełne klony z pełną historią git.

**Weryfikacja tez:**

| ID | Teza | Wynik | Dowód liczbowy |
|---|---|---|---|
| T1 | AGQ jest deterministyczne | ✅ PASS | max delta = 0.0000000000 na 80 repo |
| T2 | AGQ mierzy wymiar komplementarny do Sonara | ✅ REVISED | AGQ composite vs Sonar/KLOC: brak korelacji (r=-0.11, n.s.); składowe stability↔bugs r=-0.32 (p=0.003), cohesion↔complexity r=-0.28 (p=0.01). n=79 |
| T3 | AGQ wykrywa problemy niewidoczne dla Sonara | ✅ PASS | projekty z Sonar=A i AGQ<0.7 zidentyfikowane w zbiorze |
| T4 | AGQ umożliwia szybki feedback architektoniczny | ✅ PASS | mediana 0.32s — możliwość integracji jako pre-commit hook |
| T5 | AGQ różnicuje jakość architektoniczną | ✅ PASS | spread=0.425, std=0.065; known-good vs known-bad: p<0.001, d=3.22 |
| T6 | AGQ daje wyniki spójne z niezależnymi narzędziami | ✅ NEW | ranking AGQ = ranking Dai et al. architectural integrity (rho=1.0, n=4 Java) |

**Nota do T2 (zaktualizowana, n=79):** Cross-validation z SonarQube v9.9.8 na 79 repo Python. AGQ composite score nie koreluje z żadną znormalizowaną metryką Sonar (smells/KLOC: r=-0.11, n.s.; bugs/KLOC: r=-0.09, n.s.). Jednak dwa składowe AGQ wykazują istotny związek z metrykami Sonar na poziomie per-KLOC: **stability vs bugs/KLOC: r=-0.32, p=0.003** (wyższa stability = mniej bugów) oraz **cohesion vs complexity/KLOC: r=-0.28, p=0.01** (wyższa kohezja = mniejsza złożoność cyklomatyczna). Interpretacja: AGQ i SonarQube mierzą w dużej mierze ortogonalne wymiary, ale dwa składowe AGQ mają mierzalny związek z defektami na poziomie kodu. Confound wielkości repo wyeliminowany (AGQ vs ncloc: r=0.02, n.s. na n=79).

**Nota do T5 (nowa):** Walidacja face validity: 10 repo o uznanej dobrej architekturze (Django, Flask, FastAPI, SQLAlchemy, Pydantic, Click, Rich, Starlette, Celery, Typer) vs 10 repo z najniższym AGQ. Mann-Whitney U=0, **p<0.001, Cohen's d=3.22** (very large effect). 80% known-good = LAYERED fingerprint, 60% known-bad = FLAT/LOW_COHESION. Główny dyskryminator: stability (mean 0.84 vs 0.44). Dane: `known_good_bad_validation.json`.

**Nota do T6 (nowa):** Porównanie z Dai et al. (2026, Scientific Reports) na 4 projektach Apache Java (Ant, JDT, Camel, Hadoop). AGQ ranking identyczny z ich trained GNN architectural integrity ranking (Spearman rho=1.0). AGQ dodatkowo identyfikuje konkretne problemy: god classes (Ant/Hadoop), flat architecture (Camel), cykle (JDT). Dane: `dai_et_al_comparison.json`.

**Nota do T4:** Porównanie prędkości z SonarQube nie jest bezpośrednio miarodajne — narzędzia mierzą różne rzeczy. Istotne jest że QSE zwraca wynik architektoniczny w poniżej 1 sekundy, co umożliwia jego użycie w pre-commit hooku bez spowalniania pracy dewelopera.

**Kalibracja wag (L-BFGS-B, n=74):**

Wagi czterech składowych AGQ zostały wyznaczone empirycznie metodą optymalizacji numerycznej (L-BFGS-B). Jako signal optymalizacji użyto code churn — miarę częstości zmian plików w historii git, będącą pośrednim wskaźnikiem kosztów utrzymania (Nagappan & Ball, ICSE 2005; Faragó et al., SCAM 2015). Model dobiera wagi minimalizując błąd predykcji churn na podstawie AGQ.

Walidacja stabilności modelu: Leave-One-Out Cross-Validation (LOO-CV) — każdy z 74 projektów jest kolejno wyłączany ze zbioru treningowego, model jest rekalibrowany na pozostałych 73, i testowany na wykluczonym projekcie. Niska wartość MSE w LOO-CV oznacza że model nie "nauczył się na pamięć" danych — jest odporny na jednostkowe obserwacje.

| Składowa | Waga empiryczna | Waga równa |
|---|---|---|
| Acyclicity | **0.730** | 0.250 |
| Cohesion | **0.174** | 0.250 |
| Stability | **0.050** | 0.250 |
| Modularity | **0.000** | 0.250 |

Dominacja acyclicity (0.73) jest zgodna z niezależnymi badaniami literaturowymi (Gnoyke et al., JSS 2024). Waga modularity=0 oznacza że modularity nie wnosi niezależnego sygnału predykcyjnego gdy pozostałe trzy metryki są obecne — co może wynikać z korelacji między metrykamił lub z tego że Q Louvaina nie dyskryminuje dobrze w zakresie wartości obserwowanych w tym zbiorze. Należy traktować te wagi jako wstępne, wyznaczone na konkretnym zbiorze danych OSS-Python — kalibracja per-język (Python, Java, Go osobno) stanowi jeden z planowanych kierunków badań.

**Wyniki per repo (wybrane):**

| Repo | AGQ | Modularity | Acyclicity | Stability | Cohesion |
|---|---|---|---|---|---|
| attrs | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| pytest | 0.875 | 0.500 | 1.000 | 1.000 | 1.000 |
| boto3 | 0.869 | 0.778 | 1.000 | 0.952 | 0.746 |
| youtube-dl | 0.857 | 0.681 | 1.000 | 0.862 | 0.884 |
| ... | ... | ... | ... | ... | ... |
| hypothesis | 0.644 | 0.547 | 1.000 | 0.232 | 0.799 |
| home-assistant | 0.575 | 0.512 | 1.000 | 0.078 | 0.711 |

---

### 4.2 Benchmark Java-79

**Zbiór danych:** 79 z 80 repozytoriów Java, pełne klony z pełną historią git.

**Statystyki zbiorcze:**

| Metryka | Wartość |
|---|---|
| Liczba repo | 79 |
| Średnie AGQ | 0.627 |
| Spread | 0.434 |
| Std | 0.096 |
| Min AGQ | 0.471 (jackson-databind, TANGLED) |
| Max AGQ | 0.905 (spotbugs, CLEAN) |
| Repo z cyklami | **56/79 = 71%** |

**Najlepsze i najgorsze:**

| Repo | AGQ | Fingerprint | AGQ-z | Percentyl |
|---|---|---|---|---|
| spotbugs | 0.905 | CLEAN | +2.52 | 99% |
| resteasy | 0.847 | CLEAN | +1.58 | 94% |
| dagger | 0.839 | LAYERED | +1.44 | 93% |
| spring-boot | 0.803 | LAYERED | +1.93 | 97% |
| immutables | 0.784 | LAYERED | +1.72 | 96% |
| ... | ... | ... | ... | ... |
| flyway | 0.498 | CYCLIC | -1.32 | 9% |
| jsoup | 0.478 | TANGLED | -1.54 | 6% |
| jackson-databind | 0.471 | TANGLED | -1.61 | 5% |

---

### 4.3 Benchmark Go-81

**Zbiór danych:** 81 repozytoriów Go, pełne klony.

**Statystyki zbiorcze:**

| Metryka | Wartość |
|---|---|
| Liczba repo | 81 |
| Średnie AGQ | 0.815 |
| Spread | 0.266 |
| Std | 0.062 |
| Min AGQ | 0.655 (kubernetes, FLAT) |
| Max AGQ | 0.920 (staticcheck, CLEAN) |
| Repo z cyklami | **0/81 = 0%** |
| Cohesion = 1.000 | **81/81 = 100%** |

**Najlepsze i najgorsze:**

| Repo | AGQ | Fingerprint | AGQ-z | Percentyl |
|---|---|---|---|---|
| staticcheck | 0.920 | CLEAN | +1.66 | 95% |
| grpc-gateway | 0.920 | CLEAN | +1.65 | 95% |
| ... | ... | ... | ... | ... |
| grafana | 0.678 | FLAT | -2.21 | 1% |
| kubernetes | 0.655 | FLAT | -2.58 | 0.5% |

Wzorzec FLAT dominuje wśród najgorszych Go projektów — nie CYCLIC (cykli nie ma) ani TANGLED (cohesion zawsze=1.0), ale brak hierarchii warstw. kubernetes i grafana to projekty platformowe — ich płaska struktura może częściowo wynikać z decyzji architektonicznych adekwatnych do skali i typów kontrybutorów.

---

### 4.4 Porównanie między językami — language bias

| Wymiar | Python (80) | Java (79) | Go (81) |
|---|---|---|---|
| Średnie AGQ | 0.753 | 0.627 | **0.815** |
| Cohesion śr. | 0.647 | **0.379** | **1.000** |
| Acyclicity śr. | 0.999 | 0.973 | **1.000** |
| % repo z cyklami | 4% | **71%** | **0%** |
| Stability śr. | 0.806 | 0.486 | 0.736 |
| Modularity śr. | 0.533 | **0.637** | 0.531 |
| Dominant pattern | LAYERED | LOW_COHESION | CLEAN |

Różnice między językami nie wynikają z jakości kodu, ale z paradygmatów językowych:

- **Go:** interfejsy zamiast dziedziczenia → LCOM4=1 zawsze → cohesion=1.0; narzędzia ekosystemu aktywnie wymuszają brak cykli
- **Java:** hierarchie klas → cohesion 0.38 średnio; złożone zależności między pakietami
- **Python:** dynamiczny typing → wartości pośrednie; dominant pattern LAYERED

**Implikacja:** Cross-language porównanie AGQ bez normalizacji jest metodologicznie problematyczne. AGQ-z (percentyl w języku) rozwiązuje ten problem — jackson-databind (5.3%ile Java) i kubernetes (0.5%ile Go) obie są "najgorszymi w swojej klasie" mimo różnych wartości bezwzględnych.

---

## 5. Policy-as-a-Service — automatyczne reguły architektoniczne

### 5.1 Koncepcja

Każda organizacja ma zasady architektury zapisane w dokumentacji wewnętrznej. QSE zamienia te zasady w automatycznie egzekwowalne reguły:

```json
{
  "constraints": [
    {
      "type": "forbidden",
      "from": "domain/*",
      "to": "infrastructure/*",
      "rationale": "Domena biznesowa nie może zależeć od infrastruktury"
    },
    {
      "type": "forbidden",
      "from": "payment/*",
      "to": "user/*",
      "rationale": "Konteksty biznesowe muszą być izolowane"
    }
  ]
}
```

Gdy AI (lub człowiek) wygeneruje kod naruszający te reguły:

```
❌ NARUSZENIE ARCHITEKTURY
payment/service.py importuje user/controller.py
Reguła: moduł payment nie może zależeć od user
Dlaczego: Tworzy dwukierunkowe sprzężenie, uniemożliwia niezależny deployment
Sugestia: Użyj zdarzeń domenowych (UserCreatedEvent) lub interfejsu repozytorium
```

### 5.2 Automatyczne odkrywanie reguł (qse discover)

Kluczowa innowacja: reguły mogą generować się **automatycznie z istniejącego kodu** przez analizę grafu zależności algorytmem Louvain. Algorytm wykrywa klastry modułów i na podstawie kierunkowości krawędzi między nimi proponuje reguły zakazane.

**Przykład dla Spring Boot (Java):**

```bash
$ qse discover /path/to/spring-boot --output-constraints .qse/arch.json
```

Wynikowy plik `.qse/arch.json`:

```json
{
  "constraints": [
    {
      "type": "forbidden",
      "from": "org.springframework.boot.loader/*",
      "to": "org.springframework/*",
      "rationale": "classloader nie powinien zależeć od kodu aplikacji"
    },
    {
      "type": "forbidden",
      "from": "org.mockito/*",
      "to": "org.junit/*",
      "rationale": "JUnit zależy od Mockito (13 krawędzi) — relacja jednostronna"
    }
  ]
}
```

Wstępna walidacja na Spring Boot (Java) i Django (Python) pokazuje że generowane reguły są architektonicznie spójne z udokumentowanymi decyzjami projektowymi tych repozytoriów. Pełna walidacja z udziałem ekspertów domenowych stanowi planowany kierunek badań (sekcja 7.1D).

Inżynier przegląda wygenerowane reguły i zatwierdza lub modyfikuje — zamiast pisać konfigurację od zera.

### 5.3 Flow z AI (vibe coding guard)

```
1. Developer pisze prompt do AI
2. AI generuje kod (Copilot/Cursor)
3. Pre-commit hook: qse agq --constraints .qse/architecture.json
4. PASS → commit OK
   FAIL → konkretna wskazówka + sugestia dla AI jak poprawić
5. AI dostaje feedback architektoniczny i regeneruje
```

---

## 6. Odkrycia naukowe

### 6.1 Naprawa metryki Martina

Martin's Distance from Main Sequence (1994) jest powszechnie cytowana ale nie była empirycznie walidowana na dużych zbiorach danych open source. Nasze eksperymenty pokazały że bez danych o abstrakcji (w Pythonie prawie zawsze A=0), wzór degeneruje do odwróconego pomiaru instabilności. Zaproponowaliśmy zamiennik oparty na wariancji instability per pakiet, który poprawnie klasyfikuje projekty z płaską strukturą (niska wariancja) vs warstwową (wysoka wariancja).

### 6.2 Language bias — pierwsze empiryczne dowody na dużym zbiorze

Pierwsze badanie porównujące te same metryki architektoniczne dla Python, Java i Go na 240 repozytoriach z pełną historią git. Wynik: LCOM4 jest strukturalnie biased przez paradygmat języka — Go zawsze 1.0, Java średnio 0.38. Narzędzia porównujące projekty cross-language bez normalizacji per-język są metodologicznie błędne.

### 6.3 Ortogonalność AGQ i metryk procesowych

Żadna cross-project miara defektów (bugfix\_ratio, hotspot\_ratio, co-change entropy) nie koreluje istotnie statystycznie z AGQ w analizie bez normalizacji. Po zastosowaniu AGQ-adj (size-adjusted) korelacje z hotspot\_ratio i churn\_gini stają się statystycznie istotne (p<0.05). Wynik wspiera hipotezę komplementarności: AGQ i SonarQube mierzą niezależne wymiary jakości, których połączenie daje pełniejszy obraz stanu projektu.

### 6.4 Kalibracja wag composite metric

Pierwsza empiryczna kalibracja wag dla architektonicznej composite metric na danych OSS. Acyclicity=0.73 — wynik zgodny z literaturą. Modularity=0 — nie wnosi niezależnego sygnału predykcyjnego gdy pozostałe metryki są obecne. Implikacja praktyczna: uproszczony model `AGQ = 0.73 * acy + 0.17 * coh + 0.05 * stab` ma niższy MSE niż model równoważny — ale wagi te wymagają replikacji na zbiorach danych z innych języków i domen.

---

## 7. Strategia dalszego rozwoju i plan badawczy

### 7.1 Uzasadnienie strategii — score diagnostyczny i osobna warstwa predykcyjna

AGQ w obecnej postaci jest wartościowy jako interpretowalny wskaźnik diagnostyczny: każda składowa ma bezpośrednie znaczenie architektoniczne, a wynik końcowy można wytłumaczyć deweloperowi w terminach grafu zależności — nie jako wyjście czarnej skrzynki. Ta właściwość jest kluczowa dla praktycznego zastosowania w procesie wytwarzania oprogramowania: narzędzie diagnostyczne musi wskazywać nie tylko "ile", ale "gdzie" i "dlaczego". Z tego powodu AGQ powinien pozostać prostym, kalibrowanym score'em, a nie być rozbudowywany w kierunku złożonego modelu predykcyjnego, którego interpretowalność by ucierpiała.

Przeprowadzone benchmarki na 240 repozytoriach pokazują, że AGQ wykazuje statystycznie istotne, lecz umiarkowane korelacje z proxy metryk procesowych: acyclicity vs hotspot\_ratio (r=+0.223, p<0.01), AGQ-adj vs hotspot\_ratio (r=+0.236, p<0.001). Efekty te tłumaczą kilka procent wariancji zmiennych procesowych — wynik typowy dla statycznych metryk architektonicznych w literaturze, potwierdzający że AGQ mierzy ortogonalny wymiar jakości względem metryk kodu. Oznacza to że AGQ dostarcza informacji której nie dostarczają istniejące narzędzia, ale jednocześnie wskazuje, że sam statyczny score nie wyczerpuje przestrzeni predykcyjnej. Dalsze prace badawcze nie powinny polegać na próbie zwiększenia mocy wyjaśniającej przez dodawanie kolejnych składowych do composite score'u, lecz na budowie oddzielnej warstwy predykcyjnej, która AGQ traktuje jako jeden z wielu sygnałów wejściowych.

Rosnący udział kodu generowanego przez modele językowe tworzy specyficzne ryzyko architektoniczne: modele optymalizują pod kątem lokalnej poprawności i spójności leksykalnej, nie zaś pod kątem globalnych właściwości grafu zależności. Kod AI-generowany może przechodzić testy jednostkowe i uzyskiwać wysokie oceny narzędzi leksykalnych, jednocześnie wprowadzając cykliczne zależności, zaburzając hierarchię pakietów lub obniżając spójność modułów. AGQ w obecnej postaci adresuje tę lukę reaktywnie — jako gate przy każdym commicie. Przewidywanie przyszłych naruszeń przed ich wprowadzeniem wymaga rozbudowy o cechy temporalne i procesowe, których obecna wersja nie zawiera.

Proponowane podejście polega na utrzymaniu AGQ jako stabilnego, interpretowalnego score'u diagnostycznego oraz równoległym rozwijaniu osobnego modelu predykcyjnego, który łączy cechy architektoniczne z cechami temporalnymi, procesowymi i semantycznymi. Oba komponenty są konceptualnie odrębne: AGQ opisuje aktualny stan architektury, predictor szacuje prawdopodobieństwo przyszłych problemów utrzymaniowych. Mieszanie tych warstw prowadziłoby do utraty interpretowalności bez gwarancji wzrostu mocy predykcyjnej.

---

### 7.2 Proponowane grupy cech dla warstwy predykcyjnej

**Cycle / SCC graph features**

Obecna metryka acyclicity operuje na jednej liczbie: proporcji węzłów w największym SCC. Jest to agregat, który gubi informację o topologii cykli — ich liczbie, głębokości, wzajemnym zagnieżdżeniu i lokalizacji w hierarchii pakietów. Rozbudowa o cechy takie jak liczba rozłącznych SCC, średnica najdłuższego cyklu, procentowy udział krawędzi tworzących cykle czy rozkład wielkości SCC może istotnie wzbogacić sygnał predykcyjny bez utraty interpretowalności poszczególnych cech. W kontekście AI-generowanego kodu cykle są szczególnie istotne — modele językowe nie mają globalnej wiedzy o grafie zależności i naturalnie generują import "na skróty", który domyka cykl niewidoczny z perspektywy lokalnego pliku.

**Boundary / coupling features**

Badania D'Ambros i Lanzy (WCRE 2009) wskazują, że krawędzie graniczne między klastrami architektonicznymi są silniejszym predyktorem defektów niż ogólny coupling. Cechy takie jak boundary crossing ratio, liczba krawędzi naruszających zadeklarowane constraints, asymetria przepływu zależności między klastrami czy udział krawędzi cross-layer w całkowitej liczbie krawędzi dostarczają informacji lokalnej, którą aggregaty globalne tracą. W projektach z policy-as-a-service (zaimplementowanym przez `qse discover`) zestaw tych cech może być generowany automatycznie jako pochodna wykrytych klastrów Louvain.

**Temporal / drift features**

Metryki statyczne opisują stan architektury w jednym momencie. Dla predykcji problemów utrzymaniowych kluczowe jest to, jak szybko i w jakim kierunku architektura ewoluuje. Cechy temporalne — delta AGQ między kolejnymi wersjami, tempo wzrostu liczby krawędzi cross-cluster, czas życia cyklu od wprowadzenia do naprawy, wskaźnik regresji architektonicznej — mogą zbudować sygnał predykcyjny niedostępny dla metryk statycznych. Kierunek ten jest szczególnie wartościowy badawczo, ponieważ nie był dotychczas systematycznie eksplorowany w połączeniu z metrykami AGQ na dużych zbiorach danych.

**Process / churn / ownership features**

Statyczne metryki architektoniczne i procesowe mierzą ortogonalne wymiary, ale ich łączenie w jednym modelu może dawać efekt synergiczny. Cechy procesowe do rozważenia: churn per moduł znormalizowany przez rozmiar, Gini coefficient rozkładu zmian, liczba autorów per moduł (bus factor proxy), proporcja fix-commitów dotykających modułu oraz co-change entropy między parami modułów. Cechy te są dostępne z historii git bez żadnych zewnętrznych danych.

**Stability / layering features**

Obecna metryka stability operuje na wariancji instability per pakiet, co poprawnie odróżnia architekturę warstwową od płaskiej, ale nie opisuje jakości konkretnych warstw ani ich wzajemnych relacji. Cechy rozszerzające: liczba wykrytych poziomów topologicznych w DAG po usunięciu cykli, proporcja pakietów o nieokreślonej roli (I ≈ 0.5), zgodność z zadeklarowanymi przez użytkownika ograniczeniami warstw. Stabilność warstw jest szczególnie istotna w projektach gdzie AI generuje kod bez świadomości istniejącej hierarchii.

**Structural code features**

Cechy strukturalne niezależne od semantyki kodu: stosunek klas abstrakcyjnych do konkretnych per pakiet, liczba interfejsów jako punktów rozszerzenia, głębokość hierarchii dziedziczenia per moduł, proporcja metod publicznych do prywatnych jako proxy enkapsulacji. Cechy te mają interpretację architektoniczną, nie leksykalną, i wzbogacają model bez powielania tego co mierzą narzędzia do analizy kodu.

---

### 7.3 Metodologia prac badawczych

Planowany workflow rozbudowy warstwy predykcyjnej:

**Feature inventory** — zebranie i ujednolicenie wszystkich cech dostępnych w obecnym pipeline'ie QSE, uzupełnionych o nowe cechy z grup powyżej. Na tym etapie bez filtrowania — celem jest kompletna mapa przestrzeni cech z opisem źródła danych i kosztu obliczeniowego.

**Sanity filtering** — eliminacja cech z wartościami stałymi lub quasi-stałymi per język (jak cohesion=1.0 dla całego Go), cech z >20% braków danych i cech nieodtwarzalnych bez pełnej historii git.

**Univariate analysis** — dla każdej cechy obliczenie korelacji Spearmana ze zmiennymi docelowymi (hotspot\_ratio, churn\_gini, bugfix\_ratio) osobno per język i cross-language. Wyniki raportowane transparentnie z n, r i p-value, bez cherry-pickingu.

**Redundancy / multicollinearity check** — dla kandydatów z poprzedniego kroku obliczenie macierzy korelacji wzajemnych. Cechy z |r|>0.80 między sobą traktowane jako redundantne — pozostawiamy tę o wyższej korelacji z targetem. Cel: uniknięcie iluzorycznego wzrostu mocy modelu przez dodawanie skorelowanych cech.

**Model selection** — porównanie baseline (AGQ-adj jako jedyna cecha) z modelami rozszerzonymi: liniowym (regularyzacja Lasso), XGBoost, random forest. Walidacja przez stratified k-fold (k=10) z osobnymi zbiorami per język. Metryki: Spearman r z targetem, MSE, feature importances. Raportowanie przedziałów ufności, nie tylko estymatorów punktowych. Warstwa Predictor może być realizowana z użyciem metod uczenia maszynowego — wybór klasy modeli będzie przedmiotem walidacji empirycznej, a nie założeniem a priori. Oczekuje się, że porównanie modeli liniowych z regularyzacją (Lasso, Ridge) z modelami drzewiastymi (XGBoost, random forest) dostarczy wiedzy o nieliniowości zależności i interpretowalności wynikowego modelu. Żaden z tych wariantów nie jest z góry preferowany.

**Interpretability / ablation study** — dla najlepszego modelu iteracyjne usuwanie grup cech i obserwacja spadku jakości. Cel: identyfikacja grup koniecznych vs redundantnych oraz weryfikacja braku data leakage (cechy procesowe obliczone na tym samym oknie czasowym co target).

---

### 7.4 Pozostałe pytania badawcze

**A) Temporal AGQ — drift architektoniczny w czasie**
Jak zmienia się AGQ projektu przez lata? Czy projekty z intensywnym użyciem AI degradują architektonicznie szybciej niż pisane ręcznie? Wymaga analizy per-commit na pełnej historii git.

**B) Kalibracja wag per język**
Czy wagi (acyclicity=0.73, cohesion=0.17) są stabilne dla Java i Go? Wymaga wystarczającego zbioru labelowanych przykładów per język.

**C) Walidacja na projektach przemysłowych**
Czy wnioski z OSS generalizują się na zamknięte projekty korporacyjne? Wymaga partnerstw przemysłowych i dostępu do kodu pod NDA.

**D) Expert labeling — pilotaż**
5 projektów ocenionych przez 2 doświadczonych architektów oprogramowania, korelacja z AGQ jako pilotażowe badanie walidacyjne z ludzkim ground truth.

**E) Cykl życia naruszenia**
Jak długo żyje naruszenie reguły architektonicznej zanim zostanie naprawione? Czy typ naruszenia koreluje z MTTR?

---

*Planowany etap badawczy zakłada rozbudowę systemu QSE o osobną warstwę predykcyjną, konceptualnie odrębną od istniejącego score'u AGQ. Obecna wersja AGQ stanowi interpretowalny, diagnostyczny wskaźnik jakości architektonicznej, którego statystycznie istotne, lecz umiarkowane korelacje z metrykami procesowymi (r≈0.18–0.24 na n=234) potwierdzają ortogonalność wymiaru architektonicznego względem metryk kodu i procesu. Dalszy rozwój nie będzie polegał na rozbudowie composite score'u, lecz na systematycznej ekspansji przestrzeni cech o sześć grup sygnałów: grafowe cechy cykli, cechy graniczne między klastrami, cechy temporalne opisujące drift architektoniczny, cechy procesowe z historii git, cechy jakości warstwowania oraz cechy strukturalne klas. Dla każdej grupy przeprowadzona zostanie univariate analysis względem zmiennych docelowych, z następującą eliminacją redundancji i budową modelu predykcyjnego walidowanego przez cross-validation z rozdzieleniem per język. Wyniki będą raportowane z pełnymi statystykami i przedziałami ufności. Celem badawczym nie jest zastąpienie AGQ modelem black-box, lecz wykazanie, że połączenie interpretowalnego score'u architektonicznego z rozszerzoną przestrzenią cech umożliwia predykcję ryzyka utrzymaniowego na poziomie istotnie wyższym niż każda z tych warstw osobno.*

---

## 8. Istniejące zasoby

| Zasób | Opis | Lokalizacja |
|---|---|---|
| Kod QSE | 244 testów, pełne CLI, Rust + Python | `qse/`, `qse-core/`, `tests/` |
| Benchmark Python-80 | 80 repo, pełna historia git | `artifacts/benchmark/agq_enhanced_python80.json` |
| Benchmark Java-79 | 79 repo, pełne klony | `artifacts/benchmark/agq_enhanced_java80.json` |
| Benchmark Go-81 | 81 repo, pełne klony | `artifacts/benchmark/agq_enhanced_go80.json` |
| Benchmark cross-language 240 | Python+Java+Go, enhanced metrics | `artifacts/benchmark/agq_enhanced_*.json` |
| Rust qse-core | Scanner 7–46× szybszy | `qse-core/`, `qse-py/` |
| AGQ Enhanced metrics | AGQ-z, Fingerprint, CycleSeverity, ChurnRisk, AGQ-adj | `qse/agq_enhanced.py` |
| Kalibracja wag | L-BFGS-B + LOO-CV, n=74 | `artifacts/benchmark/agq_weight_calibration.json` |
| Policy discovery | Wstępna walidacja na Django i Spring Boot | `qse/discover.py` |
| Literatura | 40+ źródeł | `artifacts/references.md` |
| IP | Metodologia kwalifikuje się do zgłoszenia patentowego | — |

**Repozytorium:** https://github.com/PiotrGry/qse-pkg

---

## 9. Wpływ społeczny i ekonomiczny

Badania wskazują że znaczna część czasu inżynierów oprogramowania jest tracona na pracę wynikającą ze złej architektury — trudny onboarding, debugging problemów spowodowanych cyklicznymi zależnościami, refactoring który trwa wielokrotnie dłużej niż planowano [ŹRÓDŁO]. Koszty te rosną proporcjonalnie do rozmiaru zespołu i skali systemu.

QSE adresuje ten problem poprzez:

1. **Wczesne wykrywanie** — nie po fakcie gdy dług jest duży, ale przy każdym commicie
2. **Automatyzację** — nie wymaga manualnego code review architektonicznego
3. **Egzekwowanie** — nie "sugestie" ale blokada gdy jakość spada poniżej progu

---

*Dokument przygotowany na podstawie badań przeprowadzonych w [Uczelnia]. Kod i dane dostępne: https://github.com/PiotrGry/qse-pkg*
