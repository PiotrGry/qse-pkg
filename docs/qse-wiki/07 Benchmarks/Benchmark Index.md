---
type: benchmark-index
language: pl
---

# Indeks Benchmarków QSE

> **Appendix** — ta sekcja zawiera surowe dane benchmarkowe. Główna narracja projektu znajduje się w sekcjach [[QSE Canon|01 Canon]] i [[QSE Podrecznik|10 Handbook]]. Tutaj trafiasz, gdy chcesz zobaczyć konkretne liczby.

## Dostępne zbiory danych

| Nazwa | Plik wiki | Typ | n | Język | Status |
|---|---|---|---:|---|---|
| Benchmark 558 (iter6) | [[Benchmark 558]] | Benchmark masowy | 558 | Python/Java/Go/TypeScript | ✅ Aktualny |
| Java GT (Ground Truth) | [[Java GT Dataset]] | Zbiór walidacyjny | 59 | Java | ✅ Aktualny (kwiecień 2026) |
| Python GT (Ground Truth) | [[Python GT Dataset]] | Zbiór walidacyjny | 30 | Python | ⚠️ Problem kierunku |
| Jolak Cross-Validation | [[Jolak Validation]] | Walidacja krzyżowa | 8 | Java | ✅ 4/5 potwierdzone |
| OSS-30 Python | (dane w [[Benchmark 558]]) | Podzbiór referencyjny | 30 | Python | ✅ |

---

## Opis zbiorów

### Benchmark 558 — iter6 (główny benchmarking)

Masowy benchmark 558 repozytoriów open-source, wygenerowany w iteracji 6 (kwiecień 2026). Używany do:
- kalibracji wag AGQ per język,
- pomiaru rozkładu wzorców architektonicznych (Fingerprints),
- eksploracji korelacji z metrykami Sonara i danymi git.

Szczegóły: [[Benchmark 558]]

### Java GT (n=59) — zbiór walidacyjny

Główny zbiór ewaluacyjny dla języka Java. Rozszerzony w kwietniu 2026 z n=29 do n=59 przez dodanie 30 nowych repozytoriów z oceną panelową. Kluczowe statystyki:
- MW p=0.000221, Spearman ρ=0.380, AUC=0.767
- POS mean AGQ=0.571, NEG mean AGQ=0.486, Gap=0.085

Szczegóły: [[Java GT Dataset]]

### Python GT (n=30) — zbiór walidacyjny

30 repozytoriów Python z oceną panelową. Wagi Python-specific zawierają komponent `flat_score`. Znany problem odwróconego kierunku niektórych metryk — trwa dochodzenie.

Szczegóły: [[Python GT Dataset]]

### Jolak Cross-Validation (n=8)

8 repozytoriów Java z badania Jolak et al. (2025), zeskanowanych skanerem QSE. Cel: niezależna walidacja klasyfikacji jakości. Wynik: 4/5 wniosków Jolaka potwierdzonych, 1 prawdopodobny.

Szczegóły: [[Jolak Validation]]

---

## Użyte formuły AGQ

| Formuła | Język | Zastosowanie |
|---|---|---|
| AGQ v3c Java | Java | GT Java, Jolak | 
| AGQ v3c Python | Python | GT Python, Benchmark 558 Python |
| AGQ v3c równe wagi | Wszystkie | Benchmark 558 ogółem |

Wzory: [[AGQ Formula]]

---

## Zobacz też

- [[AGQ]] — definicja głównej metryki
- [[GT]] — metodologia zbioru walidacyjnego
- [[Panel Score]] — jak działa ocena panelowa
- [[Experiments Index|Indeks eksperymentów]]
