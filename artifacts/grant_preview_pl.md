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

**QSE (Quality Score Engine)** to system który automatycznie mierzy jakość architektoniczną oprogramowania, klasyfikuje jej typ oraz egzekwuje reguły architektoniczne w procesie wytwarzania oprogramowania (CI/CD). Działa dla **Python, Java i Go** z jednego interfejsu.

QSE składa się z pięciu warstw:

```
┌─────────────────────────────────────────────────────────┐
│  WARSTWA 5: AGQ Enhanced                                │
│  AGQ-z, Fingerprint, CycleSeverity, ChurnRisk, AGQ-adj  │
├─────────────────────────────────────────────────────────┤
│  WARSTWA 4: Policy-as-a-Service                         │
│  Automatyczne reguły architektoniczne (qse discover)    │
├─────────────────────────────────────────────────────────┤
│  WARSTWA 3: Quality Gate (TRL4 + ratchet)               │
│  Blokada gdy jakość spada poniżej progu                 │
├─────────────────────────────────────────────────────────┤
│  WARSTWA 2: AGQ Metrics (4 naprawione + kalibracja)     │
│  Modularity, Acyclicity, Stability, Cohesion            │
├─────────────────────────────────────────────────────────┤
│  WARSTWA 1: Scanner (Python AST + Rust tree-sitter)     │
│  Python, Java (Maven/Gradle), Go — 30× szybszy w Rust   │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Jak działa — krok po kroku

**Krok 1: Skanowanie kodu — wykrywanie języka automatyczne**

```bash
$ qse agq /ścieżka/do/projektu
```

System zlicza pliki `.py/.java/.go` i wybiera silnik:
- **Python** → Python AST scanner (sprawdzony, szybki)
- **Java/Go** → Rust qse-core z tree-sitter (30× szybszy)

Kluczowa innowacja dla Javy: zamiast ścieżki pliku (`android.guava-testlib.src.com.google.common...`) QSE czyta deklarację `package com.google.common.collect;` → semantycznie poprawne nazwy modułów (`com.google.common.collect.ImmutableList`).

**Krok 2: Graf wewnętrznych zależności**

QSE buduje graf gdzie węzły = moduły źródłowe, krawędzie = importy. Kluczowe: `internal_graph` odfiltruje węzły zewnętrzne (stdlib, biblioteki third-party). Cykl przez `os` czy `java.util` nie jest architektonicznym problemem — cykl między własymi modułami tak.

**Krok 3: Cztery metryki AGQ** (szczegóły w sekcji 3)

**Krok 4: Pięć metryk Enhanced** — NOWE

Na podstawie czterech bazowych QSE oblicza pięć dodatkowych wymiarów:

| Metryka | Co daje | Przykład |
|---|---|---|
| **AGQ-z** | Percentyl w języku — usuwa language bias | jackson: 4.3%ile Java |
| **Fingerprint** | Typ architektury (7 wzorców) | [TANGLED], [CLEAN], [LAYERED] |
| **CycleSeverity** | Powaga cykli: NONE/LOW/MEDIUM/HIGH/CRITICAL | HIGH = 15% klas w pętli |
| **ChurnRisk** | Ryzyko nierównego rozkładu zmian | CRITICAL → pilna refaktoryzacja |
| **AGQ-adj** | Score skorygowany o rozmiar projektu | małe i duże repo porównywalne |

**Krok 5: Wynik z wyjaśnieniem**

```
# Zamiast suchego "AGQ=0.46 FAIL":
AGQ GATE PASS  agq=0.4618  M=0.57 A=0.85 St=0.26 Co=0.16  lang=Java
  [TANGLED]  z=-1.71 (4.3%ile Java)  cycles=HIGH (15% klas w cyklach)
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
# Wynik dla Spring Boot:
# 27 reguł m.in.: forbidden: org.springframework.boot.loader/* → org.springframework/*
# (classloader nie może zależeć od kodu aplikacji)

$ qse agq . --constraints .qse/arch.json
# Każdy PR sprawdzany czy respektuje granice architektoniczne
```

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

### 4.0 Benchmark 237 repozytoriów — podsumowanie cross-language (NOWE)

Największy benchmark architektoniczny cross-language: **237 w pełni sklonowanych repozytoriów** (Python-78, Java-77, Go-80) z pełną historią git.

**Kluczowe statystyki:**

| Język | n | Średnie AGQ | Cohesion | Acyclicity | % z cyklami |
|---|---|---|---|---|---|
| Go | 80 | **0.817** | **1.000** | **1.000** | **0%** |
| Python | 78 | 0.746 | 0.647 | 0.999 | 4% |
| Java | 77 | **0.619** | **0.379** | 0.973 | **73%** |

**Fingerprint distribution (237 repo):**

| Wzorzec | Total | Python | Java | Go | Interpretacja |
|---|---|---|---|---|---|
| LAYERED | 68 | 57 | 4 | 7 | Warstwowa architektura — dobra |
| CLEAN | 49 | 1 | 1 | **47** | Strukturalnie czysty — Go dominuje |
| LOW_COHESION | 44 | 4 | **40** | 0 | Klasy robią za dużo — Java problem |
| MODERATE | 39 | 12 | 11 | 16 | Przeciętny, bez patologii |
| FLAT | 23 | 5 | 8 | 10 | Brak warstw — **dominujący pattern złej arch.** |
| TANGLED | 9 | 0 | **9** | 0 | Cykle + niska spójność — Java OOP dług |
| CYCLIC | 5 | 0 | **5** | 0 | Cykle bez innych patologii |

**NAJWAŻNIEJSZE ODKRYCIE:** Wzorzec FLAT (brak warstw architektonicznych) jest dominującym wzorcem złej architektury cross-language — pojawia się u najgorszych projektów w każdym języku: `home-assistant` (Python, z=-2.81), `avro` (Java, z=-3.11), `kubernetes` (Go, z=-2.58).

**Nowe statystycznie istotne korelacje (n=231-237):**

| Para | r_s / r | p-value |
|---|---|---|
| acyclicity vs hotspot_ratio | +0.223 | **0.001** |
| stability vs hotspot_ratio | +0.173 | **0.009** |
| AGQ vs churn_gini | -0.128 | 0.052 |
| **AGQ-z vs churn_gini** | **-0.130** | **0.048*** |
| **AGQ-adj vs churn_gini** | **-0.162** | **0.014*** |
| **AGQ-adj vs hotspot_ratio** | **+0.232** | **<0.001*** |
| **ChurnRisk vs hotspot_ratio** | **-0.149** | **0.024*** |

Size-adjusted AGQ (AGQ-adj) ma **najsilniejszą korelację** z churn — usunięcie bias rozmiaru wzmacnia sygnał architektoniczny.

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

### 4.2 Benchmark Java-77 (pełne klony)

**Zbiór danych:** 77 z 80 repozytoriów Java — **pełne klony**, pełna historia git.
Kluczowa różnica vs poprzednie benchmarki: shallow clone maskował 73% cykli w Javie.

**Statystyki zbiorcze:**

| Metryka | Wartość |
|---|---|
| Liczba repo | 77 |
| Średnie AGQ | 0.621 |
| Spread | 0.368 |
| Std | 0.087 |
| Min AGQ | 0.471 (jackson-databind, TANGLED) |
| Max AGQ | 0.839 (dagger, LAYERED) |
| Repo z cyklami | **59/77 = 77%** (niewidoczne w shallow clone!) |

**Najlepsze i najgorsze (z AGQ-z i fingerprint):**

| Repo | AGQ | Fingerprint | AGQ-z | Percentyl |
|---|---|---|---|---|
| dagger | 0.839 | LAYERED | +2.51 | 99% |
| spring-boot | 0.803 | LAYERED | +2.09 | 98% |
| immutables | 0.784 | LAYERED | +1.87 | 97% |
| resilience4j | 0.777 | LOW_COHESION | +1.80 | 96% |
| log4j | 0.731 | LOW_COHESION | +1.27 | 90% |
| ... | ... | ... | ... | ... |
| commons-lang | 0.533 | CYCLIC | -1.01 | 16% |
| flyway | 0.498 | CYCLIC | -1.40 | 8% |
| kryo | 0.502 | TANGLED | -1.36 | 9% |
| jsoup | 0.478 | TANGLED | -1.60 | 5% |
| jackson-databind | 0.471 | TANGLED | -1.71 | 4% |

**Odkrycie metodologiczne:** Poprzednie analizy (shallow clone) pokazywały acy=1.000 dla wszystkich Java repo. Pełne klony ujawniają że **59/77 (77%) ma cykliczne zależności** — fundamentalna zmiana interpretacji. Jednak obecność cykli NIE koreluje jednoznacznie z niską jakością: spring-boot (LAYERED, top 2%) też ma drobne cykle (acy=0.999).

### 4.3 Benchmark Go-80 (pełne klony)

**Zbiór danych:** 80 repozytoriów Go — **pełne klony**.

**Statystyki zbiorcze:**

| Metryka | Wartość |
|---|---|
| Liczba repo | 80 |
| Średnie AGQ | 0.816 |
| Spread | 0.266 |
| Std | 0.061 |
| Min AGQ | 0.655 (kubernetes, FLAT) |
| Max AGQ | 0.920 (staticcheck, CLEAN) |
| Repo z cyklami | **0/80 = 0%** |
| Cohesion = 1.000 | **80/80 = 100%** |

**Najlepsze i najgorsze (z AGQ-z):**

| Repo | AGQ | Fingerprint | AGQ-z | Percentyl |
|---|---|---|---|---|
| staticcheck | 0.920 | CLEAN | +1.66 | 95% |
| grpc-gateway | 0.920 | CLEAN | +1.65 | 95% |
| protoc-gen-go | 0.902 | CLEAN | +1.35 | 91% |
| connect-go | 0.898 | CLEAN | +1.30 | 90% |
| gore | 0.891 | CLEAN | +1.18 | 88% |
| ... | ... | ... | ... | ... |
| buf | 0.684 | FLAT | -2.12 | 1% |
| flux | 0.681 | FLAT | -2.17 | 1% |
| grafana | 0.678 | FLAT | -2.21 | 1% |
| kubernetes | 0.655 | FLAT | -2.58 | 0.5% |

**Odkrycie:** Wzorzec FLAT dominuje wśród najgorszych Go projektów — nie CYCLIC (cykli nie ma) ani TANGLED (cohesion=1.0 zawsze), ale brak hierarchii warstw (stability niska). kubernetes, grafana to "platform" projekty gdzie flat structure jest bardziej design decision niż defekt.

### 4.4 Porównanie między językami — odkrycie language bias (237 repo, pełne klony)

| Wymiar | Python (78) | Java (77) | Go (80) |
|---|---|---|---|
| Średnie AGQ | 0.746 | 0.621 | **0.816** |
| Cohesion śr. | 0.647 | **0.379** | **1.000** |
| Acyclicity śr. | 0.999 | 0.973 | **1.000** |
| % repo z cyklami | 4% | **77%** | **0%** |
| Stability śr. | 0.806 | 0.486 | 0.736 |
| Modularity śr. | 0.533 | **0.637** | 0.531 |
| Dominant pattern | LAYERED | LOW_COHESION | CLEAN |

**To jest pierwsze empiryczne potwierdzenie language bias w metrykach architektonicznych na 237 repozytoriach.** Różnice nie wynikają z jakości kodu, ale z paradygmatów językowych:

- **Go:** interfejsy zamiast dziedziczenia → LCOM4=1 zawsze → cohesion=1.0; ekosystem wymusza brak cykli → acy=1.0
- **Java:** hierarchie klas → cohesion 0.38 średnio; pełne klony ujawniają 77% repo z cyklami (niewidoczne w shallow clone!)
- **Python:** dynamiczny typing → wartości pośrednie; dominant pattern LAYERED (warstwowa architektura)

**Implikacja dla produktu:** Cross-language porównanie AGQ bez normalizacji jest metodologicznie błędne. AGQ-z (percentyl w języku) rozwiązuje ten problem — jackson-databind (4.3%ile Java) i kubernetes (0.5%ile Go) obie są "najgorszymi w swojej klasie" mimo że mają różne absolute AGQ.

**Nowe odkrycie (enhanced metrics, n=237):**
- AGQ-adj (size-adjusted) vs churn_gini: **r=-0.162, p=0.014** ✅
- ChurnRisk vs hotspot_ratio: **r=-0.149, p=0.024** ✅
- TANGLED pattern: mean churn_gini=0.585 (najgorszy), CLEAN: 0.488 (najlepszy)

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

---

## 10. Addendum — Nowe odkrycia z benchmarku pełnych repozytoriów (marzec 2026)

Po przeprowadzeniu benchmarku na **pełnych klonach** (bez ograniczenia historii git) dla 30 repozytoriów (10 Python, 10 Java, 10 Go) uzyskaliśmy istotne nowe wyniki metodologiczne i empiryczne.

### Odkrycie 6: Shallow clone maskuje cykle w Javie — błąd metodologiczny

**Obserwacja:** Przy klonowaniu z limitem historii (`--depth 1`) wszystkie repozytoria Java wykazywały acyclicity = 1.000 (brak cykli). Po pobraniu pełnych repozytoriów: **8 z 10 Java repo ma cykliczne zależności**.

| Repo | Acyclicity (shallow) | Acyclicity (full) |
|---|---|---|
| hibernate-orm | 1.000 | **0.840** |
| mockito | 1.000 | **0.868** |
| jackson-databind | 1.000 | **0.850** |
| spring-boot | 1.000 | **0.999** |

**Implikacja metodologiczna:** Benchmarki oparte na shallow clone są nierzetelne dla analizy architektonicznej. Cykle zależności między klasami wymagają pełnego kodu źródłowego. To odkrycie invaliduje wyniki poprzednich prac używających shallow clone dla Java.

### Odkrycie 7: Acyclicity koreluje statystycznie z churn cross-language

Na 30 repozytoriach (Python + Java + Go), acyclicity jest **jedyną składową** statystycznie istotnie korelującą z hotspot_ratio:

| Składowa | r_s (hotspot) | p-value |
|---|---|---|
| **acyclicity** | +0.423 | **0.020** ✅ |
| modularity | -0.160 | 0.398 |
| stability | +0.157 | 0.406 |
| cohesion | +0.110 | 0.564 |
| agq_score | +0.120 | 0.528 |

Kierunek korelacji jest dodatni (wyższe acyclicity → więcej hotspotów) co wynika z **confounding variable dojrzałości** — projekty Go (acyclicity=1.0) są aktywnie rozwijane (więcej hotspotów), podczas gdy stare Java biblioteki (acyclicity<1.0) zmieniają się rzadko.

Kalibracja wag **acyclicity=0.73** uzyskana w poprzednich eksperymentach jest potwierdzona jako dominująca składowa — jest jedyna statystycznie istotna cross-language.

### Odkrycie 8: Per-language churn correlation — Java gini r=-0.600, p=0.067

Dla samej Javy (n=10): wyższy AGQ → niższe churn_gini (bardziej równomierny rozkład zmian). p=0.067 jest bliskie progu istotności. Na zbiorze n=30 repozytoriów Java (z planowanego rozszerzenia benchmarku) ta korelacja może okazać się statystycznie istotna — co byłoby pierwszą cross-language walidacją AGQ jako predyktora rozkładu zmian w kodzie.

### Implikacje dla dalszych badań

1. **Wszystkie benchmarki architektoniczne powinny używać pełnych klonów** — to standardowa praktyka której dotychczasowa literatura MSR nie egzekwowała
2. **Acyclicity jako cross-language predictor** wymaga replikacji na większym zbiorze (n=100+)
3. **Java-specific validation** — 30 Java repo z pełną historią git jest minimalnym zbiorze dla statystycznie istotnych wniosków


---

## 11. Addendum — Pełny benchmark 235 repozytoriów (Python-78, Java-77, Go-80)

Przeprowadzono największy do tej pory benchmark architektoniczny cross-language na **235 w pełni sklonowanych repozytoriach** (bez ograniczenia historii git).

### Statystyki zbiorcze

| Język | n | Średnie AGQ | Std | Min | Max | Cohesion | Acyclicity | Stability |
|---|---|---|---|---|---|---|---|---|
| Go | 80 | **0.817** | 0.063 | 0.657 | **0.937** | **1.000** | **1.000** | 0.736 |
| Python | 78 | 0.746 | 0.055 | 0.581 | 0.860 | 0.647 | 0.999 | 0.806 |
| Java | 77 | **0.619** | 0.089 | **0.463** | 0.838 | **0.379** | 0.973 | **0.486** |

### Odkrycie 9: Java ma cykliczne zależności w 73% repozytoriów

Pełny klon (nie shallow) ujawnił: **56 z 77 repozytoriów Java** (73%) posiada cykliczne zależności między klasami. Dla porównania: Python 4%, Go 0%.

Jest to fundamentalne odkrycie metodologiczne: **poprzednie badania używające shallow clone nieświadomie maskowały cykle w Javie**. Acyclicity=1.000 w poprzednich pracach dla Java wynikała z niekompletności pobierania kodu, nie z faktycznej jakości architektury.

### Odkrycie 10: Pierwsze statystycznie istotne korelacje cross-language (n=235)

| Para | r_s | p-value | Interpretacja |
|---|---|---|---|
| acyclicity vs hotspot_ratio | +0.223 | **0.001** | Dominujący signal cross-language |
| stability vs hotspot_ratio | +0.173 | **0.009** | Drugi statystycznie istotny predictor |
| AGQ vs churn_gini | -0.139 | **0.036** | Wyższy AGQ → równomierniejszy churn |
| Go: AGQ vs churn_gini | -0.270 | **0.017** | Najsilniejszy per-language signal |

Pozytywny kierunek korelacji acyclicity/stability z hotspot wynika z confounding variable — projekty Go (acy=1.0, stab wysoka) są aktywnie rozwijane i naturalnie mają więcej hotspotów. Negatywna korelacja AGQ z churn_gini (-0.139, p=0.036) jest pierwszym poprawnie ukierunkowanym, istotnym statystycznie sygnałem.

### Odkrycie 11: Size bias w AGQ — r_s(nodes, AGQ) = -0.269, p<0.001

Większe repozytoria systematycznie uzyskują niższy AGQ. Jest to ograniczenie metodologiczne wymagające normalizacji per-rozmiar lub osobnych kalibracji dla małych (<500 nodes), średnich (500-5000) i dużych (>5000) projektów.

### Odkrycie 12: Language paradigm dominuje nad jakością kodu

**Bottom 10** cross-language: wyłącznie Java (jsoup, jackson-databind, vavr, kryo, mybatis...)
**Top 10** cross-language: wyłącznie Go (protoc-gen-go, staticcheck, grpc-gateway, connect-go...)

AGQ w formie composite metric mierzy cechy paradygmatu językowego silniej niż indywidualną jakość kodu. **Wniosek: cross-language porównania AGQ wymagają normalizacji per-język.** Per-language AGQ (z-score relative to language distribution) jest metodologicznie poprawniejszy niż absolute AGQ.

