# QSE - Work Packages i Kamienie Milowe
## Wersja zatwierdzona (marzec 2026) - wariant 71/29 BI/PR

---

## Tabela WP

| WP | Miesiące | Typ | Kamień milowy | KPI / próg PASS | TRL |
|---|---|---|---|---|---|
| WP-BR1 | 1–6 | **BI** | M1 (m-c 6) | r_s(AGQ, expert_score) ≥ 0.60; n≥50; p<0.01 | 4→5 |
| WP-BR2 | 7–12 | **BI** | M2 (m-c 12) | r(ΔAGQ, defect_rate_DoE) ≥ 0.55; p<0.01; n≥250 | 5→6 |
| WP-BR3 | 12–18 | **BI** | M3 (m-c 18) | H5: monotoniczność konwergencji 7B→70B + gate pass ≥85% | 6 |
| WP-BR4 | 19–24 | **PR** | M4 (m-c 24) | Redukcja regresji ≥15% (crossover, n≥10 zespołów); TRL = 6 (warunkowo 7) | 6→6(7) |

**Ratio: 71% BI / 29% PR**

---

## Infrastruktura obliczeniowa (HPC) - wymaganie cross-cutting

Dostęp do środowiska HPC (on-premise lub subskrypcja chmurowa) jest **warunkiem
koniecznym** powodzenia projektu od pierwszego miesiąca. Zapotrzebowanie rośnie
z kolejnymi WP:

| WP | Zapotrzebowanie HPC | Uzasadnienie |
|---|---|---|
| WP-BR1 (m 1–6) | CPU cluster: skanowanie ≥500 repo × 3 języki, inter-procedural graph | Construct validity wymaga pełnego benchmarku + opcjonalnie call graph |
| WP-BR2 (m 7–12) | CPU cluster: 5000 konfiguracji DoE (5θ × 4 typy × 50 repo × 5 powtórzeń) | Mutacje + reskan każdej konfiguracji; sekwencyjne wykonanie = miesiące |
| WP-BR3 (m 12–18) | **GPU cluster: DPO fine-tuning 7B→70B** (≥4× A100 80GB) | Prep dataset od m12 (overlap z BR2); trening 70B wymaga min. 320 GB VRAM |
| WP-BR4 (m 19–24) | CPU: CI/CD pipeline, integracja z repo partnerów | Skanowanie w czasie rzeczywistym w środowisku crossover |

**Formy realizacji (alternatywne):**
- On-premise: zakup/leasing serwera GPU (amortyzacja w budżecie BI)
- Chmura: subskrypcja AWS/GCP/Azure z instancjami GPU (p4d/a2-megagpu)
- HPC akademicki: dostęp do klastra uczelnianego (np. Cyfronet, PCSS)
- Hybryda: CPU on-prem + GPU cloud-burst dla BR3

**Kamienie milowe infrastrukturalne (operacyjne, nie badawcze - brak KPI):**
- **m-c 1**: środowisko HPC operational (procurement lub aktywacja subskrypcji)
  - Kryterium: pipeline skanuje ≥1 repo end-to-end na infrastrukturze docelowej
- **m-c 2**: pipeline benchmark zwalidowany end-to-end na HPC
  - Kryterium: 10 repo × 3 języki ukończone bez błędu, wyniki reprodukowalne (delta=0.0)
- **m-c 12**: środowisko GPU gotowe do treningu DPO (przed startem BR3)
  - Kryterium: DPO dry-run na 7B model (1 epoch, ≤100 samples) ukończony bez OOM

> Uwaga: kamienie infra są operacyjne (enablery), nie badawcze. Nie mają KPI-ID w tabeli zbiorczej. Ich nieosiągnięcie opóźnia WP, ale nie wpływa na decyzję go/no-go.

---

## Uzasadnienia Frascati per WP

### WP-BR1 - Construct validity (BI)
Niepewność badawcza: czy AGQ mierzy to samo co ekspert-architekt ocenia jako "jakość architektury"?
Wymaga: human labeling study (3 ekspertów × 50 repo), opcjonalnie call graph inter-proceduralny
(baseline: file-level), korekcja language bias.
Wynik niepewny - może okazać się że AGQ nie zgadza się z ekspertem.

### WP-BR2 - Predictive validity (BI)
DoE z kontrolowaną injekcją defektów architektonicznych (θ ∈ {0, 0.25, 0.5, 0.75, 1.0}).
Zmienna zależna: defect_rate = regresje/zmiany, nie proxy (churn/hotspot).
Wynik niepewny - korelacja może nie osiągnąć progu 0.55.

**Operacjonalizacja θ - 4 typy mutacji architektonicznych:**

| Typ | Mechanizm | Co degraduje |
|---|---|---|
| Cycle injection | Dodanie importu zamykającego cykl | Acyclicity |
| Layer violation | Import z warstwy wyższej do niższej | Stability |
| Cohesion degradation | Przeniesienie metody do obcego modułu | Cohesion |
| Hub creation | Klasa z fan-out > 2σ powyżej średniej | Modularity |

θ = odsetek modułów poddanych mutacji danego typu.
Mutatory skryptowe (deterministyczne) - eliminują confound AI/human.
Design: 5θ × 4 typy × 50 repo × 5 powtórzeń = 5000 konfiguracji.
Analiza: linear mixed-effects model z repo jako random intercept.

### WP-BR3 - Applied validity / Architectural RLHF (BI) - m 12–18 (overlap z BR2)
**Timeline:** m12 = prep dataset (pary dobry/zły kod z wyników DoE BR2); m13-18 = trening DPO
(7B/13B/70B), eval, publikacja. Overlap 1 miesiąca z BR2 daje 7 miesięcy efektywnych.

**KLUCZOWY ARGUMENT:** Dotychczasowe prace stosowały binarne sygnały jakości
kodu (pass/fail testów, linting) jako reward w RLHF/DPO. QSE oferuje
fundamentalnie inny sygnał: AGQ composite - ciągłą miarę [0,1] opartą na
4 ortogonalnych składowych grafowych, z empirycznie kalibrowanymi wagami.

Żadna publikacja nie badała:
(a) czy ciągła metryka architektoniczna działa jako reward signal w DPO,
(b) czy monotoniczność konwergencji zachodzi przy skalowaniu 7B→70B
    dla domain-specific structural code metrics,
(c) jaki jest transfer AGQ-reward na unseen architectural patterns.

Hipoteza H5 (monotoniczność) nie ma precedensu w literaturze.
DPO jako technika jest znana - ten konkretny reward signal + hipoteza = BI.
Osadzenie w literaturze: reward shaping (Ng et al. 1999) - AGQ jako
potential-based reward function spełnia warunki policy invariance.

### WP-BR4 - Walidacja eksperymentalna (PR)
Crossover design: 10 zespołów inżynierskich, within-subjects.
Każdy zespół: 8 tyg. bez QSE + 8 tyg. z QSE (randomized order).
Moc statystyczna wyższa niż between-subjects A/B przy tym samym n.
**Nie "wdrożenie"** (wdrożenie = non-B+R, wykluczone wg kryteriów str. 8).
Językowo: "walidacja eksperymentalna", "pilotowe uruchomienie w kontrolowanym
środowisku partnera badawczego", "testy crossover z realnymi zespołami".

---

## Tabela KPI zbiorczych

| KPI-ID | KPI | Próg PASS | WP |
|---|---|---|---|
| KPI-01 | r_s(AGQ, expert_architectural_score) - construct validity | ≥ 0.60; p<0.01 | WP-BR1 |
| KPI-02 | Partial r controlling age confounder | ≥ 0.55; p<0.05 | WP-BR1 |
| KPI-03 | Czas skanowania **inter-procedural graph** (call graph + DFG cross-file) 80k LOC | ≤ 2 min | WP-BR1 |
| KPI-04 | r(ΔAGQ, defect_rate) DoE - predictive validity | ≥ 0.55; p<0.01 | WP-BR2 |
| KPI-05 | Cross-validation r na held-out 20% | ≥ 0.50 | WP-BR2 |
| KPI-06 | Dataset DoE (Zenodo) | ≥ 250 obs. | WP-BR2 |
| KPI-07 | H5: monotoniczność konwergencji 7B→70B (udokumentowana) | potwierdzona | WP-BR3 |
| KPI-08 | QSELiner gate pass rate (1st attempt) | ≥ 85% | WP-BR3 |
| KPI-09 | Model HuggingFace + karta modelu | opublikowany | WP-BR3 |
| KPI-10 | Redukcja regression rate (crossover, n≥10 zespołów) | ≥ 15% | WP-BR4 |
| KPI-11 | TRL końcowy | 6 (warunkowo 7 z partnerem przemysłowym) | WP-BR4 |
| KPI-01b | ICC(3,k) - inter-rater reliability ekspertów | ≥ 0.70 | WP-BR1 |

---

## Logika korelacji przez projekt

```
WP-BR1: r_s(AGQ, expert) ≥ 0.60    → czy mierzymy właściwą rzecz?
WP-BR2: r(ΔAGQ, defects) ≥ 0.55    → czy przewidujemy defekty?
WP-BR3: r(AGQ_LLM, defects) ≥ 0.55 → czy transferuje na generowany kod?
WP-BR4: regresje ↓ 15%              → czy działa u ludzi?
```

Każdy WP to wyższy poziom dowodu tej samej hipotezy:
AGQ mierzy architektoniczną jakość która przekłada się na stabilność systemu.

---

## Go/no-go gates

| Gate | Moment | Warunek STOP | Warunek PASS | Warunek warunkowy |
|---|---|---|---|---|
| G1 | m-c 6 (M1) | KPI-01 < 0.45 | KPI-01 ≥ 0.60 | r ∈ [0.45, 0.60): kontynuacja z korektą scope BR2 |
| G2 | m-c 12 (M2) | KPI-04 < 0.40 | KPI-04 ≥ 0.55 | r ∈ [0.40, 0.55): zawężenie scope BR3 |
| G3 | m-c 18 (M3) | KPI-07 nie potwierdzona AND KPI-08 < 60% | KPI-07 potwierdzona AND KPI-08 ≥ 85% | KPI-08 ∈ [60%, 85%): BR4 startuje z ograniczonym scope (mniej zespołów, focus na diagnostykę) |

**G3 uzasadnienie:** Jeśli DPO fine-tuning nie wykazuje monotoniczności konwergencji (H5) i gate pass rate jest poniżej 60%, crossover z zespołami w BR4 nie ma podstaw merytorycznych - sygnał AGQ nie jest internalizowalny przez model. Wariant warunkowy (pass 60-85%) pozwala na BR4 z zawężonym scope: diagnostyka przyczyn niskiego transferu zamiast pełnego crossover.

---

## Bridge: łańcuch dowodowy i adresowanie luk

### POC → BR3 (ciągłość mechanizmu)

Pilot (prompt engineering, generate_loop.py) wykazał kierunek efektu:
Sonnet convergence p=0.012 (Fisher exact). Pilot pass rate (50%) nie jest
benchmarkiem dla DPO - to inne medium transferu sygnału.

BR3 przechodzi do DPO fine-tuningu - prompt feedback ≠ weight update.
To celowa eskalacja mechanizmu: jeśli sygnał architektoniczny działa
w prompcie (słabszy mechanizm), DPO (silniejszy - internalizacja w wagach
modelu) powinien go wzmocnić. Luka jest realna i adresowana explicite:
pilot dowodzi że sygnał AGQ jest informatywny, DPO testuje czy jest
internalizowalny.

### BR2 → BR3 (mostek predykcja → reward)

Jeśli ΔAGQ koreluje z defect_rate (BR2), to AGQ niesie sygnał jakościowy
→ reward oparty na tym sygnale jest informed, nie arbitralny.
DPO z informed reward > DPO z arbitrary reward (Rafailov et al. 2023).

### BR3 → BR4 (mostek fine-tuning → walidacja w terenie)

BR3 produkuje fine-tuned QSELiner (najlepszy wariant z siatki 7B/13B/34B/70B)
z udokumentowaną krzywą uczenia i gate pass rate. BR4 integruje ten model
w pipeline CI/CD partnera crossover: QSELiner analizuje PR przed merge
i generuje architektoniczny feedback (AGQ delta + rekomendacja).

Transfer: BR3 dostarcza model + inference API; BR4 testuje czy feedback
zmienia zachowanie zespołu (redukcja regresji ≥15%). Jeśli G3 warunkowy
(pass 60-85%): BR4 zawęża scope do diagnostyki - dlaczego transfer jest
niepełny (za mały model? za wąski training set? specyfika języka?) -
i dokumentuje warunki brzegowe zamiast pełnego crossover.

Kluczowa różnica BR3 vs BR4: BR3 mierzy jakość modelu (wewnętrzna
walidacja), BR4 mierzy efekt na ludzi (zewnętrzna walidacja). Model może
mieć wysokie gate pass a mimo to nie zmieniać zachowania zespołu - to
jest niepewność badawcza BR4.

### r² = 3–6% (adresowanie niskiej wariancji)

Obserwacyjne r²=3–6% (AGQ alone vs proxy churn/hotspot) jest zaniżone przez:
(a) zaszumiony proxy (churn_gini, rzetelność ≈ 0.40),
(b) confound dojrzałości projektu,
(c) brak kontroli eksperymentalnej.

DoE w BR2 eliminuje (b) i (c). Predictor (warstwa 3) łączy AGQ z 5 grupami
cech (temporalne, procesowe, boundary, zespołowe, domenowe) - target >25% R².
Samo AGQ nie jest predictorem - jest jednym z sygnałów wejściowych.

---

## Ryzyka i mitygacja

| Ryzyko | P-stwo | Wpływ | Plan B |
|---|---|---|---|
| KPI-01 r ∈ [0.50, 0.60) | ŚREDNIE | G1 warunkowy | Rekalibracja wag + rozszerzenie zbioru ekspertów |
| ICC ekspertów < 0.70 | NISKIE | Ground truth niejasny | Dodatkowy ekspert + sesja kalibracyjna |
| KPI-04 r < 0.55 | ŚREDNIE | G2 warunkowy | Ensemble z metrykami procesowymi |
| Pilot pass rate nie transferuje do DPO | ŚREDNIE | BR3 zagrożone | AGQ jako reward shaping (Ng 1999), nie jedyny reward |
| n=10 zespołów BR4 - niska moc | WYSOKIE | Type II error | Crossover design (within-subjects) zwiększa moc vs between-subjects |
| Inter-procedural graph zbyt kosztowny | NISKIE | Opóźnienie BR1 | Baseline file-level (nie jest warunkiem koniecznym) |

---

## Uzasadnienie KPI-04 (próg 0.55) - do wniosku

Wyniki obserwacyjne POC: r_s(AGQ-adj, hotspot_ratio) = 0.24 na n=234 repo OSS
(cross-language, p<0.001). Korelacja podlega atenuacji z powodu zaszumionego
proxy (hotspot_ratio, rzetelność ≈ 0.40) oraz confoundera dojrzałości projektu.
Uwaga: kierunek korelacji jest pozytywny (wyższy AGQ-adj = więcej hotspotów),
co sugeruje confounding - dojrzałe repo mają lepszą architekturę i więcej
hotspotów jednocześnie. DoE w BR2 eliminuje ten confound.

Korekcja atenuacji (Fuller 1987):

  r_true = r_obs / √(reliability_x × reliability_y)
         = 0.24 / √(0.95 × 0.40) ≈ 0.39

Przejście do bezpośredniego pomiaru defect_rate w DoE (rzetelność ≈ 0.85):

  r_controlled ≥ 0.39 × √(0.85/0.40) ≈ 0.57

Próg 0.55 jest konserwatywny. Precedens: Hassan (2009) - obserwacyjne r≈0.20
→ kontrolowane r≈0.55 dla podobnej klasy metryk.

---

## TRL start = 4 - linia obrony

**Argumenty:**
1. Brak integracji z rzeczywistym CI/CD użytkownika końcowego
2. Brak walidacji przez eksperta-architekta (KPI-01 nie jest jeszcze osiągnięty)
3. Korelacja r=0.24 to sygnał w proxy, nie w docelowej zmiennej (defect_rate)
4. Środowisko "240 OSS repo" = kontrolowane przez badacza, nie przez użytkownika
5. Żaden developer nie potwierdził że fingerprint/AGQ zmienia jego decyzje

**Framing POC:** "Wstępna walidacja laboratoryjna na zbiorze referencyjnym OSS,
potwierdzająca obliczalność i deterministyczność metryk (delta=0.0 na 240 repo).
TRL 5 wymaga walidacji w środowisku relewantnym - tj. ekspert-architekt potwierdza
że AGQ odpowiada jego ocenie (KPI-01, WP-BR1)."

---

## Wariant finansowy

| Parametr | Wartość (V7) |
|---|---|
| Koszty ogółem | 5 104 180 PLN |
| Grant (dofinansowanie) | 3 787 135 PLN |
| BI | 3 623 135 PLN |
| PR | 1 481 045 PLN |
| Ratio BI/PR | **71/29** |
| Intensywność (blended) | 74.2% |
| HPC (M1-24) | 400 000 PLN |
| Instrument | de minimis BGK |

**Decyzja: 71/29** - maksymalizacja grantu przy zachowaniu argumentu Frascati dla WP-BR3.
Ryzyko WP-BR3: argument Frascati oparty na nowości reward signalu (ciągły AGQ composite vs binarne code quality), nie na nowości techniki DPO.
