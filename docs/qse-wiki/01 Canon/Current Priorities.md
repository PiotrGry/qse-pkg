---
type: canon
language: pl
---

# Aktualne priorytety

## Prostymi słowami

To jest lista „co robimy teraz i co jest następne". Priorytety są numerowane P0–P4 — P0 to było najważniejsze (już zrobione), P4 to następny konkretny krok. Poza nimi jest lista planowanych badań bez terminu.

---

## Szczegółowy opis

### Status zadań P0–P4 (kwiecień 2026)

| ID | Zadanie | Status | Szczegóły |
|---|---|---|---|
| **P0** | Rozszerzenie Java GT do n≥50 | ✅ ZROBIONE | n=59, commit b336496 |
| **P1** | Jolak cross-validation | ✅ ZROBIONE | 4/5 POTWIERDZONE |
| **P2** | Badanie god_class_ratio | ✅ ZROBIONE | Nie dodajemy do formuły |
| **P3** | Analiza false-negative Django | ✅ ZROBIONE | Potrzeba lepszego wykrywania, deferred |
| **P4** | Re-run Java-S na rozszerzonym GT | ⏳ NASTĘPNY KROK | Odblokowany przez P0 |

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

---

## P4 — Re-run Java-S na rozszerzonym GT (NASTĘPNY KROK)

**Cel:** Sprawdzić, czy konfiguracja wag z eksperymentu Java-S (znaleziona na n=29) jest optymalna też na n=59. Możliwe że rozszerzone GT ujawni lepszy wariant wag lub potwierdzi v3c z równymi wagami 0.20.

**Status:** ⏳ Zablokowany przez P0 → teraz odblokowany

**Protokół:**
- Maksymalnie 5 iteracji (niezmiennik N7)
- Stop po 2 kolejnych iteracjach bez poprawy
- Walidacja na Jolak (niezależny zbiór) po każdej iteracji
- Brak modeli nieliniowych (niezmiennik N5)
- Brak brute-force (niezmiennik N6)

**Konfiguracja startowa:** v3c z równymi wagami 0.20 (M, A, S, C, CD) — wygrała na n=29.

---

## Planowane badania (bez terminu)

| Badanie | Opis | Dlaczego nie teraz |
|---|---|---|
| **Kalibracja wag per język** | Osobna kalibracja dla Javy i Go | Obecna tylko na OSS-Python (n=74). Java i Go mogą wymagać innych wag. |
| **Warstwa Predictor** | Model ML do predykcji ryzyka utrzymaniowego | Wymaga osobnego datasetu z etykietami procesowymi. Konceptualnie odrębne od AGQ. |
| **Walidacja na projektach przemysłowych** | Czy wyniki z OSS generalizują się na closed-source? | Cały benchmark to open-source. Potrzeba dostępu do projektów komercyjnych. |
| **Expert labeling** | Ocena projektów przez prawdziwych architektów oprogramowania | Pilotaż planowany. |
| **Temporal AGQ** | Analiza driftu architektury przez historię git, per commit | Wymaga parsowania historii commitów. |
| **Cykl życia naruszenia** | Jak długo żyje naruszenie architektoniczne zanim zostanie naprawione? | Wymaga longitudinalnego badania na dużym zbiorze. |
| **Normalizacja kategorii projektu** | Osobne normy dla utility libraries, aplikacji, platform | Utility libraries (Guava) mają inną „właściwą" architekturę niż aplikacje domenowe. |

> 🔴 **Warstwa Predictor nie istnieje w obecnej wersji systemu.** To planowany kierunek badawczy, nie zaplanowana funkcja do wdrożenia w konkretnym terminie.

---

## Definicja formalna — status badań

```
Stan walidacji AGQ (kwiecień 2026):

Java v3c:
  n=59 · MW p=0.000221 · AUC=0.767 · Jolak 4/5 ✓
  Status: WYSOKA ISTOTNOŚĆ STATYSTYCZNA

Python v3c:
  n=30 · flat_score dominuje (waga 0.35)
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
