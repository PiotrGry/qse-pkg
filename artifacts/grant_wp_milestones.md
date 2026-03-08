# QSE — Work Packages i Kamienie Milowe
## Wersja zatwierdzona (marzec 2026) — wariant 70/30 BI/PR

---

## Tabela WP

| WP | Miesiące | Typ | Kamień milowy | KPI / próg PASS | TRL |
|---|---|---|---|---|---|
| WP-BR1 | 1–6 | **BI** | M1 (m-c 6) | r_s(AGQ, expert_score) ≥ 0.60; n≥50; p<0.01 | 4→5 |
| WP-BR2 | 7–12 | **BI** | M2 (m-c 12) | r(ΔAGQ, defect_rate_DoE) ≥ 0.55; p<0.01; n≥250 | 5→6 |
| WP-BR3 | 13–18 | **BI** | M3 (m-c 18) | H5: monotoniczność konwergencji 7B→70B + gate pass ≥85% | 6 |
| WP-BR4 | 19–24 | **PR** | M4 (m-c 24) | Redukcja regresji ≥15% (A/B, n≥5 zespołów); TRL = 7 | 6→7 |

**Ratio: 70% BI / 30% PR**

---

## Uzasadnienia Frascati per WP

### WP-BR1 — Construct validity (BI)
Niepewność badawcza: czy AGQ mierzy to samo co ekspert-architekt ocenia jako "jakość architektury"?
Wymaga: human labeling study (3 ekspertów × 50 repo), nowy call graph inter-proceduralny,
korekcja language bias. Wynik niepewny — może okazać się że AGQ nie zgadza się z ekspertem.

### WP-BR2 — Predictive validity (BI)
DoE z kontrolowaną injekcją defektów architektonicznych (θ ∈ {0, 0.25, 0.5, 0.75, 1.0}).
Zmienna zależna: defect_rate = regresje/zmiany, nie proxy (churn/hotspot).
Wynik niepewny — korelacja może nie osiągnąć progu 0.55.

### WP-BR3 — Applied validity / Architectural RLHF (BI)
**KLUCZOWY ARGUMENT:** POC (generate_loop.py, OR=24.5) dotyczył DDD preset —
binarnych detektorów (anemic/fat/zombie) na modelu komercyjnym (Sonnet).
WP-BR3 bada inny, niezbadany przypadek: AGQ composite (ciągła miara 0-1,
4 składowe) jako reward signal w DPO dla open-source LLM (7B–70B).
Hipoteza H5: monotoniczność konwergencji reward względem rozmiaru modelu
nie ma precedensu w literaturze dla domain-specific structural code metrics.
DPO jako technika jest znana — ten konkretny reward signal + typ modelu + hipoteza = BI.

### WP-BR4 — Walidacja eksperymentalna (PR)
Testy A/B z realnymi zespołami inżynierskimi w warunkach zbliżonych do operacyjnych.
**Nie "wdrożenie"** (wdrożenie = non-B+R, wykluczone wg kryteriów str. 8).
Językowo: "walidacja eksperymentalna", "pilotowe uruchomienie w kontrolowanym
środowisku partnera badawczego", "testy A/B z realnymi zespołami".

---

## Tabela KPI zbiorczych

| KPI-ID | KPI | Próg PASS | WP |
|---|---|---|---|
| KPI-01 | r_s(AGQ, expert_architectural_score) — construct validity | ≥ 0.60; p<0.01 | WP-BR1 |
| KPI-02 | Partial r controlling age confounder | ≥ 0.55; p<0.05 | WP-BR1 |
| KPI-03 | Czas skanowania 80k LOC | ≤ 2 min | WP-BR1 |
| KPI-04 | r(ΔAGQ, defect_rate) DoE — predictive validity | ≥ 0.55; p<0.01 | WP-BR2 |
| KPI-05 | Cross-validation r na held-out 20% | ≥ 0.50 | WP-BR2 |
| KPI-06 | Dataset DoE (Zenodo) | ≥ 250 obs. | WP-BR2 |
| KPI-07 | H5: monotoniczność konwergencji 7B→70B (udokumentowana) | potwierdzona | WP-BR3 |
| KPI-08 | QSELiner gate pass rate (1st attempt) | ≥ 85% | WP-BR3 |
| KPI-09 | Model HuggingFace + karta modelu | opublikowany | WP-BR3 |
| KPI-10 | Redukcja regression rate (A/B, n≥5 zespołów per grupa) | ≥ 15% | WP-BR4 |
| KPI-11 | TRL końcowy | 7 | WP-BR4 |

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

## Uzasadnienie KPI-04 (próg 0.55) — do wniosku

Wyniki obserwacyjne POC (r = 0.23 na n=237 repo OSS) podlegają atenuacji
z powodu zaszumionego proxy (churn_gini, rzetelność ≈ 0.40) oraz confoundera
dojrzałości projektu. Korekcja atenuacji (Fuller 1987):

  r_true = r_obs / √(reliability_x × reliability_y)
         = 0.23 / √(0.95 × 0.40) ≈ 0.37

Przejście do bezpośredniego pomiaru defect_rate w DoE (rzetelność ≈ 0.85):

  r_controlled ≥ 0.37 × √(0.85/0.40) ≈ 0.54

Próg 0.55 jest konserwatywny. Precedens: Hassan (2009) — obserwacyjne r≈0.20
→ kontrolowane r≈0.55 dla podobnej klasy metryk.

---

## TRL start = 4 — linia obrony

**Argumenty:**
1. Brak integracji z rzeczywistym CI/CD użytkownika końcowego
2. Brak walidacji przez eksperta-architekta (KPI-01 nie jest jeszcze osiągnięty)
3. Korelacja r=0.23 to sygnał w proxy, nie w docelowej zmiennej (defect_rate)
4. Środowisko "237 OSS repo" = kontrolowane przez badacza, nie przez użytkownika
5. Żaden developer nie potwierdził że fingerprint/AGQ zmienia jego decyzje

**Framing POC:** "Wstępna walidacja laboratoryjna na zbiorze referencyjnym OSS,
potwierdzająca obliczalność i deterministyczność metryk (delta=0.0 na 78 repo).
TRL 5 wymaga walidacji w środowisku relewantnym — tj. ekspert-architekt potwierdza
że AGQ odpowiada jego ocenie (KPI-01, WP-BR1)."

---

## Wariant finansowy

| Wariant | Grant | +1 pkt K3 (PR>50%) | Ryzyko Frascati |
|---|---|---|---|
| 50/50 obecny | 2 912 462 | NIE | NISKIE |
| **70/30 (wybrany)** | **3 078 888** | NIE | ŚREDNIE (WP-BR3) |
| 40/60 | 2 829 249 | TAK | NISKIE |

**Decyzja: 70/30** — +166k grantu vs brak punktu K3.
Ryzyko WP-BR3 zarządzalne po przeformułowaniu argumentu DDD vs AGQ.
