---
type: glossary-index
language: pl
---

# Słownik terminów QSE

Pełny indeks pojęć stosowanych w projekcie QSE. Każdy termin ma co najmniej: definicję prostymi słowami, szczegółowy opis techniczny i powiązania z innymi pojęciami.

Dla czytelnika bez tła technicznego: zacznij od [[Glossary for Non-Technical Readers|Słowniczka dla niespecjalistów]].

---

## Metryki i algorytmy

| Termin | Jednym zdaniem | Plik |
|---|---|---|
| [[AGQ\|AGQ]] | Główna metryka jakości architektury — liczba [0,1] będąca ważoną sumą 5 metryk grafowych | [[AGQ]] |
| [[BLT\|BLT]] | Bug Lead Time — czas od pojawienia się błędu do jego naprawienia | [[BLT]] |
| [[LCOM4\|LCOM4]] | Lack of Cohesion in Methods 4 — ile osobnych „spraw" robi klasa (ideał: 1) | [[LCOM4]] |
| [[Louvain\|Louvain]] | Algorytm wykrywania społeczności w grafie — używany do obliczenia Modularity | [[Louvain]] |
| [[Mann-Whitney\|Mann-Whitney]] | Test statystyczny sprawdzający czy dwie grupy są naprawdę różne | [[Mann-Whitney]] |
| [[Partial Spearman\|Partial Spearman]] | Korelacja rangowa po wyeliminowaniu confoundera (np. rozmiaru projektu) | [[Partial Spearman]] |
| [[Tarjan SCC\|Tarjan SCC]] | Algorytm liniowy O(V+E) do wykrywania cykli zależności | [[Tarjan SCC]] |

---

## Pojęcia architektoniczne

| Termin | Jednym zdaniem | Plik |
|---|---|---|
| [[Blind Spot\|Blind Spot]] | Klasa problemów, których dane narzędzie nie wykrywa | [[Blind Spot]] |
| [[CRUD\|CRUD]] | Create/Read/Update/Delete — typ aplikacji bez złożonej logiki domenowej | [[CRUD]] |
| [[DDD\|DDD]] | Domain-Driven Design — architektura centrowana na modelu domeny biznesowej | [[DDD]] |
| [[Layer\|Warstwa]] | Logiczna grupa modułów na danym poziomie abstrakcji — dobre architektury mają czytelne warstwy | [[Layer]] |
| [[Repository Types\|Typy repozytoriów]] | Klasyfikacja projektów (CLEAN/LAYERED/FLAT/CYCLIC itp.) | [[Repository Types]] |
| [[Type 1 Flat Spaghetti\|Flat Spaghetti]] | Anty-wzorzec: płaski, nieustrukturyzowany projekt bez hierarchii | [[Type 1 Flat Spaghetti]] |
| [[Type 2 Legacy Monolith\|Legacy Monolith]] | Anty-wzorzec: duży, historyczny projekt z narosłymi cyklami i niską hierarchią | [[Type 2 Legacy Monolith]] |

---

## Metodologia badawcza

| Termin | Jednym zdaniem | Plik |
|---|---|---|
| [[GT\|GT (Ground Truth)]] | Zbiór repozytoriów z etykietami eksperckimi — klucz odpowiedzi do walidacji metryki | [[GT]] |
| [[Panel Score\|Panel Score]] | Zbiorowa ocena jakości architektonicznej przez 4 symulowanych ekspertów (skala 1–10) | [[Panel Score]] |

---

## Indeks tematyczny

### Statystyka
- [[Mann-Whitney]] — test różnic między grupami
- [[Partial Spearman]] — korelacja z kontrolą confounders
- [[Glossary for Non-Technical Readers]] — podstawy statystyki prostymi słowami

### Algorytmy grafowe
- [[Louvain]] — Modularity (M)
- [[Tarjan SCC]] — Acyclicity (A)
- [[LCOM4]] — Cohesion (C)

### Anty-wzorce
- [[Type 1 Flat Spaghetti]] — płaski, nieustrukturyzowany
- [[Type 2 Legacy Monolith]] — historyczny, zdegradowany

### Narzędzia i konkurencja
- [[Blind Spot]] — co narzędzia pomijają
- [[Market Analysis|Analiza rynku]] — pełna mapa konkurencji

### Dane benchmarkowe
- [[Benchmark Index|Indeks benchmarków]] — przegląd danych
- [[Java GT Dataset|Java GT]] — n=59, MW p=0.000221
- [[Python GT Dataset|Python GT]] — n=30
- [[Jolak Validation|Jolak]] — walidacja krzyżowa

---

## Zobacz też

- [[Glossary for Non-Technical Readers|Słowniczek dla niespecjalistów]] — wszystkie pojęcia bez żargonu
- [[Research Thesis|Teza badawcza]] — kontekst naukowy
- [[AGQ Formula|Wzór AGQ]] — pełna specyfikacja formuły
