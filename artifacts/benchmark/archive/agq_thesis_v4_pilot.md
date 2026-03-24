# AGQ Thesis Benchmark

- generated_at: `2026-03-07T23:27:36.401223+00:00`
- repos_target: `10`
- repos_with_agq: `10`
- repos_with_sonar: `10`

## Thesis Checks

| ID | Thesis | Result | Evidence |
|---|---|---|---|
| T1 | AGQ deterministic over repeated runs | PASS | max_score_delta=0.0000000000 (target <= 1e-9) |
| T2 | AGQ predicts code churn hotspots better than Sonar (hotspot_ratio) | FAIL | |r_s(AGQ,hotspot_ratio)|=0.3818 vs |r_s(Sonar,hotspot_ratio)|=0.3818 (n=10); r_s(AGQ,churn_gini)=-0.4545 |
| T3 | Complementarity: Sonar A but AGQ below mean-0.5*std exists | PASS | threshold=0.643 (mean=0.720 - 0.5*std=0.077); cases=3 (flask, aiohttp, ansible) |
| T4 | AGQ median runtime is lower than SonarQube median runtime | PASS | median_agq_s=0.360 vs median_sonar_s=17.309 |
| T5 | AGQ discriminates quality across heterogeneous repos | PASS | spread=0.5426, stddev=0.1542 |

## Correlations

- sonar predictor used: `code_smell_quality_score`
- pearson(AGQ, bugfix_ratio): `-0.1878`
- pearson(Sonar, bugfix_ratio): `-0.1997`
- spearman(AGQ, Sonar): `-0.2848`
- spearman(AGQ, hotspot_ratio): `-0.3818` (Sonar: `-0.3818`) n=10
- spearman(AGQ, churn_gini): `-0.4545` (Sonar: `-0.3455`)

## Repo Results

| Repo | AGQ(mean) | AGQ(delta) | Sonar Maint | Bugs | Smells | Bugfix% | Hotspot% | Churn Gini | AGQ time(s) | Sonar time(s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| flask | 0.4574 | 0.000000 | A | 7 | 99 | 0.1213 | 0.1667 | 0.4921 | 0.070 | 12.809 |
| requests | 0.6843 | 0.000000 | A | 0 | 107 | 0.1081 | 0.2353 | 0.4544 | 0.045 | 12.074 |
| django | 0.8419 | 0.000000 | A | 85 | 4314 | 0.0000 | 0.0111 | 0.0671 | 2.432 | 52.601 |
| attrs | 1.0000 | 0.000000 | A | 57 | 185 | 0.1100 | 0.0800 | 0.3436 | 0.001 | 12.578 |
| pandas | 0.7191 | 0.000000 | A | 988 | 4895 | 0.4700 | 0.0933 | 0.2476 | 7.054 | 59.249 |
| fastapi | 0.8235 | 0.000000 | A | 3 | 766 | 0.0500 | 0.0095 | 0.0448 | 0.153 | 18.485 |
| pygments | 0.7645 | 0.000000 | A | 13 | 1137 | 0.2267 | 0.0028 | 0.0700 | 1.177 | 17.601 |
| aiohttp | 0.4971 | 0.000000 | A | 18 | 700 | 0.1200 | 0.0357 | 0.2697 | 0.437 | 17.017 |
| scrapy | 0.7808 | 0.000000 | A | 87 | 882 | 0.1329 | 0.0973 | 0.4098 | 0.283 | 16.935 |
| ansible | 0.6288 | 0.000000 | A | 42 | 2654 | 0.3300 | 0.0307 | 0.1232 | 2.293 | 34.989 |

