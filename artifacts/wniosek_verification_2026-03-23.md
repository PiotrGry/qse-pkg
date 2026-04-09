# Weryfikacja wniosku grantowego QSE vs kod

**Data weryfikacji:** 2026-03-23
**Plik wniosku:** `/home/pepus/dev/uni_grant_mvp/wniosek_export_2026-03-22.txt`
**Metoda:** Każde twierdzenie techniczne sprawdzone grep/read w kodzie QSE i artifacts/benchmark/*.json

---

## ❌ BŁĘDY (do poprawienia przed złożeniem)

### 1. Fingerprint: 4 archetypów → 8
**Lokalizacja:** Cecha 3, linia 65
**Tekst:** "jeden z czterech archetypów: LAYERED, FLAT, LOW_COHESION lub MODULAR"
**Stan w kodzie:** `qse/agq_enhanced.py` definiuje 8 typów: CLEAN, LAYERED, MODERATE, FLAT, LOW_COHESION, TANGLED, CYCLIC, UNKNOWN
**Problem:** "MODULAR" nie istnieje w kodzie. Sekcja "Opis innowacji" (linia 52) wymienia poprawnie 3 typy - niespójność wewnętrzna wniosku.
**Fix:** Zmienić na "jeden z ośmiu archetypów, m.in. LAYERED, FLAT, LOW_COHESION, CYCLIC" lub wymienić wszystkie 8.

### 2. Rust jako analizowany język
**Lokalizacja:** Cecha 4, linia 69
**Tekst:** "repozytoria pisane w Rust, Pythonie, Javie i Go"
**Stan w kodzie:** `qse-core/src/scanner/universal.rs` - enum Language { Python, Java, Go }. Brak Rust.
**Problem:** Rust to język w którym scanner jest **napisany** (tree-sitter bindings), nie który **analizuje**.
**Fix:** "repozytoria pisane w Pythonie, Javie i Go"

### 3. Emerge "przede wszystkim Python"
**Lokalizacja:** Cecha 4, linia 69
**Tekst:** "Emerge - obsługuje przede wszystkim ekosystem Pythona"
**Stan faktyczny:** Emerge v2.0.7 obsługuje 12 języków: C, C++, Groovy, Java, JavaScript, TypeScript, Kotlin, Objective-C, Ruby, Swift, Python, Go.
**Źródło:** https://github.com/glato/emerge + nasza weryfikacja (cross-validation n=16)
**Fix:** "Emerge oblicza pojedynczą metrykę Louvain Q i fan-in/fan-out na grafie zależności, lecz nie oferuje kalibrowanego composite score, klasyfikacji topologicznej ani mechanizmu ratchetingu."

### 4. Wagi AGQ: 0.07 i 0.03 nie zgadzają się
**Lokalizacja:** Metoda badawcza, linia 31
**Tekst:** "Acyclicity (0,73), Cohesion (0,17), Stability (0,07) i Modularity (0,03)"
**Stan w kodzie:** `qse/graph_metrics.py` linia 360: "Calibrated churn-optimal: (0.0, 0.73, 0.05, 0.17)"
Kolejność w kodzie: (modularity=0.0, acyclicity=0.73, stability=0.05, cohesion=0.17)
**Problem:** Stability = 0.05 (nie 0.07). Modularity = 0.00 (nie 0.03). To zaokrąglenie zmienia sens - modularity ma wagę ZERO.
**Fix:** "Acyclicity (0,73), Cohesion (0,17), Stability (0,05) i Modularity (0,00)"
Uwaga: modularity=0 w kalibracji to ciekawy wynik (sam Louvain Q nie predykuje churn) - warto to obrócić jako argument za composite score.

---

## ⚠️ WYMAGAJĄ UWAGI (nie błędy faktyczne, ale ryzyko)

### 5. "Zero false regressions" - nierealistyczne KPI
**Lokalizacja:** Cecha 2, linia 61
**Tekst:** "brak fałszywych blokad (zero false regressions)"
**Problem:** Każdy system bramkowy ma false positives. KPI "zero" jest nieosiągalny i komisja to wie.
**Sugestia:** "false regression rate < 5%" lub "precision ≥ 95%"

### 6. "Wartość bazowa: 1 język (Python, POC)"
**Lokalizacja:** Opis innowacji, linia 52
**Tekst:** "liczba obsługiwanych języków - wartość bazowa: 1 (Python, POC), wartość docelowa: 3"
**Stan w kodzie:** Rust scanner (`qse-core`) już obsługuje Python, Java, Go. Benchmark 240 repo × 3 języki istnieje.
**Problem:** POC obsługuje 3 języki, nie 1. Zaniżanie bazowej wartości.
**Sugestia:** "wartość bazowa: 3 (Python, Java, Go - POC), wartość docelowa: 3 z pełną walidacją enterprise"

### 7. rho=1.0 bez podania n
**Lokalizacja:** Opis innowacji, linia 52
**Tekst:** "rho=1,0 na próbie pilotażowej"
**Stan faktyczny:** rho=1.0 na n=4 (Dai et al. - Apache Ant, JDT, Camel, Hadoop). p=0.083 (NIE istotne statystycznie).
**Problem:** Bez n i p wygląda na silniejszy wynik niż jest.
**Sugestia:** "rho=1,0 na próbie pilotażowej n=4 (p=0,08 - kierunkowo zgodne, lecz wymagające walidacji na większej próbie)"

### 8. "r = 0,23 korelacja z zewnętrznymi ocenami jakości"
**Lokalizacja:** Problem badawczy, linia 16
**Tekst:** "korelacja AGQ z zewnętrznymi ocenami jakości"
**Stan faktyczny:** r=0.236 to korelacja AGQ-adj vs hotspot_ratio (churn proxy), nie "oceny jakości" sensu stricto.
**Problem:** Hotspot ratio to proxy dla maintenance cost, nie bezpośrednia ocena jakości przez ekspertów.
**Sugestia:** "korelacja AGQ z proxy metrykami procesowymi (hotspot ratio)" - uczciwe i nadal mocne.

---

## ✅ POPRAWNE (zweryfikowane w kodzie/danych)

| Twierdzenie | Źródło weryfikacji |
|---|---|
| AGQ = 4 składowe (acyclicity, cohesion, stability, modularity) | `qse/graph_metrics.py:26-31` |
| SonarQube nie mierzy topologii grafu zależności | Potwierdzone - Sonar mierzy per-file metrics |
| Benchmark 240 repo (Python-80, Java-79, Go-81) | `artifacts/benchmark/agq_enhanced_*.json` |
| p<0.001, d=3.22 (known-good vs known-bad) | `artifacts/benchmark/known_good_bad_validation.json` |
| stability↔bugs/KLOC r=-0.32, p=0.003 (SonarQube n=79) | `artifacts/benchmark/sonar_vs_agq_validation.json` |
| Deterministyczność delta=0.000 | Potwierdzone w benchmarku |
| Mediana analizy 0.32s | Potwierdzone w benchmarku |
| L-BFGS-B + LOO-CV kalibracja | `artifacts/benchmark/agq_weight_calibration.json` |
| Ratcheting istnieje w kodzie | `qse/cli.py:366-377`, `.github/workflows/qse-gate.yml` |
| SaaS/API model B2B | Architektura CLI + API, GH Actions workflow |
| Composite score > pojedyncza metryka | Emerge Q r=0.06 vs AGQ, cross-validation potwierdza |
| Dai et al. ranking agreement | `artifacts/benchmark/dai_et_al_comparison.json` |
| Fingerprint 80% good=LAYERED | `artifacts/benchmark/known_good_bad_validation.json` |

---

## Nowe treści do rozważenia (nie we wniosku, a mogłyby wzmocnić)

1. **Extended metrics** (CCD, IC, fan-out) - benchmark 240 repo, fan_out_std/log(n) cross-language istotne (r=+0.13, p=0.048). Dane w `extended_metrics_normalized.json`.
2. **Size normalization** - confound rozmiaru udokumentowany i rozwiązany (per log(n)).
3. **Scanner enterprise fix** - Eclipse JDT (9267 plików Java) teraz działa po naprawie.
4. **SonarQube n=79** pełne dane z per-KLOC normalizacją (nie deklaracja, dane w repo).
