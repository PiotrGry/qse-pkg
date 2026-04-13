---
type: canon
language: pl
---

# Aktualne priorytety

## Prostymi słowami

To jest lista „co robimy teraz i co jest następne". Priorytety P0–P4 zostały wszystkie ukończone. Obecna faza to wdrożenie: mamy działające narzędzie CLI (qse-archtest), specyfikację testów architektury, i pilotaż na prawdziwych repozytoriach.

---

## Szczegółowy opis

### Status zadań P0–P4 (kwiecień 2026) — WSZYSTKIE UKOŃCZONE

| ID | Zadanie | Status | Szczegóły |
|---|---|---|---|
| **P0** | Rozszerzenie Java GT do n≥50 | ✅ ZROBIONE | n=59, commit b336496 |
| **P1** | Jolak cross-validation | ✅ ZROBIONE | 4/5 POTWIERDZONE |
| **P2** | Badanie god_class_ratio | ✅ ZROBIONE | Nie dodajemy do formuły |
| **P3** | Analiza false-negative Django | ✅ ZROBIONE | Potrzeba lepszego wykrywania, deferred |
| **P4** | Re-run Java-S na rozszerzonym GT | ✅ ZROBIONE | v3c POTWIERDZONE, S monotonicity broken |

---

## Szczegóły ukończonych zadań

### P0 — Rozszerzenie Java GT do n≥50 ✅

**Cel:** Zwiększenie Java Ground Truth z n=29 do n≥50, żeby wyniki statystyczne były wiarygodniejsze.

**Wykonane:**
- Przeskanowano 30 nowych kandydatów
- Panel ekspertów ocenił wszystkie 30 (wynik: 16 POS, 14 NEG)
- Połączono z oryginalnym GT (n=29) → expanded GT (n=59)
- Statystyki po rozszerzeniu: MW p=0.0002, Spearman ρ=0.380, partial_r=0.447, AUC=0.767
- Gap zawęził się: 0.115 → 0.085 (oczekiwane przy większej różnorodności)
- Wszystkie testy istotności pozostały p<0.01 ✓

**Commit:** b336496

### P1 — Jolak cross-validation ✅

**Cel:** Niezależna walidacja skanera Java na 8 repozytoriach z zewnętrznego badania Jolak et al. (2025).

**Wykonane:**
- Zbudowano czysty Python Java scanner (tree-sitter-java)
- Naprawiono krytyczny bug granulacji (poziom pakietu → poziom pliku)
- Przeskanowano 8/8 repozytoriów
- Wyniki: średnia AGQ v3c = 0.535 (pomiędzy GT-POS=0.585 a GT-NEG=0.470 — oczekiwane)
- **4/5 wyników Jolak POTWIERDZONE, 1 PRAWDOPODOBNE**

### P2 — Badanie god_class_ratio ✅

**Cel:** Sprawdzić czy god_class_ratio (% klas z LCOM4 > próg) poprawia dyskryminację GT.

**Wynik:** Nie dodajemy do formuły. Brak wystarczającego uzasadnienia dla nowej metryki (niezmiennik N4). Istniejące metryki dostatecznie pokrywają wymiar spójności przez LCOM4 per klasa.

### P3 — Analiza false-negative Django ✅

**Cel:** Zrozumieć dlaczego Django dostaje NEG mimo uznanej dobrej architektury.

**Wynik:**
- Przyczyna: skaner wymaga lepszego wykrywania wewnątrz-pakietowego (intra-package detection)
- Django używa głęboko zagnieżdżonych `__init__.py` jako fasad — skaner nie śledzi tych zależności
- Deferred — nie blokuje głównej linii badań

### P4 — Re-run Java-S na rozszerzonym GT ✅

**Cel:** Sprawdzić, czy wagi v3c (equal 0.20) są optymalne na rozszerzonym GT (n=59).

**Wykonane:**
- Przetestowano 18 wariantów wag na expanded GT (n=59)
- **v3c (equal 0.20) POTWIERDZONE jako zwycięzca** — żaden wariant nie wychodzi poza bootstrap CI
- **S monotonicity ZŁAMANA** na n=59: ρ=0.00 (była 1.00 na n=29)
- Krzywa S ma kształt odwróconego U — peak przy S=0.20
- Split-half: WSZYSTKIE warianty niestabilne (Δ>0.15) — krajobraz płaski [0.40, 0.49]
- CI zawężone 40% (0.55→0.33) ale zbyt szerokie do rozróżnienia wariantów
- Rekomendacja: **zamknąć optymalizację wag, v3c jest wystarczająco dobre**
- Wariant rezerwowy: C_boost (M10/A10/S20/C30/CD30) — partial_r=0.484, w CI v3c

**Commit:** 5566912

**Dodatkowe odkrycia (Strict Protocol GT n=38):**
- Filtry: panel≥7.0/≤3.5, σ<2.0, 100≤nodes≤5000 → n=38 (20 POS, 18 NEG)
- Silniejsze wyniki: partial_r=0.507 (p=0.001), MW p=0.0004
- C najsilniejsza: partial_r=0.571 (p=0.0002)
- S istotna na strict GT: partial_r=0.410 (p=0.011)

---

## Obecna faza: wdrożenie i pilotaż

### Ukończone deliverables (kwiecień 2026)

| Deliverable | Status | Opis |
|---|---|---|
| Test Architecture v1 Spec | ✅ | Specyfikacja systemu testów: progi, fitness functions, pipeline |
| qse-archtest CLI | ✅ | Narzędzie CLI: skan → AGQ → green/amber/red + insights |
| GitHub Action | ✅ | Reusable action + 6 wzorców użycia |
| Pilot Plan Template | ✅ | Szablon pilotażu: OSS + internal |
| Claims & Evidence v3.0 | ✅ | 14 claims z kwalifikacjami i dowodami |
| Threats to Validity v3.0 | ✅ | Nowe: IV-06 (S monotonicity), SC-07 (strict protocol) |

### Aktualny priorytet: pilotaż qse-archtest

**Pilot 1 — Before/After refactoring** ✅ ZAKOŃCZONY (kwiecień 2026):
- Repo: `colinbut/monolith-enterprise-application` (fork → `PiotrGry/qse-pilot-enterprise`)
- Baseline: AGQ=0.574 GREEN, Expert Panel=3.0/10 (NEG) → **BLIND SPOT**
- Refactoring: 19 plików, +451/-129 linii (clean DIP, port/adapter, god class→composition)
- Po refactoringu: AGQ=0.576 GREEN → **delta = +0.002 (w granicach szumu)**
- Kluczowy wniosek: S nie reaguje na zmianę kierunków zależności, blind spot nierozwiązany
- Szczegóły: [[Pilot OSS]]

**Następne kroki pilotażu:**
1. Multi-repo scan na repozytoriach spoza GT (rozkład statusów, false positive rate)
2. Investigation: alternatywna metryka dependency-direction dla S
3. Investigation: detection of "fake layering" (interface/impl without real separation)

---

## Planowane badania (bez terminu)

| Badanie | Opis | Dlaczego nie teraz |
|---|---|---|
| **Kalibracja wag per język** | Osobna kalibracja dla Javy i Go | Obecna tylko na OSS-Python (n=74). Java i Go mogą wymagać innych wag. |
| **Warstwa Predictor** | Model ML do predykcji ryzyka utrzymaniowego | Wymaga osobnego datasetu z etykietami procesowymi. Konceptualnie odrębne od AGQ. |
| **Walidacja na projektach przemysłowych** | Czy wyniki z OSS generalizują się na closed-source? | Cały benchmark to open-source. Potrzeba dostępu do projektów komercyjnych. |
| **Expert labeling** | Ocena projektów przez prawdziwych architektów oprogramowania | Pilotaż planowany. |
| **Temporal AGQ** | Analiza driftu architektury przez historię git, per commit | Wymaga parsowania historii commitów. |
| **Normalizacja kategorii projektu** | Osobne normy dla utility libraries, aplikacji, platform | Utility libraries (Guava) mają inną „właściwą" architekturę niż aplikacje domenowe. |

> 🔴 **Warstwa Predictor nie istnieje w obecnej wersji systemu.** To planowany kierunek badawczy, nie zaplanowana funkcja do wdrożenia w konkretnym terminie.

---

## Definicja formalna — status badań

```
Stan walidacji AGQ (kwiecień 2026):

Java v3c:
  n=59 · MW p=0.000221 · AUC=0.767 · Jolak 4/5 ✓
  P4 complete: v3c confirmed, S monotonicity broken
  Strict GT (n=38): partial_r=0.507, MW p=0.0004
  Status: WYSOKA ISTOTNOŚĆ STATYSTYCZNA, FORMUŁA ZAMROŻONA

Python v3c:
  n=30 · flat_score dominuje (waga 0.35)
  God-module metryki: kierunek poprawny, ns (p>0.10)
  Status: WSTĘPNA WALIDACJA — wymaga rozszerzenia

Go:
  Brak GT · cohesion=1.0 strukturalne · 0% cykli
  Status: BRAK WALIDACJI

Cross-language:
  Brak korelacji AGQ vs SonarQube (n=78, p>0.10)
  r=+0.236 AGQ-adj vs hotspot_ratio (n=234, p<0.001)
  Status: POTWIERDZONE KORELACJE PROCESOWE (umiarkowane)
```

---

## Zobacz też
[[Ground Truth]] · [[Invariants]] · [[Experiments Index]] · [[Hypotheses Register]] · [[Architecture]]
