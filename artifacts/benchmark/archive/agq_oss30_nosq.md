# AGQ Thesis Benchmark

- generated_at: `2026-03-07T11:37:16.953106+00:00`
- repos_target: `30`
- repos_with_agq: `30`
- repos_with_sonar: `0`

## Thesis Checks

| ID | Thesis | Result | Evidence |
|---|---|---|---|
| T1 | AGQ deterministic over repeated runs | PASS | max_score_delta=0.0000000000 (target <= 1e-9) |
| T2 | AGQ correlates stronger with defect proxy than Sonar maintainability | FAIL | insufficient data (predictor=code_smell_quality_score) |
| T3 | Complementarity: Sonar A but low AGQ exists | FAIL | cases=0 (none) |
| T4 | AGQ median runtime is lower than SonarQube median runtime | FAIL | median_agq_s=0.166 vs median_sonar_s=n/a |
| T5 | AGQ discriminates quality across heterogeneous repos | PASS | spread=0.2840, stddev=0.0560 |

## Correlations

- sonar predictor used: `code_smell_quality_score`
- pearson(AGQ, defect_proxy): `n/a`
- pearson(SonarPredictor, defect_proxy): `n/a`
- spearman(AGQ, SonarPredictor): `n/a`

## Repo Results

| Repo | AGQ(mean) | AGQ(delta) | Sonar Maint | Bugs | Vulns | Smells | Defect proxy | AGQ time(s) | Sonar time(s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| httpx | 0.6098 | 0.000000 | n/a | n/a | n/a | n/a | 0.0952 | 0.108 | n/a |
| requests | 0.6379 | 0.000000 | n/a | n/a | n/a | n/a | 0.1081 | 0.046 | n/a |
| flask | 0.5577 | 0.000000 | n/a | n/a | n/a | n/a | 0.1213 | 0.069 | n/a |
| click | 0.5718 | 0.000000 | n/a | n/a | n/a | n/a | 0.1688 | 0.160 | n/a |
| pydantic | 0.6798 | 0.000000 | n/a | n/a | n/a | n/a | 0.1838 | 0.674 | n/a |
| fastapi | 0.7086 | 0.000000 | n/a | n/a | n/a | n/a | 0.0575 | 0.144 | n/a |
| rich | 0.6378 | 0.000000 | n/a | n/a | n/a | n/a | 0.1971 | 0.368 | n/a |
| pytest | 0.6667 | 0.000000 | n/a | n/a | n/a | n/a | 0.1423 | 0.000 | n/a |
| sanic | 0.6863 | 0.000000 | n/a | n/a | n/a | n/a | 0.1910 | 0.207 | n/a |
| scrapy | 0.6626 | 0.000000 | n/a | n/a | n/a | n/a | 0.1040 | 0.277 | n/a |
| urllib3 | 0.6047 | 0.000000 | n/a | n/a | n/a | n/a | 0.1382 | 0.125 | n/a |
| aiohttp | 0.5758 | 0.000000 | n/a | n/a | n/a | n/a | 0.1367 | 0.429 | n/a |
| django | 0.7113 | 0.000000 | n/a | n/a | n/a | n/a | 0.0025 | 2.355 | n/a |
| starlette | 0.6619 | 0.000000 | n/a | n/a | n/a | n/a | 0.0891 | 0.126 | n/a |
| celery | 0.6471 | 0.000000 | n/a | n/a | n/a | n/a | 0.1750 | 0.438 | n/a |
| tornado | 0.6738 | 0.000000 | n/a | n/a | n/a | n/a | 0.1091 | 1.784 | n/a |
| typer | 0.6302 | 0.000000 | n/a | n/a | n/a | n/a | 0.0325 | 0.060 | n/a |
| arrow | 0.6887 | 0.000000 | n/a | n/a | n/a | n/a | 0.2174 | 0.461 | n/a |
| pendulum | 0.6719 | 0.000000 | n/a | n/a | n/a | n/a | 0.3134 | 0.076 | n/a |
| httpcore | 0.6653 | 0.000000 | n/a | n/a | n/a | n/a | 0.1389 | 0.086 | n/a |
| attrs | 0.8417 | 0.000000 | n/a | n/a | n/a | n/a | 0.1132 | 0.001 | n/a |
| marshmallow | 0.6560 | 0.000000 | n/a | n/a | n/a | n/a | 0.1141 | 0.140 | n/a |
| ansible | 0.6134 | 0.000000 | n/a | n/a | n/a | n/a | 0.2325 | 2.286 | n/a |
| salt | 0.7522 | 0.000000 | n/a | n/a | n/a | n/a | 0.2406 | 2.705 | n/a |
| home-assistant | 0.6173 | 0.000000 | n/a | n/a | n/a | n/a | 0.1100 | 20.126 | n/a |
| airflow | 0.6211 | 0.000000 | n/a | n/a | n/a | n/a | 0.2400 | 14.151 | n/a |
| thefuck | 0.7194 | 0.000000 | n/a | n/a | n/a | n/a | 0.0000 | 0.048 | n/a |
| you-get | 0.6057 | 0.000000 | n/a | n/a | n/a | n/a | 0.2895 | 0.172 | n/a |
| youtube-dl | 0.6437 | 0.000000 | n/a | n/a | n/a | n/a | 0.2281 | 2.097 | n/a |
| glances | 0.6803 | 0.000000 | n/a | n/a | n/a | n/a | 0.1005 | 0.152 | n/a |

