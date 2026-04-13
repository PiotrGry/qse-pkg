---
type: experiment
status: zakończony
language: pl
---

# Pilot OSS — Uruchomienie qse-archtest na repozytorium spoza GT

## Prostymi słowami

Pilotaż testuje narzędzie qse-archtest w realistycznym scenariuszu: fork prawdziwego repozytorium open-source → baseline scan → refactoring architektury sterowany wynikami archtest → ponowny scan → pomiar delta. Cel: sprawdzić, czy (1) wyniki archtest identyfikują realne problemy architektoniczne, (2) refactoring sterowany wynikami faktycznie zmienia metryki, (3) gdzie AGQ ma blind spots.

---

## Szczegółowy opis

### Cel pilotażu

1. **Actionability** — czy wynik archtest wskazuje na realne problemy do naprawienia
2. **Sensitivity** — czy refactoring architektoniczny zmienia AGQ
3. **Blind spot detection** — gdzie AGQ mija się z oceną ekspercką
4. **CI/CD integration** — czy narzędzie da się zintegrować z GitHub Actions

### Wybór repozytorium

**Repozytorium**: `colinbut/monolith-enterprise-application`  
**Fork**: `PiotrGry/qse-pilot-enterprise`  
**Uzasadnienie wyboru**:
- Średnia wielkość (84 pliki Java, 194 nodes, 609 edges)
- Warstwowa architektura (domain/application/infrastructure)
- Widoczne problemy architektoniczne (leaky abstractions, DIP violations)
- Single pom.xml (nie multi-module — czytelna analiza)

### Protokół pilotażu

1. Fork repozytorium → `PiotrGry/qse-pilot-enterprise`
2. Setup GitHub Actions CI z qse-archtest
3. Baseline scan (BEFORE) na branchu `master`
4. Analiza wyników — identyfikacja celów refactoringu
5. Refactoring na branchu `refactor/architecture-improvements`
6. Ponowny scan (AFTER) na zrefaktoryzowanym kodzie
7. Porównanie delta

---

## Wyniki pilotażu

### Baseline (BEFORE)

| Metryka | Wartość |
|---|---|
| **AGQ_v3c** | **0.5739** |
| **Status** | **GREEN** |
| M (Modularity) | 0.6882 |
| A (Acyclicity) | 1.0000 |
| S (Stability) | 0.1900 |
| C (Cohesion) | 0.5147 |
| CD (Coupling Density) | 0.4768 |
| Nodes | 194 |
| Edges | 609 |

**Expert Panel Assessment**: 3.0/10 (NEG) → **BLIND SPOT** — AGQ mówi GREEN, eksperci mówią NEG.

### Zidentyfikowane problemy (z analizy archtest + kodu)

1. **S=0.19 (najsłabsza)** — duża wariancja stabilności między pakietami
2. **ClientServiceImpl** — imports RestTemplate, ObjectMapper, HttpStatus w warstwie domain service → infrastructure leak
3. **ReportingData** — god class agregujący 5 modeli domenowych; istnieją już split classes (Business/Hr/System) ale nie są używane
4. **Repository impls w domain/** — importują DAO z infrastructure, łamiąc DIP
5. **UserServiceImpl** — bezpośredni import UserDao zamiast repository interface

### Przeprowadzony refactoring (19 plików, +451/-129 linii)

1. **Extract ClientProjectPort + ClientProjectAdapter** — port w domain, adapter w infrastructure; ClientServiceImpl nie importuje już RestTemplate/ObjectMapper/HttpStatus
2. **Move 4 repository impls** z `domain/repository/impl/` → `infrastructure/db/repository/` — domain layer zawiera tylko interfejsy
3. **Fix UserServiceImpl** — UserDao → UserRepository (nowy interface + impl)
4. **Refactor ReportingData** — kompozycja BusinessReportingData + HrReportingData + SystemReportingData zamiast bezpośredniej agregacji modeli
5. **Aktualizacja testów** — dopasowanie do nowej struktury pakietów

### Po refactoringu (AFTER) — median 3 uruchomień

| Metryka | Wartość |
|---|---|
| **AGQ_v3c** | **0.5760** |
| **Status** | **GREEN** |
| M (Modularity) | 0.6989 |
| A (Acyclicity) | 1.0000 |
| S (Stability) | 0.1900 |
| C (Cohesion) | 0.5143 |
| CD (Coupling Density) | 0.4768 |
| Nodes | 201 |
| Edges | 631 |

### Delta (AFTER − BEFORE)

| Metryka | BEFORE | AFTER | Delta | Komentarz |
|---|---|---|---|---|
| **AGQ_v3c** | 0.5739 | 0.5760 | **+0.0021** | Minimalny wzrost, w granicach szumu |
| M | 0.6882 | 0.6989 | +0.0107 | Lekka poprawa modularności |
| A | 1.0000 | 1.0000 | 0.0 | Bez zmian (nie było cykli) |
| S | 0.1900 | 0.1900 | 0.0 | **Bez zmian** — problematyczne |
| C | 0.5147 | 0.5143 | −0.0004 | Brak zmiany (szum) |
| CD | 0.4768 | 0.4768 | 0.0 | Bez zmian |
| Nodes | 194 | 201 | +7 | Nowe klasy (port, adaptery, repo impls) |
| Edges | 609 | 631 | +22 | Więcej zależności (dodane interfejsy) |

---

## Wnioski

### 1. Actionability — CZĘŚCIOWA ✅⚠️

Archtest **trafnie** zidentyfikował problemy:
- Niskie S=0.19 wskazało na nierównomierną stabilność pakietów → potwierdzone w kodzie (domain importował infrastructure)
- Analiza grafu zależności ujawniła DIP violations i infrastructure leaks

Ale: actionability wynikała z **analizy szczegółów pod spodem** (pakiety, importy), nie z samej liczby S=0.19. Potrzebna lepsza warstwa insightów.

### 2. Sensitivity — NISKA ⚠️

AGQ zmienił się o **+0.0021** po istotnym refactoringu (19 plików, usunięcie wszystkich domain→infra violations). To jest **w granicach szumu** stochastycznego algorytmu Louvain (M waha się ±0.01 między uruchomieniami).

Kluczowy problem: **S=0.19 nie zmieniło się wcale**, mimo że refactoring fundamentalnie zmienił kierunki zależności między pakietami. S mierzy wariancję Martin's instability I = Ce/(Ca+Ce) na poziomie pakietów — przeniesienie klas między pakietami zmienia rozkład Ce/Ca, ale w tym przypadku nie wystarczająco.

### 3. Blind spot — POTWIERDZONY ❌

AGQ=0.574→0.576 (GREEN) vs Expert Panel=3.0/10 (NEG). Blind spot **nie został rozwiązany** przez refactoring. Przyczyna: projekt stosuje over-engineered interface/impl pattern, który influje M i A bez dostarczania realnej jakości architektonicznej. AGQ nie odróżnia "interfejs bo DIP" od "interfejs bo Java boilerplate".

### 4. CI/CD integration — SUKCES ✅

GitHub Actions pipeline działał poprawnie:
- `.github/workflows/archtest.yml` — setup Python, install tree-sitter, run archtest
- Czas: ~30s na scan 84-plikowego projektu
- Exit code 0/1/2/3 poprawnie obsługiwane

### Implikacje dla QSE

| Aspekt | Ocena | Implikacja |
|---|---|---|
| S sensitivity | Zbyt niska | S wymaga investigation — czy Martin I variance wyłapuje te refactoringi? Może potrzeba alternatywnej metryki dependency-direction |
| Blind spot | Nierozwiązany | AGQ nie wyłapuje "fake layering" — interface/impl bez realnej separacji. Potencjalnie potrzebna metryka "abstraction quality" |
| Tool integration | Dobra | CLI i CI pipeline działają, format output jest OK |
| Insight quality | Do poprawy | Archtest powinien dawać actionable insights, nie tylko liczby |

---

## Artefakty

- `artifacts/pilot_results.json` — pełne wyniki BEFORE/AFTER
- Repo: [PiotrGry/qse-pilot-enterprise](https://github.com/PiotrGry/qse-pilot-enterprise)
- Branch: `refactor/architecture-improvements` (commit `0a3b594`)
- Baseline: `docs/ARCHTEST_BASELINE.md` (commit `0cf79cb`)

## Zobacz też

- [[qse-archtest CLI]] — opis narzędzia
- [[Current Priorities]] — kontekst
- [[Experiments Index]] — indeks eksperymentów
- [[AGQv3c Java]] — wzór AGQ
