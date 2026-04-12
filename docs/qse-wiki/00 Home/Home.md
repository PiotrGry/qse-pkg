---
type: home
language: pl
---

# QSE Wiki — Quality Score Engine

> *„Możesz sprawdzić czy każda cegła jest dobra. Ale kto sprawdzi, czy budynek jest dobrze zaprojektowany?"*

**QSE (Quality Score Engine)** to otwarte narzędzie do automatycznego pomiaru jakości architektonicznej oprogramowania. Analizuje graf zależności między modułami projektu i oblicza kompozytową metrykę **AGQ** (*Architecture Graph Quality*) — liczbę w przedziale [0, 1], która mówi jak zdrowa jest struktura całego systemu.

QSE mierzy to, czego SonarQube i linters nie mierzą: **czy moduły są od siebie oddzielone, czy nie ma cyklicznych zależności, czy system ma wyraźne warstwy, czy klasy mają jedną odpowiedzialność**.

---

## Kluczowe wyniki empiryczne

| Zbiór danych | n | Kluczowe wyniki |
|---|---|---|
| Java Ground Truth (GT) | 59 repozytoriów (31 POS, 28 NEG) | MW p=0.000221 · Spearman ρ=0.380 · AUC=0.767 |
| Python Ground Truth (GT) | 30 repozytoriów (13 POS, 17 NEG) | Formuła v3c z flat_score (waga 0.35) |
| Benchmark OSS | 558 repozytoriów (351 Python, 147 Java, 30 Go, 30 TypeScript) | Korelacje, fingerprints, language bias |
| Jolak cross-validation | 8 repozytoriów | 4/5 wyników potwierdzonych, 1 prawdopodobne |

**Wagi AGQ v3c dla Javy:** `0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD`

**Wagi AGQ v3c dla Pythona:** `0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score`

---

## Nawigacja po wiki

### 00 Wstęp — dla każdego czytelnika
- [[Start Here]] — od czego zacząć, trzy ścieżki czytania
- [[What is QSE in Simple Words]] — co to jest QSE, analogie i pipeline
- [[Why QSE Exists]] — dlaczego SonarQube nie wystarcza, era AI
- [[How QSE Works Simply]] — krok po kroku z diagramami
- [[Current State in Simple Words]] — co działa, co udowodniono, co planowane

### 01 Kanon — fundament projektu
- [[QSE Canon]] — kanoniczny opis: czym QSE jest i czym nie jest
- [[Architecture]] — pięciowarstwowa architektura systemu
- [[Ground Truth]] — dane empiryczne, metodologia panelu, walidacja
- [[Scanner]] — skanery Python, Java, Rust; historia krytycznego buga
- [[Static Analysis]] — analiza statyczna w kontekście QSE
- [[Invariants]] — niezmienniki: co NIGDY się nie zmieni
- [[Current Priorities]] — priorytety P0–P4 i status
- [[What QSE Is Not]] — czym QSE nie jest

### 02 Pojęcia
- [[Dependency Graph|Graf zależności]] · [[Modularity]] · [[Acyclicity]] · [[Stability]] · [[Cohesion]] · [[CD]]

### 03 Formuły
- [[AGQ Formulas]] — wzory AGQ Core i Enhanced

### 04 Metryki
- [[AGQ Enhanced]] · [[Fingerprint]] · [[CycleSeverity]] · [[ChurnRisk]]

### 05 Eksperymenty
- [[Experiments Index]] — E1–E6 z wynikami

### 06 Hipotezy
- [[Hypotheses Register]] — W1–W10, status każdej

### 08 Słowniczek
- [[Glossary]] — 30+ pojęć z definicjami

---

## Jak czytać wiki — trzy ścieżki

### Ścieżka 1: Nowy czytelnik (student, junior developer)
Nie znasz jeszcze tematu? Zacznij tu i czytaj po kolei:

1. [[What is QSE in Simple Words]] — 5 minut, żadnego przygotowania nie trzeba
2. [[Why QSE Exists]] — po co to w ogóle
3. [[How QSE Works Simply]] — jak to działa w praktyce
4. [[Start Here]] — mapa dalszego czytania

### Ścieżka 2: Technik (senior developer, architekt)
Znasz temat, chcesz zrozumieć szczegóły:

1. [[QSE Canon]] — precyzyjna definicja
2. [[Architecture]] — architektura 5-warstwowa
3. [[AGQ Formulas]] — wzory i kalibracja
4. [[Scanner]] — jak działa skaner, znane ograniczenia
5. [[Invariants]] — co nie ulega zmianie i dlaczego

### Ścieżka 3: Badacz (PhD, senior researcher)
Chcesz zrozumieć metodologię i wyniki empiryczne:

1. [[Ground Truth]] — pełne dane GT, metodologia panelu
2. [[Hypotheses Register]] — W1–W10, co obalono, co potwierdzone
3. [[Experiments Index]] — E1–E6, protokoły i wyniki
4. [[Current Priorities]] — co jest następne
5. [[Invariants]] — ograniczenia metodologiczne

---

## Stan projektu (kwiecień 2026)

| Komponent | Status |
|---|---|
| AGQ Core (4 metryki) + AGQ Enhanced (5 wymiarów) | ✅ Zaimplementowany, 149 testów |
| Skaner Rust (Python/Java/Go), 7–46× szybszy | ✅ Działający |
| CLI: `qse agq`, `qse discover` | ✅ Działają |
| Java Ground Truth n=59 (MW p=0.000221) | ✅ Zwalidowany |
| Jolak cross-validation (4/5 potwierdzonych) | ✅ Ukończony |
| P4: Re-run Java-S na n=59 | ⏳ Następny krok |
| Warstwa Predictor | 🔬 Planowane badawczo |

---

## Instalacja i użycie

```bash
pip install git+https://github.com/PiotrGry/qse-pkg.git
qse agq /ścieżka/do/projektu
```

Wynik pojawia się w mniej niż sekundę (mediana 0.32s). Przykład:

```
AGQ = 0.571  [LAYERED]  z=+0.45  60%ile Java
  Modularity=0.668  Acyclicity=0.994  Stability=0.344  Cohesion=0.393
  CycleSeverity=NONE  ChurnRisk=LOW
```

---

## Zobacz też
[[QSE Canon]] · [[Ground Truth]] · [[AGQ Formulas]] · [[Glossary]] · [[Hypotheses Register]]
