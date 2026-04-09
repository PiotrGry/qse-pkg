# Benchmark Data - QSE AGQ

## Source of Truth (n=240: Python-80, Java-79, Go-81)
- `agq_enhanced_*.json` - per-language AGQ + fingerprints + enhanced metrics
- `agq_weight_calibration.json` - L-BFGS-B calibrated weights
- `agq_correlation_breakdown.json` - cross-language correlations (n=234)

## Validation Studies
- `known_good_bad_validation.json` - discriminant validity (p<0.001, d=3.22)
- `sonar_vs_agq_validation.json` - SonarQube orthogonality (n=79)
- `dai_et_al_comparison.json` - external ranking agreement (rho=1.0)
- `emerge_vs_qse_comparison.json` - Emerge cross-validation (n=16)
- `extended_metrics_normalized.json` - size-normalized 240 repo × 3 languages

## Archive
`archive/` - superseded benchmark iterations (thesis_v1-v4, oss30, churn_v1/v2, etc.)
