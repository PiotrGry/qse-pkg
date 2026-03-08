# QSE — Quality Score Engine
## Wniosek grantowy — opis projektu
### Wersja robocza do EU / NCBiR / NCN

---

## 1. Wprowadzenie — problem który rozwiązujemy

### 1.1 Era AI i nowe zagrożenia dla jakości oprogramowania

Sztuczna inteligencja rewolucjonizuje tworzenie oprogramowania. Narzędzia takie jak GitHub Copilot, Cursor czy Claude Code generują dziś ponad 46% nowego kodu na platformie GitHub (dane 2025). Programista opisuje w języku naturalnym co chce osiągnąć, a AI pisze kod w ciągu sekund.

Problem polega na tym, że **AI optymalizuje pod kątem "działa teraz", nie "będzie działać za rok"**. Kod wygenerowany przez AI przechodzi testy jednostkowe, nie zawiera oczywistych błędów, ale systematycznie niszczy wewnętrzną strukturę systemu — jego architekturę.

Wyobraźmy sobie firmę budującą oprogramowanie bankowe. Po roku używania AI do generowania kodu:
- Moduł odpowiedzialny za płatności zaczął importować dane z modułu użytkowników (których nie powinien dotykać)
- W systemie pojawiły się "cykliczne zależności" — moduł A potrzebuje modułu B, moduł B potrzebuje modułu A — co sprawia że zmiana jednego wymaga zmiany drugiego
- Klasy stały się "god objects" — jeden obiekt robi 20 różnych rzeczy zamiast jednej

Żadne istniejące narzędzie tego nie wykrywa. SonarQube (lider rynku) sprawdza jakość kodu linijka po linijce — czy nie ma błędów, czy kod jest czytelny, czy nie ma luk bezpieczeństwa. **Nie sprawdza czy architektura systemu jako całości jest zdrowa.**

### 1.2 Czym jest "dobra architektura" — dla niespecjalisty

Wyobraźmy sobie budynek. Dobry budynek ma:
- **Niezależne pomieszczenia** — łazienka nie musi "wiedzieć" co dzieje się w kuchni
- **Jasne wejścia i wyjścia** — drzwi są tam gdzie powinny być, nie ma dziur w ścianach
- **Hierarchię** — piwnica nie opiera się na dachu

W oprogramowaniu:
- **Niezależne moduły** (modularity) — zmiana w module płatności nie powinna wymuszać zmian w module raportowania
- **Brak cykli** (acyclicity) — moduł A może zależeć od B, ale B nie może zależeć od A
- **Warstwy** (stability) — "jądro" systemu jest stabilne, zmiany zachodzą na "obrzeżach"
- **Skupienie** (cohesion) — każda klasa robi jedną rzecz i robi ją dobrze

---

## 2. QSE — nasze rozwiązanie

### 2.1 Co to jest QSE

**QSE (Quality Score Engine)** to system który automatycznie mierzy jakość architektoniczną oprogramowania i egzekwuje reguły architektoniczne w procesie wytwarzania oprogramowania (CI/CD).

QSE składa się z czterech warstw:

```
┌─────────────────────────────────────────────────┐
│  WARSTWA 4: Policy-as-a-Service                 │
│  Automatyczne reguły architektoniczne           │
├─────────────────────────────────────────────────┤
│  WARSTWA 3: Quality Gate (TRL4)                 │
│  Blokada gdy jakość spada poniżej progu         │
├─────────────────────────────────────────────────┤
│  WARSTWA 2: AGQ Metrics                         │
│  4 metryki strukturalne + 1 test quality        │
├─────────────────────────────────────────────────┤
│  WARSTWA 1: Scanner (Python, Java, Go)          │
│  Analiza kodu źródłowego — graf zależności      │
└─────────────────────────────────────────────────┘
```

### 2.2 Jak działa — krok po kroku

**Krok 1: Skanowanie kodu**
QSE czyta pliki źródłowe i buduje "mapę zależności" — kto od kogo zależy. Jak sieć połączeń między modułami. Ten krok jest 30× szybszy w naszej implementacji Rust niż w konkurencyjnych narzędziach Python (home-assistant: 20 sekund → 0.65 sekundy).

**Krok 2: Obliczanie metryk AGQ**
Na podstawie mapy zależności obliczamy cztery liczby między 0 a 1 (gdzie 1 = doskonały):

**Krok 3: Gate — ocena wynikowa**
Jeśli wynik spada poniżej ustalonego progu → system blokuje zmianę w kodzie.

**Krok 4: Wyjaśnienie naruszenia**
Nie tylko "fail" — konkretne: "moduł `payment/service.py` importuje `user/controller.py`, co narusza regułę separacji domen. Sugestia: użyj interfejsu lub zdarzeń."

---

## 3. Metryki AGQ — wyjaśnienie dla niespecjalisty

### 3.1 Modularity (Modularność) — "czy moduły są naprawdę niezależne?"

**Co mierzy:** Czy system jest podzielony na grupy modułów które intensywnie komunikują się wewnętrznie, ale rzadko z innymi grupami.

**Analogia:** Wyobraź sobie miasto. Dobra dzielnica mieszkalna ma dużo wewnętrznych połączeń (ulice, chodniki między budynkami), ale kilka głównych dróg łączących ją z innymi dzielnicami. Jeśli każda ulica w mieście łączy się z każdą inną — to chaos, nie dzielnice.

**Jak obliczamy:** Używamy algorytmu Louvain — ten sam który Facebook używa do wykrywania "społeczności" w sieciach społecznych. Obliczamy stosunek połączeń wewnątrz grup do połączeń między grupami.

**Wynik 0:** Wszystkie moduły łączą się ze wszystkimi — brak struktury ("big ball of mud")
**Wynik 1:** Moduły tworzą wyraźne, izolowane grupy — idealna modularność

**Kalibracja na danych:** Max Q w naszym zbiorze 127 repo = 0.80. Normalizujemy: `max(0, Q) / 0.75`.

### 3.2 Acyclicity (Acykliczność) — "czy nie ma błędnych pętli zależności?"

**Co mierzy:** Czy istnieją "cykliczne zależności" — sytuacje gdzie A zależy od B, B od C, C od A. To architektoniczny odpowiednik "jajka i kury" — co kompilować/testować pierwsze?

**Analogia:** Wyobraź sobie firmę gdzie dział kadr czeka na decyzję finansową, finanse czekają na plan HR, a HR czeka na decyzję finansową. Nikt nic nie zrobi. W kodzie — zmiana w A wymusza zmianę w B, która wymusza zmianę w C, która wymusza zmianę w A. Niekończąca się pętla.

**Jak obliczamy:** Tarjan's Strongly Connected Components — algorytm z teorii grafów. Szukamy największej "pętli" w grafie zależności.

**Wynik 0:** Cały system jest jedną wielką pętlą — wszystko jest od wszystkiego zależne
**Wynik 1:** Brak jakichkolwiek cykli — każda zależność idzie "w dół"

**Kluczowe odkrycie naukowe:** Ta metryka dominuje w kalibracji — waga 0.73 z 4 metryk. Potwierdzone przez niezależne badania (Gnoyke et al., JSS 2024): "cyclic dependencies correlate with defects most among architectural smells." Nasze obliczenia i literatura są zgodne.

### 3.3 Stability (Stabilność warstw) — "czy architektura ma wyraźne warstwy?"

**Co mierzy:** Stopień w jakim moduły systemu pełnią wyraźnie różne role architektoniczne — jedne są "jądrem" (stabilnym, od wszystkiego zależnym), inne są "obrzeżem" (zmieniającym się, od mało zależnym).

**Analogia:** Wyobraź sobie armię. Generałowie są stabilni — wielu oficerów raportuje do nich, oni sami raportują do niewielu. Żołnierze są niestabilni — raportują do oficerów, ale nikt do nich nie raportuje. Dobrze zorganizowana armia ma wyraźną hierarchię. Kiepska armia — wszyscy raportują do wszystkich, żaden stopień nie ma jasnej roli.

**Jak obliczamy:** Dla każdego pakietu obliczamy I (Instability) = `wychodzące_importy / (wychodzące + przychodzące)`. Pakiet "jądra" ma I≈0 (wiele go importuje, on mało). Pakiet "obrzeża" ma I≈1 (on importuje wiele, mało go importuje). Mierzymy wariancję I — im wyższa, tym wyraźniejsza hierarchia.

**Odkrycie:** Oryginalny wzór Martina (Distance from Main Sequence) degeneruje bez danych o abstrakcji. Nasz wzór oparty na wariancji instability'ego jest pierwszym empirycznie walidowanym zamiennikiem.

### 3.4 Cohesion (Spójność) — "czy każda klasa robi jedną rzecz?"

**Co mierzy:** Czy metody (funkcje) w klasie faktycznie współpracują, dzieląc dane, czy są "przypadkowymi sąsiadami" w tym samym pliku.

**Analogia:** Dobra klasa to jak dobry pracownik — ma jedno stanowisko pracy, wszystkie jego narzędzia służą do jednego celu. Zła klasa to "człowiek-orkiestra" — ma biurko, stół operacyjny i stanowisko kierowcy tira jednocześnie.

**Jak obliczamy:** LCOM4 (Lack of Cohesion of Methods v4) — liczymy ile "wysp" tworzą metody klasy jeśli połączymy te które dzielą atrybuty. Klasa z LCOM4=1 to jeden spójny byt. Klasa z LCOM4=5 powinna być podzielona na 5 mniejszych klas.

**Odkrycie language bias:** Go zawsze = 1.00, Java średnio = 0.33. To nie dlatego że Go jest "lepiej napisane" — Go strukturalnie nie ma wielodziedziczenia → LCOM4=1 zawsze. Java ma złożone hierarchie klas → niższe cohesion jest normą, nie błędem.

### 3.5 QSE_test — "czy testy są dobrej jakości?"

Pięć wymiarów jakości testów:

1. **Assertion density** — ile asercji (sprawdzeń) ma przeciętny test? Test z 0 asercjami niczego nie sprawdza.
2. **Test-to-code ratio** — ile kodu testowego na ile kodu produkcyjnego?
3. **Naming quality** — czy testy mają opisowe nazwy (`test_should_reject_invalid_payment` vs `test_1`)?
4. **Isolation score** — czy testy używają mocków/fictures (izolacja od zewnętrznych systemów)?
5. **Coverage potential** — jaki procent klas domenowych ma co najmniej jeden test?

---

## 4. Wyniki eksperymentalne — pełne dane

### 4.1 Benchmark Python OSS-80

**Zbiór danych:** 78 z 80 repozytoriów Python (2 błędy: ruff — null bytes, lxml — non-UTF-8)

**Weryfikacja tez:**

| ID | Teza | Wynik | Dowód liczbowy |
|---|---|---|---|
| T1 | AGQ jest deterministyczne | ✅ PASS | max delta = 0.0000000000 na 78 repo |
| T2 | AGQ ortogonalne do Sonara | ✅ PASS* | r=-0.21 (komplementarność) |
| T3 | AGQ widzi to czego Sonar nie widzi | ✅ PASS | 21 z 78 repo: Sonar=A, AGQ<próg |
| T4 | AGQ jest szybszy od Sonara | ✅ PASS | mediana 0.32s vs 15.0s (~47× szybciej) |
| T5 | AGQ różnicuje jakość | ✅ PASS | spread=0.548, std=0.093 |

*T2 reinterpretowane: nie "AGQ lepszy od Sonara" ale "AGQ i Sonar mierzą ortogonalne wymiary"

**Ewolucja metryk v1→v4:**

| Wersja | Zmiana | Spread | Std |
|---|---|---|---|
| v1 | Baseline (Martin's D) | 0.286 | 0.050 |
| v2 | Per-node stability variance | 0.337 | 0.057 |
| v3 | Package-level stability | 0.401 | 0.073 |
| v4 | + boundary crossing ratio | **0.548** | **0.093** |

**Interpretacja:** Każda naprawa metryk zwiększała zdolność do rozróżniania projektów. v4 ma spread prawie 2× większy niż v1 — metryki "widzą" więcej.

**Kalibracja wag (L-BFGS-B, LOO-CV, n=74):**

| Składowa | Waga empiryczna | Waga równa | Zmiana |
|---|---|---|---|
| Acyclicity | **0.730** | 0.250 | +193% |
| Cohesion | **0.174** | 0.250 | -30% |
| Stability | **0.050** | 0.250 | -80% |
| Modularity | **0.000** | 0.250 | -100% |

LOO-CV MSE = 0.006 ± 0.013 — model stabilny, nie przeucza się.

**Wyniki per repo (top 10 i bottom 10):**

| Repo | AGQ v4 | Modularity | Acyclicity | Stability | Cohesion |
|---|---|---|---|---|---|
| attrs | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| boto3 | 0.889 | 0.724 | 1.000 | 0.827 | 0.869 |
| whoosh | 0.860 | 0.667 | 1.000 | 0.983 | 0.791 |
| django-rest-framework | 0.847 | 0.565 | 1.000 | 0.967 | 0.857 |
| mako | 0.876 | 0.738 | 1.000 | 0.859 | 0.821 |
| ... | ... | ... | ... | ... | ... |
| flask | 0.457 | 0.417 | 0.795 | 0.488 | 0.692 |
| click | 0.604 | 0.510 | 0.797 | 0.483 | 0.785 |
| aiohttp | 0.497 | 0.339 | 0.714 | 0.563 | 0.855 |

### 4.2 Benchmark Java-30

**Zbiór danych:** 29 z 30 repozytoriów Java (spotbugs błędnie wykryty jako Python)

**Statystyki zbiorcze:**

| Metryka | Wartość |
|---|---|
| Liczba repo | 29 |
| Średnie AGQ | 0.666 |
| Min AGQ | 0.459 (jackson-databind) |
| Max AGQ | 0.814 (spring-boot) |
| Spread | 0.355 |
| Std | 0.089 |

**Wyniki per repo:**

| Repo | AGQ | Nodes | Cohesion | Acyclicity | Stability |
|---|---|---|---|---|---|
| spring-boot | 0.814 | 10520 | 0.512 | 1.000 | 0.929 |
| resilience4j | 0.780 | 1578 | 0.384 | 1.000 | 0.981 |
| log4j | 0.750 | 2955 | 0.337 | 1.000 | 0.899 |
| netty | 0.748 | 4768 | 0.220 | 1.000 | 0.902 |
| testcontainers | 0.735 | 939 | 0.336 | 1.000 | 0.869 |
| opentelemetry | 0.720 | 2526 | 0.275 | 1.000 | 0.921 |
| junit5 | 0.717 | 2039 | 0.303 | 1.000 | 0.868 |
| slf4j | 0.723 | 347 | 0.366 | 1.000 | 0.873 |
| hibernate-orm | 0.706 | 14994 | 0.211 | 1.000 | 0.912 |
| guava | 0.698 | 3110 | 0.199 | 1.000 | 0.902 |
| gson | 0.703 | 348 | 0.228 | 1.000 | 0.880 |
| jooq | 0.707 | 6538 | 0.183 | 1.000 | 0.945 |
| retrofit | 0.733 | 425 | 0.351 | 1.000 | 0.848 |
| flyway | 0.745 | 1540 | 0.299 | 1.000 | 0.936 |
| mockito | 0.673 | 1204 | 0.262 | 1.000 | 0.575 |
| okhttp | 0.675 | 172 | 0.311 | 1.000 | 0.507 |
| caffeine | 0.631 | 1577 | 0.142 | 1.000 | 0.634 |
| assertj | 0.627 | 1899 | 0.182 | 1.000 | 0.627 |
| commons-lang | 0.533 | 536 | 0.100 | 1.000 | 0.566 |
| checkstyle | 0.582 | 3189 | 0.163 | 1.000 | 0.581 |
| junit4 | 0.576 | 460 | 0.150 | 1.000 | 0.578 |
| jackson-core | 0.531 | 207 | 0.124 | 1.000 | 0.534 |
| jackson-databind | 0.459 | 869 | 0.059 | 1.000 | 0.459 |

**Kluczowa obserwacja:** Acyclicity = 1.000 dla WSZYSTKICH repozytoriów Java. Java enforces package structure kompilacyjnie → żadne duże projekty nie mają cykli między pakietami.

### 4.3 Benchmark Go-20

**Zbiór danych:** 20/20 repozytoriów Go

| Metryka | Wartość |
|---|---|
| Liczba repo | 20 |
| Średnie AGQ | 0.816 |
| Min AGQ | 0.652 (kubernetes) |
| Max AGQ | 0.879 (vault) |
| Spread | 0.227 |
| Std | 0.062 |

**Wyniki per repo:**

| Repo | AGQ | Nodes | Cohesion | Acyclicity | Stability |
|---|---|---|---|---|---|
| vault | 0.879 | 2919 | 1.000 | 1.000 | 0.985 |
| fx | 0.877 | 208 | 1.000 | 1.000 | 0.922 |
| prometheus | 0.873 | 1078 | 1.000 | 1.000 | 0.965 |
| hugo | 0.873 | 1284 | 1.000 | 1.000 | 0.983 |
| etcd | 0.863 | 1448 | 1.000 | 1.000 | 0.900 |
| grpc-go | 0.862 | 1412 | 1.000 | 1.000 | 0.862 |
| testify | 0.856 | 114 | 1.000 | 1.000 | 0.854 |
| viper | 0.854 | 74 | 1.000 | 1.000 | 0.801 |
| fiber | 0.849 | 347 | 1.000 | 1.000 | 0.977 |
| gin | 0.845 | 167 | 1.000 | 1.000 | 0.956 |
| cobra | 0.830 | 62 | 1.000 | 1.000 | 0.963 |
| docker | 0.816 | 12005 | 1.000 | 1.000 | 0.734 |
| echo | 0.814 | 142 | 1.000 | 1.000 | 0.921 |
| traefik | 0.790 | 1215 | 1.000 | 1.000 | 0.517 |
| caddy | 0.788 | 519 | 1.000 | 1.000 | 0.724 |
| gorm | 0.784 | 216 | 1.000 | 1.000 | 0.764 |
| zap | 0.784 | 205 | 1.000 | 1.000 | 0.792 |
| terraform | 0.762 | 2346 | 1.000 | 1.000 | 0.540 |
| grafana | 0.677 | 7457 | 1.000 | 1.000 | 0.160 |
| kubernetes | 0.652 | 20237 | 1.000 | 1.000 | 0.107 |

**Kluczowa obserwacja:** Cohesion = 1.000 dla WSZYSTKICH repozytoriów Go. Go strukturalnie uniemożliwia patterns które LCOM4 penalizuje.

### 4.4 Porównanie między językami — odkrycie language bias

| Wymiar | Python (78) | Java (29) | Go (20) |
|---|---|---|---|
| Średnie AGQ | 0.745 | 0.666 | **0.816** |
| Cohesion śr. | ~0.750 | **0.328** | **1.000** |
| Acyclicity śr. | 0.978 | **1.000** | **1.000** |
| Stability śr. | 0.733 | 0.718 | 0.771 |
| Modularity śr. | 0.523 | **0.671** | 0.494 |

**To jest pierwsze empiryczne potwierdzenie language bias w metrykach architektonicznych.** Różnice nie wynikają z jakości kodu, ale z paradygmatów językowych:
- Go: interfejsy zamiast klas → cohesion zawsze 1.0; cykle niemożliwe
- Java: hierarchie klas → cohesion naturalnie niskie; package structure → wyższa modularność
- Python: dynamiczny typing → pośredni wynik

---

## 5. Policy-as-a-Service — automatyczne reguły architektoniczne

### 5.1 Koncepcja

Każda firma ma "zasady architektury" zapisane w dokumentach Confluence których nikt nie czyta. QSE zamienia te dokumenty w **automatycznie egzekwowalne reguły**.

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

Kluczowa innowacja: reguły generują się **automatycznie z istniejącego kodu** przez analizę grafu zależności algorytmem Louvain.

**Przykład dla Spring Boot (Java):**
```bash
qse discover /path/to/spring-boot
```
Wynik:
- 6 klastrów: org.springframework (główny), org.springframework.boot.loader (classloader), org.apache (zewnętrzny), ...
- 27 reguł w tym: `forbidden: org.springframework.boot.loader/* → org.springframework/*` (classloader nie może zależeć od kodu aplikacji)

**Przykład dla Mockito (Java):**
```
Reguła: forbidden: org.mockito/* → org.junit/*
Uzasadnienie: JUnit zależy od Mockito (13 krawędzi) ale nigdy odwrotnie →
Mockito jest stabilną zależnością JUnit, nie powinno od JUnit zależeć
```

Inżynier zatwierdza reguły w 30 minut — nie tygodniami pisze konfigurację.

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

## 6. Odkrycia naukowe — pełny opis

### 6.1 Naprawa metryki Martina

Martin's Distance from Main Sequence (1994) to metryka powszechnie cytowana ale **nigdy empirycznie nie zwalidowana** na dużych zbiorach danych. Nasz eksperyment pokazał że bez danych o abstrakcji (niemal zawsze A=0 w Pythonie), wzór degeneruje do pomiaru instabilności — dokładnie odwrotnego zamysłu.

Zaproponowaliśmy zamiennik: wariancja instability'ego per pakiet. Walidacja: projekt youtube-dl (płaska architektura "plugin") poprawnie dostaje stability=0.23 zamiast 0.99. Django (warstwowy framework) poprawnie 0.93.

### 6.2 Language bias — pierwsze empiryczne dowody

Pierwsza praca empiryczna porównująca te same metryki architektoniczne dla Python, Java i Go na 127 repozytoriach. Wynik: kohezja mierzona LCOM4 jest strukturalnie biased — Go zawsze 1.0, Java średnio 0.33. Implikacja: narzędzia porównujące projekty cross-language bez kalibracji per-język są metodologicznie błędne.

### 6.3 Ortogonalność metryk statycznych i procesowych

Żadna cross-project miara defektów (bugfix_ratio, hotspot_ratio, co-change entropy) nie koreluje statystycznie z AGQ (wszystkie p>0.05). To nie jest porażka — to odkrycie: metryki architektoniczne i procesowe mierzą ortogonalne wymiary jakości. Wspiera to tezę komplementarności z SonarQube.

### 6.4 Kalibracja wag: acykliczność dominuje

Pierwsza empiryczna kalibracja wag composite metric dla architektury. Acyclicity=0.73 — potwierdzone niezależnie przez literaturę (Gnoyke JSS 2024). Modularity=0 — nie wnosi niezależnego sygnału gdy inne metryki są obecne.

### 6.5 Automatyczne odkrywanie polityk

Algorytm łączący Louvain clustering z analizą kierunkowości krawędzi grafu skutecznie wykrywa granice architektoniczne bez konfiguracji. Walidacja: reguły dla Django i Spring Boot są architektonicznie prawidłowe i konsekwentnie utrzymane w kodzie.

---

## 7. Proponowane kierunki dalszych badań

### 7.1 Badania które należy przeprowadzić

**A) Temporal AGQ — drift w czasie**
Jak zmienia się AGQ projektu przez 5 lat? Czy AI-assisted projekty degradują szybciej? Wymaga: pełna historia git, analiza per-commit. Potencjał: pierwsza empiryczna mapa "architectural decay curves."

**B) Kalibracja per język**
Czy wagi (acyclicity=0.73 etc.) są takie same dla Java i Go? Wymaga: wystarczający zbiór labelowanych przykładów dla każdego języka osobno. Potencjał: language-specific AGQ który jest fair cross-language.

**C) Walidacja na projektach przemysłowych**
Czy wnioski z OSS generalizują się na zamknięte projekty korporacyjne? Wymaga: partnerstwa przemysłowe, NDA, dostęp do kodu. Potencjał: najsilniejszy argument naukowy i komercyjny.

**D) Expert labeling**
Zbieramy 50 projektów, prosimy 10 doświadczonych architektów o ocenę jakości architektonicznej. Korelujemy z AGQ. Wymaga: czas ekspertów, protokół oceny. Potencjał: ground truth z ludzką walidacją.

**E) Cykl życia naruszenia**
Jak długo "żyje" naruszenie reguły architektonicznej zanim zostanie naprawione? Czy typ naruszenia koreluje z MTTR? Wymaga: historia commitów + constraints. Potencjał: predykcja "kosztu" naruszeń.

### 7.2 Kamień milowy ML — model predykcji naruszeń

**Cel:** Nauczyć model przewidywać naruszenia architektoniczne ZANIM kod zostanie napisany — na podstawie opisu zmiany (diff, opis w natural language).

**Etap 1 (miesiące 1-6):** Budowa datasetu
- 300+ repozytoriów × historia git × naruszenia constraints = 500k+ labeled examples
- Para (diff który naruszył) + (diff który naprawił) = preference pair

**Etap 2 (miesiące 7-12):** XGBoost predictor
- Wejście: cechy diffu (nowe importy, zmiana liczby klas, depth zmian)
- Wyjście: P(naruszenie) dla każdego pliku
- Target: AUC > 0.80, inference < 10ms

**Etap 3 (miesiące 13-18):** Fine-tuning CodeBERT
- Architectural smell detection z rozumieniem kontekstu kodu
- Target: precision > 0.85, recall > 0.80

**Etap 4 (miesiące 19-24):** Architectural RLHF
- Fine-tune model generowania kodu używając AGQ jako reward signal
- Pozytywne = kod który przeszedł gate
- Negatywne = kod który nie przeszedł gate
- Cel: 85% AI-generated code przechodzi gate na pierwszą próbę (baseline ~40%)

**Kluczowa innowacja:** AGQ jako automatyczny reward signal zastępuje drogi human feedback. Nie potrzebujemy annotatorów — gate jest oracle'em.

### 7.3 Pytania badawcze które wymagają odpowiedzi

1. **Czy AGQ przewiduje czas naprawy bugów (MTTR)?** — wymaga danych z trackerów w stylu JIRA, GitHub Issues z precyzyjnymi timestampami
2. **Czy projekty z wysokim AGQ mają niższy onboarding time?** — wymaga badania z programistami (human study)
3. **Jak AI zmienia AGQ w ciągu roku od wdrożenia Copilota?** — wymaga longitudinalnego studium
4. **Czy policy enforcement zmniejsza architectural drift?** — A/B test: zespoły z QSE vs bez QSE, 6 miesięcy
5. **Czy istnieje "naturalny" poziom AGQ dla danego typu projektu?** — microservices vs monolith vs library vs framework

---

## 8. Istniejące zasoby (zrealizowane przed wnioskiem)

| Zasób | Opis |
|---|---|
| Kod QSE | 215 testów, pełne CLI Python + Rust |
| Benchmark Python | 78 repo, 4 wersje metryk, pełna historia |
| Benchmark Java | 29 repo, pełne klony |
| Benchmark Go | 20 repo |
| Rust qse-core | Scanner 3-30× szybszy, Python+Java+Go |
| Kalibracja wag | L-BFGS-B + LOO-CV, n=74 |
| Policy discovery | Algorytm walidowany na Django, Spring Boot |
| Literatura | 40+ źródeł przejrzanych i zacytowanych |
| IP | Metodologia kwalifikuje się do zgłoszenia patentowego |

---

## 9. Wpływ społeczny i ekonomiczny

Każda firma powyżej 50 programistów traci szacunkowo 15-25% czasu inżynierów na "walczenie z architekturą" — debugging problemów spowodowanych złymi zależnościami, trudny onboarding nowych członków, refactoring który trwa 3× dłużej niż planowano.

Przy średnim koszcie programisty €80k/rok i 50-osobowym zespole: €80k × 50 × 0.20 = **€800k rocznie "zmarnowane" na architektoniczny dług**.

QSE adresuje ten problem poprzez:
1. Wczesne wykrywanie (nie po fakcie gdy dług jest duży)
2. Automatyzację (nie wymaga drogich code review)
3. Egzekwowanie (nie "sugestie" których nikt nie czyta)

Przy hipotetycznym rynku 10,000 firm 50+ programistów w EU i cenie €299/mies: rynek adresowalny = **~€36M/rok**.

---

*Dokument przygotowany na podstawie badań przeprowadzonych w [Uczelnia]. Kod i dane dostępne: https://github.com/PiotrGry/qse-pkg*
