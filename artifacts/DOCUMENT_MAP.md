# QSE-PKG — Mapa dokumentów
**Wygenerowano:** 2026-03-22 (updated)
**Zasada:** ★★★ = aktywny/kluczowy | ★★☆ = pomocniczy/aktualny | ★☆☆ = przestarzały/archiwalny

---

## 1. Dokumenty grantowe

| Ścieżka | Rozmiar | Wartość | Uwagi |
|---------|---------|---------|-------|
| `artifacts/grant_preview_pl.md` | 642 linie | ★★★ KLUCZOWY | Główny wniosek PL, zaudytowany (commit 04c2f08), liczby zgodne z JSON |
| `artifacts/grant_wp_milestones.md` | 123 linie | ★★★ AKTYWNY | WP/milestones 70/30 BI/PR, marzec 2026, zatwierdzony |
| `artifacts/grant_consolidated_pl.md` | 660+ linie | ★★☆ OSTROŻNIE | Skonsolidacja grantu, n=240 zaktualizowane, walidacja + extended metrics dodane |
| `artifacts/grant_description.md` | 371 linie | ★☆☆ PRZESTARZAŁY | n=127 repo, en, superseded przez grant_preview_pl.md |

---

## 2. Raporty badawcze / B+R

| Ścieżka | Rozmiar | Wartość | Uwagi |
|---------|---------|---------|-------|
| `papiers/RAPORT_NAUKOWY_BR.md` | 2046 linie | ★☆☆ PRZESTARZAŁY | Oparty na DDD preset i QSE4 (T_ddd) — nie odzwierciedla aktualnego AGQ-centric kierunku |
| `papiers/FENG_BR_WNIOSKI_PILOT.md` | 168 linie | ★☆☆ PRZESTARZAŁY | Primary metric = QSE4 (T_ddd), domena = 10 spec DDD — wyniki nie cytowalne w kontekście AGQ |
| `papiers/PILOT_RESULTS_FINAL.md` | 141 linie | ★★☆ POMOCNICZY | Wyniki pilotu v3.1, reguła selekcji last-timestamp, 12 canonical files |
| `papiers/PODRECZNIK_DLA_STUDENTA.md` | — | ★☆☆ PRZESTARZAŁY | Tłumaczy QSE przez pryzmat DDD i T_ddd — nie odzwierciedla AGQ |

---

## 3. Materiały komunikacyjne / outreach

| Ścieżka | Rozmiar | Wartość | Uwagi |
|---------|---------|---------|-------|
| `artifacts/qse_podrecznik.md` | 1771 linie | ★★☆ POMOCNICZY | Pełny podręcznik QSE, techniczny, ma PDF |
| `artifacts/qse_brief_naukowy.md` | 74 linie | ★★☆ POMOCNICZY | Brief 1-stronicowy, ma PDF |
| `artifacts/qse_ulotka.md` | 49 linie | ★★☆ POMOCNICZY | One-pager/ulotka, ma PDF |

---

## 4. Benchmarki — AKTUALNE (referencyjne)

| Ścieżka | Wartość | Uwagi |
|---------|---------|-------|
| `artifacts/benchmark/agq_enhanced_python80.json` + `.md` | ★★★ | Python-80, AGQ Enhanced, fingerprints — REFERENCYJNY |
| `artifacts/benchmark/agq_enhanced_java80.json` + `.md` | ★★★ | Java-79, AGQ Enhanced — REFERENCYJNY |
| `artifacts/benchmark/agq_enhanced_go80.json` + `.md` | ★★★ | Go-81, AGQ Enhanced — REFERENCYJNY |
| `artifacts/benchmark/agq_weight_calibration.json` | ★★★ | Kalibracja wag L-BFGS-B (acyclicity=0.730) |
| `artifacts/benchmark/agq_correlation_breakdown.json` | ★★★ | Korelacje cross-language n=234, p-values |
| `artifacts/benchmark/agq_cochange_entropy.json` + `.md` | ★★☆ | Co-change entropy vs AGQ |

---

## 4b. Benchmarki — WALIDACJA (nowe, 2026-03-21/22)

| Ścieżka | Wartość | Uwagi |
|---------|---------|-------|
| `artifacts/benchmark/emerge_vs_qse_comparison.json` + `.md` | ★★★ | Emerge cross-validation n=16, Louvain Q r=0.06 |
| `artifacts/benchmark/known_good_bad_validation.json` + `.md` | ★★★ | Known-good vs known-bad: p<0.001, d=3.22 |
| `artifacts/benchmark/sonar_vs_agq_validation.json` + `.md` | ★★★ | SonarQube n=79: orthogonal, stability↔bugs r=-0.32 |
| `artifacts/benchmark/dai_et_al_comparison.json` + `.md` | ★★★ | Dai et al. 4/4 Java: AGQ vs arch. integrity rho=1.0 |
| `artifacts/benchmark/extended_metrics_benchmark.json` + `.md` | ★★★ | Extended metrics (CCD, IC, fan-out) Python-80 |
| `artifacts/benchmark/extended_metrics_java.json` | ★★★ | Extended metrics Java-79 |
| `artifacts/benchmark/extended_metrics_go.json` | ★★★ | Extended metrics Go-81 |
| `artifacts/benchmark/extended_metrics_normalized.json` | ★★★ | Size-normalized 240 repo × 3 languages, korelacje |

---

## 5. Benchmarki — POMOCNICZE / historyczne

| Ścieżka | Wartość | Uwagi |
|---------|---------|-------|
| `artifacts/benchmark/agq_churn_analysis_v3.json` + `.md` | ★★☆ | Ostatnia iteracja churn vs AGQ |
| `artifacts/benchmark/agq_churn_analysis_v1/v2.*` | ★☆☆ | Wcześniejsze iteracje — superseded przez v3 |
| `artifacts/benchmark/agq_oss80_ground_truth.json` + `.md` | ★★☆ | Ground truth Python-80 |
| `artifacts/benchmark/agq_oss30_ground_truth.json` + `.md` | ★☆☆ | Ground truth OSS-30 — mała próba |
| `artifacts/benchmark/agq_correlation_breakdown.md` | ★☆☆ | PRZESTARZAŁY — źródło: agq_thesis_oss80.json (n=78, 2026-03-07), superseded przez nowy JSON |
| `artifacts/benchmark/agq_spaghetti_v3.json` + `.md` | ★★☆ | Patologiczne cases, extrema architektoniczne |
| `artifacts/benchmark/agq_spaghetti_oss.json` + `.md` | ★☆☆ | Wcześniejsza wersja spaghetti |
| `artifacts/benchmark/agq_240_python80/java80/go80.*` | ★☆☆ | Superseded przez agq_enhanced_* |
| `artifacts/benchmark/agq_full_python/java/go.*` | ★☆☆ | Superseded przez agq_enhanced_* |
| `artifacts/benchmark/agq_thesis_oss80_v2/v3/v4.*` | ★☆☆ | Ewolucja metryk — wartość historyczna |
| `artifacts/benchmark/agq_thesis_oss80.json` + `.md` | ★☆☆ | v1 Python-80, archiwalne |
| `artifacts/benchmark/agq_thesis_oss15.*` | ★☆☆ | Pilot 15 repo — tylko historyczny |
| `artifacts/benchmark/agq_go20.*` | ★☆☆ | Wczesny pilot Go-20 |
| `artifacts/benchmark/agq_java30.*` | ★☆☆ | Wczesny pilot Java-30 |
| `artifacts/benchmark/agq_oss30_*.json` + `.md` | ★☆☆ | Seria OSS-30: nosq/correlation/full/gt — mała próba, archiwalne |
| `artifacts/benchmark/agq_version_comparison.md` | ★★☆ | Tylko .md, porównanie wersji AGQ — przydatny do narracji |

---

## 6. TRL4 / walidacja systemowa

| Ścieżka | Wartość | Uwagi |
|---------|---------|-------|
| `artifacts/trl4/validation.json` + `.md` | ★★★ | TRL4 pass=True, 2026-03-07 — certyfikat gotowości |
| `artifacts/trl4/heavy_benchmark.json` + `.md` | ★★☆ | Heavy benchmark pass=True, duże repo |

---

## 7. Referencje i mapa

| Ścieżka | Wartość | Uwagi |
|---------|---------|-------|
| `artifacts/references.md` | ★★★ | 14 kategorii, ~50 pozycji, zaktualizowane 2026-03-22 (Dai et al., Šora, Lakos, SAM2014, walidacja własna) |
| `artifacts/DOCUMENT_MAP.md` | ★★★ | Ten plik |

---

## 8. PDF-y (wygenerowane)

| Ścieżka | Źródło | Uwagi |
|---------|--------|-------|
| `artifacts/qse_brief_naukowy.pdf` | `qse_brief_naukowy.md` | Sync z MD? Sprawdzić |
| `artifacts/qse_ulotka.pdf` | `qse_ulotka.md` | Sync z MD? Sprawdzić |
| `artifacts/qse_podrecznik.pdf` | `qse_podrecznik.md` | Sync z MD? Sprawdzić |
| `papiers/PODRECZNIK_DLA_STUDENTA.pdf` | `PODRECZNIK_DLA_STUDENTA.md` | Sync z MD? Sprawdzić |

---

## 9. Źródła naukowe (papiers/sources/)

| Plik | Wartość | Uwagi |
|------|---------|-------|
| `ProxyWar_2602.04296.pdf` | ★★☆ | arXiv — prawdopodobnie dot. AI code evaluation |
| `EvoCodeBench_2602.10171.pdf` | ★★☆ | arXiv — benchmark ewolucji kodu |
| `AICDBench_2602.02079.pdf` | ★★☆ | arXiv — AI code generation benchmark |
| `Assessing_Quality_Security_AI_Code_2508.14727.pdf` | ★★★ | Jakość i bezpieczeństwo AI code — bezpośrednio relevantny |
| `IdeaFirstCodeLater_2601.11332.pdf` | ★★☆ | arXiv — flow AI code generation |

---

## Podsumowanie — co używać w prompcie

**Zawsze:** `grant_preview_pl.md`, `grant_wp_milestones.md`, `references.md`, `agq_enhanced_*.json`, sekcja 4b (walidacja)
**Ostrożnie:** `grant_consolidated_pl.md` (zaktualizowany, ale sprawdzić spójność z preview)
**Nie używać:** `grant_description.md` (n=127, en, archiwalne), `agq_correlation_breakdown.md` (stary, n=78)
