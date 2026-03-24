# AGQ Thesis Benchmark on 15 OSS Repos

- generated_at: `2026-03-06T23:12:36.284980+00:00`
- repos_target: `15`
- repos_with_agq: `15`
- repos_with_sonar: `15`

## Thesis Checks

| ID | Thesis | Result | Evidence |
|---|---|---|---|
| T1 | AGQ deterministic over repeated runs | PASS | max_score_delta=0.0000000000 (target <= 1e-9) |
| T2 | AGQ correlates stronger with defect proxy than Sonar maintainability | PASS | predictor=code_smell_quality_score; |r(AGQ,defect_proxy)|=0.0458 vs |r(Sonar,defect_proxy)|=0.0176 |
| T3 | Complementarity: Sonar A but low AGQ exists | PASS | cases=14 (httpx, requests, urllib3, flask, click, jinja, werkzeug, pydantic, pyjwt, rich, aiohttp, pytest, sanic, scrapy) |
| T4 | AGQ median runtime is lower than SonarQube median runtime | PASS | median_agq_s=0.156 vs median_sonar_s=14.012 |
| T5 | AGQ discriminates quality across heterogeneous repos | PASS | spread=0.1509, stddev=0.0427 |

## Correlations

- sonar predictor used: `code_smell_quality_score`
- pearson(AGQ, defect_proxy): `-0.0458`
- pearson(SonarPredictor, defect_proxy): `0.0176`
- spearman(AGQ, SonarPredictor): `-0.1107`

## Repo Results

| Repo | AGQ(mean) | AGQ(delta) | Sonar Maint | Bugs | Vulns | Smells | Defect proxy | AGQ time(s) | Sonar time(s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| httpx | 0.6098 | 0.000000 | A | 8 | 3 | 171 | 0.0952 | 0.103 | 12.673 |
| requests | 0.6379 | 0.000000 | A | 0 | 0 | 107 | 0.1081 | 0.043 | 12.186 |
| urllib3 | 0.6047 | 0.000000 | A | 4 | 25 | 259 | 0.1382 | 0.125 | 13.601 |
| flask | 0.5577 | 0.000000 | A | 7 | 0 | 99 | 0.1213 | 0.067 | 12.733 |
| click | 0.5718 | 0.000000 | A | 0 | 0 | 200 | 0.1688 | 0.156 | 12.899 |
| jinja | 0.6548 | 0.000000 | A | 95 | 0 | 171 | 0.1486 | 0.295 | 13.163 |
| werkzeug | 0.6308 | 0.000000 | A | 7 | 0 | 311 | 0.0767 | 0.237 | 14.012 |
| pydantic | 0.6798 | 0.000000 | A | 44 | 0 | 1825 | 0.1848 | 0.675 | 20.974 |
| fastapi | 0.7086 | 0.000000 | A | 3 | 0 | 766 | 0.0575 | 0.145 | 18.563 |
| pyjwt | 0.6283 | 0.000000 | A | 2 | 4 | 57 | 0.1926 | 0.082 | 11.911 |
| rich | 0.6378 | 0.000000 | A | 20 | 0 | 413 | 0.1971 | 0.372 | 15.054 |
| aiohttp | 0.5758 | 0.000000 | A | 18 | 1 | 700 | 0.1367 | 0.433 | 17.155 |
| pytest | 0.6667 | 0.000000 | A | 33 | 0 | 1041 | 0.1423 | 0.000 | 17.684 |
| sanic | 0.6863 | 0.000000 | A | 35 | 0 | 464 | 0.1910 | 0.208 | 15.470 |
| scrapy | 0.6626 | 0.000000 | A | 87 | 10 | 882 | 0.1040 | 0.279 | 16.894 |

