---
type: glossary
language: pl
---

# Panel Score — Ocena panelowa

## Prostymi słowami

Panel Score to „ocena eksperta" przypisana każdemu repozytorium w zbiorze GT. Jak w telewizyjnym konkursie kulinarnym, gdzie jury składa się z kilku sędziów o różnych profilach — ostateczna ocena to średnia ich ocen. W QSE: czterech symulowanych ekspertów o różnych perspektywach wystawia ocenę 1-10 każdemu projektowi.

## Szczegółowy opis

**Panel Score** to zbiorowa ocena jakości architektonicznej repozytorium, uzyskana przez symulowany panel ekspertów. Służy jako etykieta ground truth w zbiorach GT Java i GT Python.

### Skład panelu

Panel składa się z 4 symulowanych recenzentów:

| Recenzent | Profil | Ocenia przede wszystkim |
|---|---|---|
| Puryst architektoniczny | Akademik, znawca wzorców | DDD, Hexagonal, Clean Arch — obecność wzorców |
| Pragmatyk | Senior developer | Możliwość utrzymania, onboarding nowego dewelopera |
| Metrykolog | Data scientist | Obserwowalne metryki strukturalne — spójność, cykle |
| Praktyk przemysłowy | Tech Lead, konsultant | Realistyczna ocena dla projektu przemysłowego |

### Skala i procedura

**Skala:** 1 (bardzo słaba architektura) do 10 (wzorcowa architektura)

**Procedura:**
1. Każdy recenzent analizuje repozytorium niezależnie (kod, strukturę, zależności)
2. Wystawia ocenę 1–10 z uzasadnieniem
3. Panel Score = mean(ocena₁, ocena₂, ocena₃, ocena₄)
4. σ (odchylenie standardowe 4 ocen) obliczane jako miara niezgodności

**Kryteria akceptacji:**
- σ ≤ 2.0 → repozytorium akceptowane
- σ > 2.0 → repozytorium wykluczane lub powtarzana dyskusja

**Przypisanie etykiety:**
- Panel Score ≥ 6.0 → **POS** (pozytywna architektura)
- Panel Score < 6.0 → **NEG** (negatywna architektura)

Próg 6.0 odpowiada ocenie „wystarczająco dobra" — nie wymagamy perfekcji, ale minimalnego poziomu jakości strukturalnej.

### Przykłady z Java GT

| Repozytorium | Panel Score | σ | Etykieta | Uzasadnienie |
|---|---:|---:|---|---|
| ddd-by-examples/library | 8.50 | 0.58 | POS | Wzorcowy DDD, wyraźne Bounded Contexts |
| citerus/dddsample-core | 8.25 | 0.50 | POS | Klasyczny DDD, świetna izolacja warstw |
| spring-petclinic | 6.50 | 0.87 | POS | Prosta ale dobrze ustrukturyzowana aplikacja |
| apache/struts | 2.50 | 0.87 | NEG | Legacy, splątane zależności, god classes |
| macrozheng/mall | 2.00 | 0.71 | NEG | CRUD monolith bez separacji warstw |

### Ograniczenia metodologiczne

**Panel jest symulowany, nie prawdziwy.** Czterech recenzentów to symulowane persony, nie prawdziwi eksperci zewnętrzni. To oznacza:
- Potencjalny bias osoby tworzącej symulację
- Brak inter-rater reliability na prawdziwych ekspertach
- Wyniki mogą różnić się od ocen faktycznych architektów

**Pozytywne aspekty:**
- Szybkość tworzenia GT (każda ocena w minutach, nie godzinach)
- Dokumentowalność (każda ocena z uzasadnieniem)
- Powtarzalność (ta sama procedura dla wszystkich repo)

Pełna walidacja wymagałaby badania inter-rater reliability z prawdziwymi ekspertami — to jeden z planowanych kierunków badań.

## Definicja formalna

$$\text{PanelScore}(r) = \frac{1}{4} \sum_{i=1}^{4} \text{score}_i(r)$$

$$\sigma(r) = \sqrt{\frac{1}{4} \sum_{i=1}^{4} (\text{score}_i(r) - \text{PanelScore}(r))^2}$$

$$L(r) = \begin{cases} POS & \text{jeśli PanelScore}(r) \geq 6.0 \text{ i } \sigma(r) \leq 2.0 \\ NEG & \text{jeśli PanelScore}(r) < 6.0 \text{ i } \sigma(r) \leq 2.0 \\ \text{EXCLUDED} & \text{jeśli } \sigma(r) > 2.0 \end{cases}$$

## Zobacz też

- [[GT|GT]] — Ground Truth — metodologia walidacji
- [[07 Benchmarks/Java GT Dataset|Java GT Dataset]] — pełne dane
- [[07 Benchmarks/Python GT Dataset|Python GT Dataset]] — pełne dane Python
- [[Mann-Whitney|Mann-Whitney]] — test statystyczny na etykietach GT
- [[11 Research/Limitations|Ograniczenia]] — ograniczenia symulowanego panelu
