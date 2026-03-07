# AGQ Thesis Benchmark

- generated_at: `2026-03-07T12:45:03.945275+00:00`
- repos_target: `80`
- repos_with_agq: `78`
- repos_with_sonar: `0`

## Thesis Checks

| ID | Thesis | Result | Evidence |
|---|---|---|---|
| T1 | AGQ deterministic over repeated runs | PASS | max_score_delta=0.0000000000 (target <= 1e-9) |
| T2 | AGQ correlates stronger with defect proxy than Sonar maintainability | FAIL | insufficient data (predictor=code_smell_quality_score) |
| T3 | Complementarity: Sonar A but low AGQ exists | FAIL | cases=0 (none) |
| T4 | AGQ median runtime is lower than SonarQube median runtime | FAIL | median_agq_s=0.307 vs median_sonar_s=n/a |
| T5 | AGQ discriminates quality across heterogeneous repos | PASS | spread=0.2863, stddev=0.0499 |

## Correlations

- sonar predictor used: `code_smell_quality_score`
- pearson(AGQ, defect_proxy): `n/a`
- pearson(SonarPredictor, defect_proxy): `n/a`
- spearman(AGQ, SonarPredictor): `n/a`

## Repo Results

| Repo | AGQ(mean) | AGQ(delta) | Sonar Maint | Bugs | Vulns | Smells | Defect proxy | AGQ time(s) | Sonar time(s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| httpx | 0.6098 | 0.000000 | n/a | n/a | n/a | n/a | 0.0952 | 0.108 | n/a |
| requests | 0.6379 | 0.000000 | n/a | n/a | n/a | n/a | 0.1081 | 0.042 | n/a |
| urllib3 | 0.6047 | 0.000000 | n/a | n/a | n/a | n/a | 0.1382 | 0.129 | n/a |
| flask | 0.5577 | 0.000000 | n/a | n/a | n/a | n/a | 0.1213 | 0.071 | n/a |
| click | 0.5718 | 0.000000 | n/a | n/a | n/a | n/a | 0.1688 | 0.162 | n/a |
| pydantic | 0.6798 | 0.000000 | n/a | n/a | n/a | n/a | 0.1913 | 0.682 | n/a |
| fastapi | 0.7086 | 0.000000 | n/a | n/a | n/a | n/a | 0.0480 | 0.145 | n/a |
| rich | 0.6378 | 0.000000 | n/a | n/a | n/a | n/a | 0.1971 | 0.370 | n/a |
| pytest | 0.6667 | 0.000000 | n/a | n/a | n/a | n/a | 0.1375 | 0.000 | n/a |
| sanic | 0.6863 | 0.000000 | n/a | n/a | n/a | n/a | 0.1910 | 0.209 | n/a |
| scrapy | 0.6626 | 0.000000 | n/a | n/a | n/a | n/a | 0.1040 | 0.279 | n/a |
| aiohttp | 0.5758 | 0.000000 | n/a | n/a | n/a | n/a | 0.1394 | 0.435 | n/a |
| django | 0.7113 | 0.000000 | n/a | n/a | n/a | n/a | 0.0020 | 2.375 | n/a |
| starlette | 0.6619 | 0.000000 | n/a | n/a | n/a | n/a | 0.0888 | 0.128 | n/a |
| celery | 0.6471 | 0.000000 | n/a | n/a | n/a | n/a | 0.1620 | 0.442 | n/a |
| tornado | 0.6738 | 0.000000 | n/a | n/a | n/a | n/a | 0.1091 | 1.790 | n/a |
| typer | 0.6302 | 0.000000 | n/a | n/a | n/a | n/a | 0.0360 | 0.061 | n/a |
| arrow | 0.6887 | 0.000000 | n/a | n/a | n/a | n/a | 0.2174 | 0.470 | n/a |
| pendulum | 0.6719 | 0.000000 | n/a | n/a | n/a | n/a | 0.3134 | 0.077 | n/a |
| httpcore | 0.6653 | 0.000000 | n/a | n/a | n/a | n/a | 0.1389 | 0.085 | n/a |
| attrs | 0.8417 | 0.000000 | n/a | n/a | n/a | n/a | 0.1132 | 0.001 | n/a |
| marshmallow | 0.6560 | 0.000000 | n/a | n/a | n/a | n/a | 0.1141 | 0.140 | n/a |
| ansible | 0.6134 | 0.000000 | n/a | n/a | n/a | n/a | 0.2220 | 2.281 | n/a |
| salt | 0.7522 | 0.000000 | n/a | n/a | n/a | n/a | 0.2438 | 2.687 | n/a |
| home-assistant | 0.6181 | 0.000000 | n/a | n/a | n/a | n/a | 0.1020 | 20.201 | n/a |
| airflow | 0.6221 | 0.000000 | n/a | n/a | n/a | n/a | 0.2320 | 14.334 | n/a |
| thefuck | 0.7194 | 0.000000 | n/a | n/a | n/a | n/a | 0.0000 | 0.045 | n/a |
| you-get | 0.6057 | 0.000000 | n/a | n/a | n/a | n/a | 0.2895 | 0.172 | n/a |
| youtube-dl | 0.6437 | 0.000000 | n/a | n/a | n/a | n/a | 0.2281 | 2.073 | n/a |
| glances | 0.6803 | 0.000000 | n/a | n/a | n/a | n/a | 0.1005 | 0.151 | n/a |
| sqlalchemy | 0.6226 | 0.000000 | n/a | n/a | n/a | n/a | 0.1220 | 36.876 | n/a |
| django-rest-framework | 0.7247 | 0.000000 | n/a | n/a | n/a | n/a | 0.1727 | 2.639 | n/a |
| boto3 | 0.7435 | 0.000000 | n/a | n/a | n/a | n/a | 0.0194 | 0.062 | n/a |
| paramiko | 0.6768 | 0.000000 | n/a | n/a | n/a | n/a | 0.1111 | 0.177 | n/a |
| fabric | 0.6638 | 0.000000 | n/a | n/a | n/a | n/a | 0.0000 | 0.028 | n/a |
| sphinx | 0.7149 | 0.000000 | n/a | n/a | n/a | n/a | 0.1240 | 1.652 | n/a |
| black | 0.6649 | 0.000000 | n/a | n/a | n/a | n/a | 0.2620 | 0.120 | n/a |
| mypy | 0.6703 | 0.000000 | n/a | n/a | n/a | n/a | 0.2320 | 2.949 | n/a |
| ruff | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| poetry | 0.6682 | 0.000000 | n/a | n/a | n/a | n/a | 0.2580 | 0.246 | n/a |
| pillow | 0.7436 | 0.000000 | n/a | n/a | n/a | n/a | 0.0415 | 0.488 | n/a |
| scikit-learn | 0.6670 | 0.000000 | n/a | n/a | n/a | n/a | 0.2500 | 3.259 | n/a |
| pandas | 0.5991 | 0.000000 | n/a | n/a | n/a | n/a | 0.4040 | 7.053 | n/a |
| numpy | 0.6781 | 0.000000 | n/a | n/a | n/a | n/a | 0.2068 | 11.973 | n/a |
| matplotlib | 0.6238 | 0.000000 | n/a | n/a | n/a | n/a | 0.1626 | 4.283 | n/a |
| sympy | 0.6854 | 0.000000 | n/a | n/a | n/a | n/a | 0.1753 | 11.811 | n/a |
| networkx | 0.6806 | 0.000000 | n/a | n/a | n/a | n/a | 0.1392 | 1.631 | n/a |
| dask | 0.6977 | 0.000000 | n/a | n/a | n/a | n/a | 0.2090 | 3.386 | n/a |
| luigi | 0.6508 | 0.000000 | n/a | n/a | n/a | n/a | 0.3209 | 0.468 | n/a |
| prefect | 0.7176 | 0.000000 | n/a | n/a | n/a | n/a | 0.2640 | 2.443 | n/a |
| dramatiq | 0.6710 | 0.000000 | n/a | n/a | n/a | n/a | 0.1649 | 0.059 | n/a |
| huey | 0.6863 | 0.000000 | n/a | n/a | n/a | n/a | 0.1200 | 0.234 | n/a |
| gunicorn | 0.7232 | 0.000000 | n/a | n/a | n/a | n/a | 0.3382 | 0.461 | n/a |
| uvicorn | 0.6811 | 0.000000 | n/a | n/a | n/a | n/a | 0.0506 | 0.076 | n/a |
| werkzeug | 0.6308 | 0.000000 | n/a | n/a | n/a | n/a | 0.0767 | 0.245 | n/a |
| jinja | 0.6548 | 0.000000 | n/a | n/a | n/a | n/a | 0.1486 | 0.300 | n/a |
| mako | 0.7236 | 0.000000 | n/a | n/a | n/a | n/a | 0.1515 | 0.120 | n/a |
| pyjwt | 0.6283 | 0.000000 | n/a | n/a | n/a | n/a | 0.1926 | 0.090 | n/a |
| cryptography | 0.6703 | 0.000000 | n/a | n/a | n/a | n/a | 0.0160 | 0.312 | n/a |
| itsdangerous | 0.6308 | 0.000000 | n/a | n/a | n/a | n/a | 0.0247 | 0.014 | n/a |
| httpie | 0.6915 | 0.000000 | n/a | n/a | n/a | n/a | 0.2667 | 0.086 | n/a |
| dulwich | 0.6353 | 0.000000 | n/a | n/a | n/a | n/a | 0.1956 | 2.478 | n/a |
| pygments | 0.8440 | 0.000000 | n/a | n/a | n/a | n/a | 0.2141 | 1.187 | n/a |
| beautifulsoup4 | 0.6788 | 0.000000 | n/a | n/a | n/a | n/a | 0.0000 | 0.125 | n/a |
| lxml | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| tox | 0.6099 | 0.000000 | n/a | n/a | n/a | n/a | 0.2807 | 0.188 | n/a |
| nox | 0.6648 | 0.000000 | n/a | n/a | n/a | n/a | 0.3663 | 0.061 | n/a |
| hypothesis | 0.6276 | 0.000000 | n/a | n/a | n/a | n/a | 0.1015 | 1.229 | n/a |
| responses | 0.6324 | 0.000000 | n/a | n/a | n/a | n/a | 0.2308 | 0.095 | n/a |
| sentry-sdk | 0.6319 | 0.000000 | n/a | n/a | n/a | n/a | 0.2732 | 0.984 | n/a |
| kombu | 0.6462 | 0.000000 | n/a | n/a | n/a | n/a | 0.1372 | 0.221 | n/a |
| peewee | 0.7234 | 0.000000 | n/a | n/a | n/a | n/a | 0.1290 | 7.436 | n/a |
| alembic | 0.6326 | 0.000000 | n/a | n/a | n/a | n/a | 0.1535 | 0.303 | n/a |
| textual | 0.7293 | 0.000000 | n/a | n/a | n/a | n/a | 0.1847 | 1.105 | n/a |
| yt-dlp | 0.6500 | 0.000000 | n/a | n/a | n/a | n/a | 0.2960 | 3.845 | n/a |
| supervisor | 0.6695 | 0.000000 | n/a | n/a | n/a | n/a | 0.3191 | 1.099 | n/a |
| locust | 0.6931 | 0.000000 | n/a | n/a | n/a | n/a | 0.1371 | 3.453 | n/a |
| whoosh | 0.7309 | 0.000000 | n/a | n/a | n/a | n/a | 0.0000 | 0.890 | n/a |
| bottle | 0.6698 | 0.000000 | n/a | n/a | n/a | n/a | 0.3409 | 0.657 | n/a |
| falcon | 0.7082 | 0.000000 | n/a | n/a | n/a | n/a | 0.1233 | 0.250 | n/a |

## Failures

- `ruff`: source code string cannot contain null bytes
- `lxml`: 'utf-8' codec can't decode byte 0xe4 in position 27127: invalid continuation byte

