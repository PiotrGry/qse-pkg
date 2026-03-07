# AGQ Thesis Benchmark

- generated_at: `2026-03-07T13:44:38.151736+00:00`
- repos_target: `80`
- repos_with_agq: `78`
- repos_with_sonar: `78`

## Thesis Checks

| ID | Thesis | Result | Evidence |
|---|---|---|---|
| T1 | AGQ deterministic over repeated runs | PASS | max_score_delta=0.0000000000 (target <= 1e-9) |
| T2 | AGQ correlates stronger with defect proxy than Sonar maintainability | PASS | predictor=code_smell_quality_score; |r(AGQ,defect_proxy)|=0.1659 vs |r(Sonar,defect_proxy)|=0.0811 |
| T3 | Complementarity: Sonar A but low AGQ exists | PASS | cases=61 (httpx, requests, urllib3, flask, click, pydantic, rich, pytest, sanic, scrapy, aiohttp, starlette, celery, tornado, typer, arrow, pendulum, httpcore, marshmallow, ansible, home-assistant, airflow, you-get, youtube-dl, glances, sqlalchemy, paramiko, fabric, black, mypy, poetry, scikit-learn, pandas, numpy, matplotlib, sympy, networkx, dask, luigi, dramatiq, huey, uvicorn, werkzeug, jinja, pyjwt, cryptography, itsdangerous, httpie, dulwich, beautifulsoup4, tox, nox, hypothesis, responses, sentry-sdk, kombu, alembic, yt-dlp, supervisor, locust, bottle) |
| T4 | AGQ median runtime is lower than SonarQube median runtime | PASS | median_agq_s=0.301 vs median_sonar_s=14.903 |
| T5 | AGQ discriminates quality across heterogeneous repos | PASS | spread=0.2863, stddev=0.0499 |

## Correlations

- sonar predictor used: `code_smell_quality_score`
- pearson(AGQ, defect_proxy): `-0.1659`
- pearson(SonarPredictor, defect_proxy): `-0.0811`
- spearman(AGQ, SonarPredictor): `-0.2362`

## Repo Results

| Repo | AGQ(mean) | AGQ(delta) | Sonar Maint | Bugs | Vulns | Smells | Defect proxy | AGQ time(s) | Sonar time(s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| httpx | 0.6098 | 0.000000 | A | 8 | 3 | 171 | 0.0952 | 0.112 | 12.804 |
| requests | 0.6379 | 0.000000 | A | 0 | 0 | 107 | 0.1081 | 0.043 | 12.266 |
| urllib3 | 0.6047 | 0.000000 | A | 4 | 25 | 259 | 0.1300 | 0.128 | 13.677 |
| flask | 0.5577 | 0.000000 | A | 7 | 0 | 99 | 0.1213 | 0.072 | 12.688 |
| click | 0.5718 | 0.000000 | A | 0 | 0 | 200 | 0.1688 | 0.162 | 12.973 |
| pydantic | 0.6798 | 0.000000 | A | 44 | 0 | 1825 | 0.2900 | 0.686 | 26.027 |
| fastapi | 0.7086 | 0.000000 | A | 3 | 0 | 766 | 0.0500 | 0.147 | 18.502 |
| rich | 0.6378 | 0.000000 | A | 20 | 0 | 413 | 0.1971 | 0.375 | 14.982 |
| pytest | 0.6667 | 0.000000 | A | 33 | 0 | 1041 | 0.1279 | 0.000 | 17.624 |
| sanic | 0.6863 | 0.000000 | A | 35 | 0 | 464 | 0.1910 | 0.215 | 15.613 |
| scrapy | 0.6626 | 0.000000 | A | 87 | 10 | 882 | 0.1329 | 0.284 | 16.884 |
| aiohttp | 0.5758 | 0.000000 | A | 18 | 1 | 700 | 0.1200 | 0.435 | 17.021 |
| django | 0.7113 | 0.000000 | A | 85 | 1 | 4314 | 0.0000 | 2.430 | 53.311 |
| starlette | 0.6619 | 0.000000 | A | 6 | 0 | 216 | 0.0400 | 0.131 | 12.819 |
| celery | 0.6471 | 0.000000 | A | 25 | 1 | 1260 | 0.2600 | 0.447 | 17.832 |
| tornado | 0.6738 | 0.000000 | A | 22 | 9 | 469 | 0.1091 | 1.755 | 14.600 |
| typer | 0.6302 | 0.000000 | A | 2 | 0 | 143 | 0.0200 | 0.061 | 14.285 |
| arrow | 0.6887 | 0.000000 | A | 13 | 0 | 242 | 0.2174 | 0.471 | 12.718 |
| pendulum | 0.6719 | 0.000000 | A | 163 | 0 | 149 | 0.3134 | 0.077 | 13.359 |
| httpcore | 0.6653 | 0.000000 | A | 1 | 8 | 145 | 0.1389 | 0.089 | 12.249 |
| attrs | 0.8417 | 0.000000 | A | 57 | 0 | 185 | 0.1100 | 0.001 | 12.513 |
| marshmallow | 0.6560 | 0.000000 | A | 9 | 0 | 111 | 0.1509 | 0.143 | 12.490 |
| ansible | 0.6134 | 0.000000 | A | 42 | 4 | 2654 | 0.3300 | 2.305 | 34.991 |
| salt | 0.7522 | 0.000000 | A | 112 | 18 | 10286 | 0.1881 | 2.736 | 69.800 |
| home-assistant | 0.6181 | 0.000000 | A | 85 | 2 | 14783 | 0.1200 | 20.421 | 208.869 |
| airflow | 0.6221 | 0.000000 | A | 174 | 9 | 5832 | 0.2200 | 14.424 | 102.584 |
| thefuck | 0.7194 | 0.000000 | A | 2 | 0 | 108 | 0.0000 | 0.046 | 13.498 |
| you-get | 0.6057 | 0.000000 | A | 8 | 6 | 713 | 0.2895 | 0.168 | 13.002 |
| youtube-dl | 0.6437 | 0.000000 | A | 29 | 13 | 1197 | 0.1600 | 2.121 | 29.227 |
| glances | 0.6803 | 0.000000 | A | 7 | 0 | 277 | 0.1239 | 0.153 | 14.320 |
| sqlalchemy | 0.6226 | 0.000000 | A | 241 | 0 | 10845 | 0.1236 | 37.034 | 60.510 |
| django-rest-framework | 0.7247 | 0.000000 | A | 14 | 0 | 527 | 0.1100 | 2.651 | 14.280 |
| boto3 | 0.7435 | 0.000000 | A | 17 | 0 | 209 | 0.0156 | 0.062 | 12.575 |
| paramiko | 0.6768 | 0.000000 | A | 8 | 3 | 532 | 0.1111 | 0.181 | 13.347 |
| fabric | 0.6638 | 0.000000 | A | 2 | 0 | 362 | 0.0000 | 0.025 | 11.893 |
| sphinx | 0.7149 | 0.000000 | A | 17 | 0 | 2004 | 0.1900 | 1.701 | 27.514 |
| black | 0.6649 | 0.000000 | A | 432 | 0 | 1719 | 0.2500 | 0.120 | 17.659 |
| mypy | 0.6703 | 0.000000 | A | 10 | 2 | 3032 | 0.1900 | 2.948 | 48.417 |
| ruff | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| poetry | 0.6682 | 0.000000 | A | 15 | 1 | 320 | 0.2200 | 0.244 | 16.372 |
| pillow | 0.7436 | 0.000000 | A | 29 | 0 | 773 | 0.0378 | 0.487 | 16.706 |
| scikit-learn | 0.6670 | 0.000000 | A | 115 | 0 | 7850 | 0.3000 | 3.279 | 37.224 |
| pandas | 0.5991 | 0.000000 | A | 988 | 6 | 4895 | 0.4700 | 7.048 | 58.595 |
| numpy | 0.6781 | 0.000000 | A | 1119 | 0 | 2505 | 0.1863 | 11.939 | 31.553 |
| matplotlib | 0.6238 | 0.000000 | A | 29 | 0 | 2405 | 0.1627 | 4.340 | 33.719 |
| sympy | 0.6854 | 0.000000 | A | 372 | 0 | 15996 | 0.1785 | 11.878 | 86.064 |
| networkx | 0.6806 | 0.000000 | A | 51 | 0 | 3639 | 0.1500 | 1.615 | 27.799 |
| dask | 0.6977 | 0.000000 | A | 63 | 0 | 1069 | 0.1300 | 3.329 | 23.341 |
| luigi | 0.6508 | 0.000000 | A | 10 | 1 | 678 | 0.3209 | 0.464 | 15.718 |
| prefect | 0.7176 | 0.000000 | A | 64 | 13 | 3902 | 0.2800 | 2.377 | 52.836 |
| dramatiq | 0.6710 | 0.000000 | A | 6 | 0 | 58 | 0.1705 | 0.058 | 12.565 |
| huey | 0.6863 | 0.000000 | A | 0 | 0 | 111 | 0.1200 | 0.214 | 11.993 |
| gunicorn | 0.7232 | 0.000000 | A | 6 | 20 | 582 | 0.3548 | 0.462 | 16.281 |
| uvicorn | 0.6811 | 0.000000 | A | 0 | 0 | 129 | 0.0500 | 0.070 | 12.398 |
| werkzeug | 0.6308 | 0.000000 | A | 7 | 0 | 311 | 0.0767 | 0.241 | 13.948 |
| jinja | 0.6548 | 0.000000 | A | 95 | 0 | 171 | 0.1486 | 0.294 | 12.973 |
| mako | 0.7236 | 0.000000 | A | 3 | 0 | 254 | 0.1515 | 0.116 | 12.431 |
| pyjwt | 0.6283 | 0.000000 | A | 2 | 4 | 57 | 0.1700 | 0.088 | 11.856 |
| cryptography | 0.6703 | 0.000000 | A | 31 | 43 | 256 | 0.0300 | 0.309 | 15.276 |
| itsdangerous | 0.6308 | 0.000000 | A | 1 | 0 | 5 | 0.0247 | 0.017 | 11.261 |
| httpie | 0.6915 | 0.000000 | A | 0 | 1 | 187 | 0.2667 | 0.083 | 12.861 |
| dulwich | 0.6353 | 0.000000 | A | 36 | 0 | 1660 | 0.2586 | 2.492 | 22.068 |
| pygments | 0.8440 | 0.000000 | A | 13 | 0 | 1137 | 0.2267 | 1.220 | 17.588 |
| beautifulsoup4 | 0.6788 | 0.000000 | A | 4 | 0 | 212 | 0.0000 | 0.123 | 12.089 |
| lxml | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| tox | 0.6099 | 0.000000 | A | 7 | 0 | 265 | 0.3500 | 0.183 | 14.473 |
| nox | 0.6648 | 0.000000 | A | 0 | 0 | 108 | 0.3900 | 0.058 | 12.412 |
| hypothesis | 0.6276 | 0.000000 | A | 50 | 0 | 772 | 0.1049 | 1.189 | 17.915 |
| responses | 0.6324 | 0.000000 | A | 0 | 0 | 69 | 0.2308 | 0.095 | 11.707 |
| sentry-sdk | 0.6319 | 0.000000 | A | 94 | 0 | 1350 | 0.3241 | 0.978 | 18.578 |
| kombu | 0.6462 | 0.000000 | A | 16 | 1 | 646 | 0.1300 | 0.224 | 14.434 |
| peewee | 0.7234 | 0.000000 | A | 6 | 1 | 743 | 0.1100 | 7.534 | 14.824 |
| alembic | 0.6326 | 0.000000 | A | 14 | 0 | 406 | 0.1513 | 0.294 | 14.633 |
| textual | 0.7293 | 0.000000 | A | 44 | 0 | 2714 | 0.2128 | 1.096 | 30.303 |
| yt-dlp | 0.6500 | 0.000000 | A | 27 | 9 | 1963 | 0.3400 | 3.873 | 34.246 |
| supervisor | 0.6695 | 0.000000 | A | 2 | 0 | 546 | 0.3191 | 1.144 | 13.757 |
| locust | 0.6931 | 0.000000 | A | 3 | 1 | 498 | 0.1155 | 3.503 | 14.004 |
| whoosh | 0.7309 | 0.000000 | A | 10 | 0 | 518 | 0.0000 | 0.883 | 15.512 |
| bottle | 0.6698 | 0.000000 | A | 9 | 0 | 126 | 0.3409 | 0.648 | 12.172 |
| falcon | 0.7082 | 0.000000 | A | 9 | 0 | 680 | 0.1800 | 0.255 | 15.057 |

## Failures

- `ruff`: source code string cannot contain null bytes
- `lxml`: 'utf-8' codec can't decode byte 0xe4 in position 27127: invalid continuation byte

