# QSE-PKG — Mapa dokumentów
**Aktualizacja:** 2026-03-23
**Zasada:** ★★★ = source of truth | ★★☆ = pomocniczy/aktualny | ★☆☆ = archiwalny

---

## 1. Dokumenty grantowe

| Ścieżka | Wartość | Uwagi |
|---------|---------|-------|
| `artifacts/grant_preview_pl.md` | ★★★ SoT | Główny wniosek PL, zaudytowany, n=240 |
| `artifacts/grant_wp_milestones.md` | ★★★ SoT | WP/milestones 70/30 BI/PR |
| `artifacts/wniosek_verification_2026-03-23.md` | ★★★ SoT | Raport weryfikacyjny: 4 błędy, 4 ostrzeżenia, 13 OK |
| `artifacts/references.md` | ★★★ SoT | 14 kategorii, ~50 pozycji |
| `artifacts/archive/grant_description.md` | ★☆☆ ARCHIWUM | n=127, en, superseded |
| `artifacts/archive/grant_consolidated_pl.md` | ★☆☆ ARCHIWUM | n=237, niespójny |

---

## 2. Benchmarki — SOURCE OF TRUTH

| Ścieżka | Uwagi |
|---------|-------|
| `benchmark/agq_enhanced_python80.json` + `.md` | ★★★ Python-80, AGQ Enhanced, fingerprints |
| `benchmark/agq_enhanced_java80.json` + `.md` | ★★★ Java-79, AGQ Enhanced |
| `benchmark/agq_enhanced_go80.json` + `.md` | ★★★ Go-81, AGQ Enhanced |
| `benchmark/agq_weight_calibration.json` | ★★★ Kalibracja wag L-BFGS-B |
| `benchmark/agq_correlation_breakdown.json` | ★★★ Korelacje cross-language n=234 |

---

## 3. Benchmarki — WALIDACJA

| Ścieżka | Uwagi |
|---------|-------|
| `benchmark/known_good_bad_validation.json` + `.md` | ★★★ p<0.001, d=3.22 |
| `benchmark/sonar_vs_agq_validation.json` + `.md` | ★★★ SonarQube n=79, orthogonal |
| `benchmark/dai_et_al_comparison.json` + `.md` | ★★★ 4/4 Java, rho=1.0 |
| `benchmark/emerge_vs_qse_comparison.json` + `.md` | ★★★ Emerge cross-val n=16 |
| `benchmark/extended_metrics_normalized.json` | ★★★ Size-normalized 240 repo × 3 languages |
| `benchmark/extended_metrics_benchmark.json` + `.md` | ★★★ CCD, IC, fan-out Python-80 |
| `benchmark/extended_metrics_java.json` | ★★★ Extended metrics Java-79 |
| `benchmark/extended_metrics_go.json` | ★★★ Extended metrics Go-81 |

---

## 4. Benchmarki — POMOCNICZE

| Ścieżka | Uwagi |
|---------|-------|
| `benchmark/agq_churn_analysis_v3.json` + `.md` | ★★☆ Ostatnia iteracja churn vs AGQ |
| `benchmark/agq_cochange_entropy.json` + `.md` | ★★☆ Co-change entropy |
| `benchmark/agq_oss80_ground_truth.json` + `.md` | ★★☆ Ground truth Python-80 |
| `benchmark/agq_oss80_full.json` + `.md` | ★★☆ Pełne dane OSS-80 |
| `benchmark/agq_spaghetti_v3.json` + `.md` | ★★☆ Patologiczne cases |

Starsze wersje → `benchmark/archive/` (51 plików: thesis_v1-v4, 240_*, full_*, oss30_*, churn_v1/v2, spaghetti_oss, go20, java30)

---

## 5. Materiały komunikacyjne

| Ścieżka | Uwagi |
|---------|-------|
| `artifacts/qse_podrecznik.md` + `.pdf` | ★★☆ Podręcznik techniczny |
| `artifacts/qse_brief_naukowy.md` + `.pdf` | ★★☆ Brief 1-stronicowy |
| `artifacts/qse_ulotka.md` + `.pdf` | ★★☆ One-pager |

---

## 6. Raporty badawcze

| Ścieżka | Uwagi |
|---------|-------|
| `papiers/PILOT_RESULTS_FINAL.md` | ★★☆ Wyniki pilotu v3.1 |
| `papiers/s41598-025-31209-5.pdf` | ★★☆ Published research paper |
| `papiers/sources/*.pdf` | ★★☆ Referencyjne artykuły naukowe |
| `papiers/archive/RAPORT_NAUKOWY_BR.md` | ★☆☆ ARCHIWUM — DDD/T_ddd |
| `papiers/archive/FENG_BR_WNIOSKI_PILOT.md` | ★☆☆ ARCHIWUM — QSE4/T_ddd |
| `papiers/archive/PODRECZNIK_DLA_STUDENTA.*` | ★☆☆ ARCHIWUM — DDD-centric |

---

## 7. TRL4 / walidacja systemowa

| Ścieżka | Uwagi |
|---------|-------|
| `artifacts/trl4/validation.json` + `.md` | ★★★ TRL4 pass=True |
| `artifacts/trl4/heavy_benchmark.json` + `.md` | ★★☆ Heavy benchmark pass |

---

## Podsumowanie — co konsumować jako kontekst

**Autorytatywne (SoT):** `grant_preview_pl.md`, `grant_wp_milestones.md`, `references.md`, `wniosek_verification_2026-03-23.md`, `agq_enhanced_*.json`, sekcja 3 (walidacja)
**Pomocnicze:** outreach PDFs, `PILOT_RESULTS_FINAL.md`, `agq_churn_analysis_v3`
**Nie używać bez filtrowania:** wszystko w `archive/`
