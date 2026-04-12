---
type: concept
language: pl
---

# Panel ekspertów

## Prostymi słowami

Panel ekspertów to sposób na ocenę jakości architektury przez ludzi, nie algorytm. Każde repozytorium jest oceniane przez czterech symulowanych ekspertów reprezentujących różne perspektywy — jak jury w konkursie. Średnia ich ocen staje się "prawdą" (Ground Truth) do kalibracji i walidacji metryk QSE. Bez tej oceny nie wiedzielibyśmy, czy AGQ mierzy coś sensownego.

## Szczegółowy opis

### Cztery role panelu

Panel ekspertów składa się z czterech symulowanych ról (sesja Turn 14, kwiecień 2026):

| Rola | Perspektywa | Co ocenia |
|---|---|---|
| **Purista** | Akademicka czystość | Zgodność z SOLID, DDD, hexagonal; brak naruszeń zasad |
| **Pragmatyk** | Praktyczna utrzymywalność | Łatwość zmiany, testowania, rozumienia przez nowego dewelopera |
| **Metrics-aware** | Dane ilościowe | Modularity, cykle, coupling — widzi metryki i wie co oznaczają |
| **Industry** | Doświadczenie produkcyjne | Czy taka architektura działa w prawdziwym projekcie enterprise |

### Skala i kryteria

Skala ocen: **1–10** (całkowite lub połówkowe)

| Próg | Klasyfikacja | Znaczenie |
|---|---|---|
| ≥ 6.0 | **POS** (pozytywna) | Dobra architektura — godna naśladowania |
| 4.0–5.9 | **UNCLEAR** / pominięta | Niewystarczająca pewność — repo odrzucane z GT |
| < 4.0 | **NEG** (negatywna) | Zła architektura — anty-wzorzec |

Warunek jakości oceny: **σ ≤ 2.0** — jeśli cztery role różnią się między sobą o więcej niż 2 punkty odchylenia standardowego, ocena jest uznana za niepewną i repo nie trafia do GT.

### Przykłady ocen z benchmarku (ns_metrics_gt_v1.json)

**Najwyżej oceniane repozytoria Java (POS):**

| Repo | Panel | Kategoria | Uwagi |
|---|---|---|---|
| ddd-by-examples/library | **8.50** | POS | Wzorcowy DDD |
| citerus/dddsample-core | **8.25** | POS | Klasyczny DDD sample |
| VaughnVernon/IDDD_Samples | **7.75** | POS | Implementacja DDD "Implementing DDD" |
| microservices-patterns/ftgo | **7.75** | POS | Microservices patterns |
| gothinkster/realworld | **7.50** | POS | Clean layered |

**Najniżej oceniane repozytoria Java (NEG):**

| Repo | Panel | Kategoria | Uwagi |
|---|---|---|---|
| macrozheng/mall | **2.00** | NEG | Anemic model, CRUD |
| elunez/eladmin | **2.00** | NEG | CRUD monolith |
| apache/struts | **2.50** | NEG | Framework tangled |
| newbee-ltd/newbee-mall | **2.50** | NEG | CRUD shopping cart |

**Przykłady Python:**

| Repo | Panel | Kategoria |
|---|---|---|
| netbox-community/netbox | 8.00 | POS |
| saleor/saleor | 7.50 | POS |
| ytdl-org/youtube-dl | 2.25 | NEG |
| archivebox/archivebox | 3.00 | NEG |

### Dane zbiorcze Ground Truth

**Java GT** (stan kwiecień 2026, po rozszerzeniu):
- n = 59 (31 POS, 28 NEG)
- Mann-Whitney p = 0.000221 (AGQ v3c)
- Spearman ρ = 0.380
- AUC-ROC = 0.767
- Partial r = 0.447

**Python GT:**
- n = 30 (13 POS, 17 NEG)
- Sygnał w innym kierunku — patrz [[W9 AGQv3c Python Discriminates Quality]]

### Ograniczenia panelu

1. **Symulowany, nie prawdziwy** — cztery role to LLM prompt engineering, nie realni eksperci. To metodologiczne ograniczenie, które musi być opisane w publikacjach.
2. **Selection bias** — repozytoria do oceny nie są losowane z całej populacji, tylko z wyselekcjonowanych kategorii (DDD, CRUD, frameworki).
3. **Środkowa luka** — brak repo z Panel=4–6 w pierwszych zbiorach (dziura w rozkładzie).
4. **Frameworki bezpieczeństwa** — spring-security (Panel=6.5) ma strukturalnie inną architekturę niż projekty biznesowe; panel może nie być odpowiednim kryterium dla bibliotek.

### Dlaczego panel, nie BLT?

Pierwsza wersja GT używała **Bug Lead Time (BLT)** jako proxy jakości (W1). Wynik: r=−0.125 ns po oczyszczeniu z confounders. BLT mierzy kulturę procesu (szybkość naprawiania bugów), nie jakość architektury. Panel ekspertów okazał się znacznie lepszym predyktorem — patrz [[Ground Truth in Simple Words]].

## Definicja formalna

Ocena panelowa repozytorium \(r\):

\[\text{Panel}(r) = \frac{1}{4} \sum_{i=1}^{4} \text{score}_i(r), \quad \text{score}_i \in [1, 10]\]

Klasyfikacja:

\[\text{GT}(r) = \begin{cases} \text{POS} & \text{jeśli } \text{Panel}(r) \geq 6.0 \text{ i } \sigma \leq 2.0 \\ \text{NEG} & \text{jeśli } \text{Panel}(r) < 4.0 \text{ i } \sigma \leq 2.0 \\ \text{UNCLEAR} & \text{wpp.} \end{cases}\]

Repozytorium UNCLEAR jest **wyłączane z GT** — nie wchodzi ani do zbioru pozytywnego, ani negatywnego.

## Zobacz też

- [[Ground Truth in Simple Words]] — intuicja za potrzebą GT
- [[Ground Truth]] — techniczne szczegóły zbioru GT
- [[Experiment]] — jak GT jest używane w eksperymentach
- [[W1 BLT Correlation]] — dlaczego BLT zawiodło
