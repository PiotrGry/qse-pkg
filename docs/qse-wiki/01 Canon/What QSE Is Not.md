---
type: canon
language: pl
---

# Czym QSE nie jest

## Prostymi słowami

QSE jest narzędziem do mierzenia jakości architektonicznej — i tylko tego. Nie jest superinteligentnym narzędziem które wykrywa wszystkie problemy. Nie zastępuje code review. Nie prognozuje przyszłości. To ważne żeby wiedzieć, bo błędne oczekiwania prowadzą do złego użycia.

---

## Szczegółowy opis

### QSE NIE mierzy jakości kodu

**Co to znaczy:** AGQ mierzy relacje między modułami (graf zależności), nie treść poszczególnych plików.

Projekt może mieć:
- **Wysokie AGQ** (dobra architektura) + **zły kod** (nieczytelne funkcje, brak dokumentacji, stare wzorce)
- **Niskie AGQ** (zła architektura) + **dobry kod** (czytelne, dobrze przetestowane pliki)

To nie jest defekt AGQ — to jest dowód, że architektura i jakość kodu to dwa **różne wymiary**.

```
Empiryczny dowód: n=78, brak korelacji AGQ z oceną SonarQube (wszystkie p>0.10)
→ Oba narzędzia są potrzebne jednocześnie, nie zamiast siebie.
```

### QSE NIE jest linterem

**Linter** (Pylint, ESLint, Checkstyle) analizuje każdy plik osobno i wskazuje konkretne linie kodu do naprawy: „funkcja `foo` ma zbyt wiele argumentów", „zmienna `x` jest nieużywana".

**QSE** analizuje cały projekt jako system i zwraca metryki globalne: „15% modułów w cyklach", „Stability=0.26 — brak wyraźnej hierarchii". Nie wskazuje konkretnych linii — wskazuje wzorce strukturalne.

`qse discover` identyfikuje naruszenia granic modułowych, ale na poziomie modułu, nie linii.

### QSE NIE zastępuje SonarQube

SonarQube i QSE **wzajemnie się uzupełniają**:

| | SonarQube | QSE |
|---|---|---|
| Poziom analizy | Plik (linia kodu) | System (graf modułów) |
| Co wykrywa | Błędy · code smells · bezpieczeństwo · duplikaty | Cykle · brak warstw · niska spójność · modularity |
| Wynik | Issue list, rating A–F | AGQ [0,1], Fingerprint |
| Czas analizy | Minuty (wymaga budowania) | < 1 sekunda |
| Korelacja między sobą | **Brak** (n=78, p>0.10) | — |

Brak korelacji empirycznej oznacza, że narzędzie z oceną A w SonarQube może mieć niskie AGQ i vice versa. Oba są potrzebne.

### QSE NIE wykrywa błędów

AGQ nie mierzy:
- ❌ błędów programistycznych (NullPointerException, IndexError)
- ❌ luk bezpieczeństwa (SQL injection, XSS)
- ❌ problemów z wydajnością (wąskie gardła, wycieki pamięci)
- ❌ pokrycia testami

Do tych celów istnieją dedykowane narzędzia (testy jednostkowe, skanery bezpieczeństwa, profiler).

### QSE NIE jest narzędziem predykcyjnym

**AGQ jest diagnostyczny** — mierzy aktualną strukturę projektu. Nie prognozuje:
- czy projekt będzie miał problemy w przyszłości
- kiedy nastąpi awaria
- ile bugów pojawi się w następnym sprincie

Korelacje AGQ z metrykami procesowymi są statystycznie istotne, ale umiarkowane:
- r=+0.236 z hotspot_ratio (p<0.001)
- r=−0.154 z churn_gini (p=0.018)
- r²≈3–6% wyjaśnionej wariancji

**Interpretacja:** AGQ to jeden z wielu czynników wpływających na procesy wytwarzania. Inne czynniki (rozmiar zespołu, domena, zarządzanie, historia projektu) tłumaczą 94–97% zmienności.

> **Analogia:** AGQ to badanie krwi. Mówi aktualne wartości parametrów. Sam wynik nie prognozuje choroby — to wejście do dalszej analizy.

Warstwa Predictor (która miałaby prognozować ryzyko) jest **planowana badawczo, ale nie istnieje** w obecnej wersji systemu.

### QSE NIE zastępuje code review

QSE nie:
- nie czyta semantyki kodu (co robi funkcja, czy logika jest poprawna)
- nie ocenia nazewnictwa zmiennych i funkcji
- nie sprawdza czy testy testują właściwe zachowania
- nie wychwytuje problemów domenowych

Code review pozostaje niezbędny. QSE uzupełnia review o strukturalną perspektywę na poziomie systemu.

### QSE NIE działa dobrze na małych projektach

Projekty z mniej niż ~50 węzłami wewnętrznymi mają **zawyżone AGQ**:
- Brak cykli w 5-plikowym projekcie jest trywialny → acyclicity=1.0 bez sensu
- Modularity dla 3 modułów jest nieinterpretowalna
- AGQ-adj częściowo koryguje ten efekt, ale nie eliminuje go

AGQ jest wiarygodne dla projektów z ≥50 węzłami wewnętrznymi.

---

## Tabela podsumowująca

| Błędne przekonanie | Rzeczywistość |
|---|---|
| „AGQ mierzy jakość kodu" | AGQ mierzy strukturę architektoniczną, nie treść plików |
| „QSE to zaawansowany linter" | Linter patrzy na linie, QSE na graf między modułami |
| „QSE zastępuje SonarQube" | Oba mierzą różne ortogonalne wymiary — oba potrzebne |
| „Niskie AGQ = projekt jest zły" | Niskie AGQ to sygnał, nie wyrok. Kubernetes: AGQ-z=−2.58, działa doskonale. |
| „Wysokie AGQ = projekt jest dobry" | AGQ mierzy jeden wymiar. Projekt może mieć AGQ=1.0 i być nieużywalny. |
| „QSE przewiduje defekty" | AGQ jest diagnostyczny. r²≈3–6%. Nie prognozuje przyszłości. |
| „Mogę porównywać AGQ Java i Python" | Language bias uniemożliwia bezpośrednie porównania. Używaj AGQ-z. |
| „Predictor to część QSE" | Predictor nie istnieje. Planowany badawczo, odrębny od AGQ. |

---

## Definicja formalna — granice systemu

QSE operuje na zbiorze **statycznych właściwości strukturalnych** grafu zależności wewnętrznych modułów. Wszelkie właściwości spoza tego zakresu (semantyka kodu, historia git, zachowanie runtime, ocena ekspercka) są poza granicami systemu.

Formalnie: AGQ jest funkcją `f: G → [0,1]` gdzie G = (V, E) jest grafem zależności. Wszystkie właściwości nieprzedstawialne jako G są nieobserwowalne przez AGQ.

---

## Zobacz też
[[QSE Canon]] · [[Architecture]] · [[Why QSE Exists]] · [[Invariants]] · [[What is QSE in Simple Words]]
