# AGQ Thesis Benchmark

- generated_at: `2026-03-07T11:55:17.665346+00:00`
- repos_target: `30`
- repos_with_agq: `29`
- repos_with_sonar: `29`

## Thesis Checks

| ID | Thesis | Result | Evidence |
|---|---|---|---|
| T1 | AGQ deterministic over repeated runs | PASS | max_score_delta=0.0000000000 (target <= 1e-9) |
| T2 | AGQ correlates stronger with defect proxy than Sonar maintainability | FAIL | predictor=code_smell_quality_score; |r(AGQ,defect_proxy)|=0.1763 vs |r(Sonar,defect_proxy)|=0.1825 |
| T3 | Complementarity: Sonar A but low AGQ exists | PASS | cases=24 (httpx, requests, flask, click, rich, pytest, sanic, scrapy, urllib3, aiohttp, starlette, celery, tornado, typer, arrow, pendulum, httpcore, marshmallow, ansible, home-assistant, airflow, you-get, youtube-dl, glances) |
| T4 | AGQ median runtime is lower than SonarQube median runtime | PASS | median_agq_s=0.159 vs median_sonar_s=14.304 |
| T5 | AGQ discriminates quality across heterogeneous repos | PASS | spread=0.2840, stddev=0.0568 |

## Correlations

- sonar predictor used: `code_smell_quality_score`
- pearson(AGQ, defect_proxy): `-0.1763`
- pearson(SonarPredictor, defect_proxy): `-0.1825`
- spearman(AGQ, SonarPredictor): `-0.1857`

## Repo Results

| Repo | AGQ(mean) | AGQ(delta) | Sonar Maint | Bugs | Vulns | Smells | Defect proxy | AGQ time(s) | Sonar time(s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| httpx | 0.6098 | 0.000000 | A | 8 | 3 | 171 | 0.0952 | 0.106 | 12.541 |
| requests | 0.6379 | 0.000000 | A | 0 | 0 | 107 | 0.1081 | 0.045 | 12.162 |
| flask | 0.5577 | 0.000000 | A | 7 | 0 | 99 | 0.1213 | 0.067 | 12.619 |
| click | 0.5718 | 0.000000 | A | 0 | 0 | 200 | 0.1688 | 0.157 | 12.957 |
| pydantic | 0.6798 | 0.000000 | n/a | n/a | n/a | n/a | 0.1838 | 0.685 | n/a |
| fastapi | 0.7086 | 0.000000 | A | 3 | 0 | 766 | 0.0575 | 0.149 | 18.593 |
| rich | 0.6378 | 0.000000 | A | 20 | 0 | 413 | 0.1971 | 0.379 | 14.935 |
| pytest | 0.6667 | 0.000000 | A | 33 | 0 | 1041 | 0.1423 | 0.001 | 17.548 |
| sanic | 0.6863 | 0.000000 | A | 35 | 0 | 464 | 0.1910 | 0.211 | 15.490 |
| scrapy | 0.6626 | 0.000000 | A | 87 | 10 | 882 | 0.1040 | 0.282 | 16.879 |
| urllib3 | 0.6047 | 0.000000 | A | 4 | 25 | 259 | 0.1382 | 0.123 | 13.635 |
| aiohttp | 0.5758 | 0.000000 | A | 18 | 1 | 700 | 0.1367 | 0.439 | 17.142 |
| django | 0.7113 | 0.000000 | A | 85 | 1 | 4314 | 0.0025 | 2.410 | 52.831 |
| starlette | 0.6619 | 0.000000 | A | 6 | 0 | 216 | 0.0891 | 0.125 | 12.690 |
| celery | 0.6471 | 0.000000 | A | 25 | 1 | 1260 | 0.1750 | 0.441 | 17.910 |
| tornado | 0.6738 | 0.000000 | A | 22 | 9 | 469 | 0.1091 | 1.766 | 14.449 |
| typer | 0.6302 | 0.000000 | A | 2 | 0 | 143 | 0.0325 | 0.057 | 14.206 |
| arrow | 0.6887 | 0.000000 | A | 13 | 0 | 242 | 0.2174 | 0.463 | 12.474 |
| pendulum | 0.6719 | 0.000000 | A | 163 | 0 | 149 | 0.3134 | 0.075 | 13.457 |
| httpcore | 0.6653 | 0.000000 | A | 1 | 8 | 145 | 0.1389 | 0.083 | 12.075 |
| attrs | 0.8417 | 0.000000 | A | 57 | 0 | 185 | 0.1132 | 0.001 | 12.494 |
| marshmallow | 0.6560 | 0.000000 | A | 9 | 0 | 111 | 0.1141 | 0.136 | 12.322 |
| ansible | 0.6134 | 0.000000 | A | 42 | 4 | 2654 | 0.2325 | 2.298 | 34.804 |
| salt | 0.7522 | 0.000000 | A | 112 | 18 | 10286 | 0.2406 | 2.740 | 70.439 |
| home-assistant | 0.6173 | 0.000000 | A | 85 | 2 | 14780 | 0.1100 | 20.402 | 209.177 |
| airflow | 0.6211 | 0.000000 | A | 174 | 9 | 5826 | 0.2400 | 14.295 | 103.233 |
| thefuck | 0.7194 | 0.000000 | A | 2 | 0 | 108 | 0.0000 | 0.046 | 13.363 |
| you-get | 0.6057 | 0.000000 | A | 8 | 6 | 713 | 0.2895 | 0.169 | 12.927 |
| youtube-dl | 0.6437 | 0.000000 | A | 29 | 13 | 1197 | 0.2281 | 2.122 | 29.197 |
| glances | 0.6803 | 0.000000 | A | 7 | 0 | 277 | 0.1005 | 0.159 | 14.304 |

## Failures

- `pydantic`: Command failed: docker run --rm --network host -e SONAR_HOST_URL=http://127.0.0.1:9000 -v /tmp/agq_oss_30/pydantic:/usr/src sonarsource/sonar-scanner-cli:latest sonar-scanner -Dsonar.projectKey=agq_oss_pydantic -Dsonar.projectName=agq_oss_pydantic -Dsonar.sources=. -Dsonar.inclusions=**/*.py -Dsonar.python.version=3.10 -Dsonar.sourceEncoding=UTF-8 -Dsonar.login=admin -Dsonar.password=admin -Dsonar.qualitygate.wait=true -Dsonar.qualitygate.timeout=600
stdout_tail:
11:40:14.815 WARN    * tests/test_model_signature.py
11:40:14.815 WARN    * tests/mypy/outputs/mypy-default_ini/metaclass_args.py
11:40:14.815 WARN    * pydantic-core/tests/serializers/test_any.py
11:40:14.815 WARN    * pydantic-core/tests/validators/test_tagged_union.py
11:40:14.815 WARN    * pydantic/typing.py
11:40:14.815 WARN    * tests/test_plugins.py
11:40:14.815 WARN    * pydantic/json.py
11:40:14.815 WARN    * tests/test_internal.py
11:40:14.815 WARN    * pydantic/_internal/_generate_schema.py
11:40:14.815 WARN  This may lead to missing/broken features in SonarQube
11:40:14.875 INFO  CPD Executor 41 files had no CPD blocks
11:40:14.875 INFO  CPD Executor Calculating CPD for 360 files
11:40:14.956 INFO  CPD Executor CPD calculation finished (done) | time=80ms
11:40:15.014 INFO  Analysis report generated in 47ms, dir size=17.3 MB
11:40:15.411 INFO  Analysis report compressed in 397ms, zip size=9.1 MB
11:40:15.510 INFO  Analysis report uploaded in 99ms
11:40:15.510 INFO  ------------- Check Quality Gate status
11:40:15.511 INFO  Waiting for the analysis report to be processed (max 600s)
11:40:20.736 INFO  EXECUTION FAILURE
11:40:20.737 INFO  Total time: 20.258s
stderr_tail:
11:40:20.737 ERROR Error during SonarScanner CLI execution
11:40:20.737 ERROR QUALITY GATE STATUS: FAILED - View details on http://127.0.0.1:9000/dashboard?id=agq_oss_pydantic
11:40:20.737 ERROR 
11:40:20.737 ERROR Re-run SonarScanner CLI using the -X switch to enable full debug logging.

