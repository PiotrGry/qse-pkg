# AGQ Metric Version Comparison

- generated_at: `2026-03-07T22:10:25.628457+00:00`
- versions: `v1`, `v2`

## AGQ Score Distribution

| Version | n | Min | Max | Mean | Std | Spread |
|---|---:|---:|---:|---:|---:|---:|
| v1 | 78 | 0.5577 | 0.8440 | 0.6688 | 0.0499 | 0.2863 |
| v2 | 78 | 0.6294 | 0.9667 | 0.7935 | 0.0572 | 0.3373 |

## AGQ Component Means

| Version | Modularity | Acyclicity | Stability | Cohesion |
|---|---:|---:|---:|---:|
| v1 | 0.5919 | 0.9767 | 0.3131 | 0.7934 |
| v2 | 0.5919 | 0.9776 | 0.8113 | 0.7934 |

## Thesis Results

| Version | T1 | T2 | T3 | T4 | T5 | Total |
|---|---:|---:|---:|---:|---:|---:|
| v1 | PASS | PASS | PASS | PASS | PASS | 5/5 |
| v2 | PASS | FAIL | PASS | PASS | PASS | 4/5 |

## Correlations

| Version | r(AGQ,bugfix) | r(Sonar,bugfix) | r_s(AGQ,hotspot) | r_s(Sonar,hotspot) | r_s(AGQ,gini) |
|---|---:|---:|---:|---:|---:|
| v1 | -0.1659 | -0.0811 | n/a | n/a | n/a |
| v2 | 0.0304 | -0.0811 | n/a | n/a | n/a |

## Per-Repo AGQ: v1 → v2

| Repo | v1 | v2 | Δ(v2-v1) |
|---|---:|---:|---:|
| youtube-dl | 0.6437 | 0.8761 | +0.2324 |
| yt-dlp | 0.6500 | 0.8818 | +0.2318 |
| hypothesis | 0.6276 | 0.8513 | +0.2236 |
| you-get | 0.6057 | 0.8201 | +0.2144 |
| sqlalchemy | 0.6226 | 0.8348 | +0.2122 |
| ansible | 0.6134 | 0.8232 | +0.2099 |
| airflow | 0.6221 | 0.8277 | +0.2056 |
| matplotlib | 0.6238 | 0.8081 | +0.1842 |
| home-assistant | 0.6181 | 0.8009 | +0.1829 |
| tox | 0.6099 | 0.7841 | +0.1742 |
| cryptography | 0.6703 | 0.8422 | +0.1719 |
| sentry-sdk | 0.6319 | 0.8026 | +0.1707 |
| prefect | 0.7176 | 0.8715 | +0.1539 |
| dask | 0.6977 | 0.8461 | +0.1484 |
| luigi | 0.6508 | 0.7988 | +0.1480 |
| jinja | 0.6548 | 0.7944 | +0.1395 |
| marshmallow | 0.6560 | 0.7952 | +0.1392 |
| pytest | 0.6667 | 0.8056 | +0.1389 |
| poetry | 0.6682 | 0.8063 | +0.1381 |
| glances | 0.6803 | 0.8174 | +0.1371 |
| tornado | 0.6738 | 0.8109 | +0.1371 |
| mypy | 0.6703 | 0.8072 | +0.1369 |
| scrapy | 0.6626 | 0.7983 | +0.1356 |
| starlette | 0.6619 | 0.7961 | +0.1342 |
| django | 0.7113 | 0.8452 | +0.1339 |
| uvicorn | 0.6811 | 0.8145 | +0.1334 |
| supervisor | 0.6695 | 0.8029 | +0.1333 |
| mako | 0.7236 | 0.8546 | +0.1310 |
| paramiko | 0.6768 | 0.8062 | +0.1294 |
| whoosh | 0.7309 | 0.8601 | +0.1292 |
| falcon | 0.7082 | 0.8369 | +0.1288 |
| numpy | 0.6781 | 0.8042 | +0.1261 |
| huey | 0.6863 | 0.8121 | +0.1257 |
| attrs | 0.8417 | 0.9667 | +0.1250 |
| sanic | 0.6863 | 0.8109 | +0.1247 |
| celery | 0.6471 | 0.7709 | +0.1238 |
| dramatiq | 0.6710 | 0.7938 | +0.1227 |
| textual | 0.7293 | 0.8508 | +0.1215 |
| gunicorn | 0.7232 | 0.8437 | +0.1205 |
| bottle | 0.6698 | 0.7901 | +0.1203 |
| pydantic | 0.6798 | 0.7999 | +0.1202 |
| black | 0.6649 | 0.7834 | +0.1184 |
| arrow | 0.6887 | 0.8070 | +0.1182 |
| alembic | 0.6326 | 0.7502 | +0.1176 |
| fastapi | 0.7086 | 0.8259 | +0.1173 |
| dulwich | 0.6353 | 0.7520 | +0.1167 |
| peewee | 0.7234 | 0.8397 | +0.1163 |
| sphinx | 0.7149 | 0.8306 | +0.1157 |
| pendulum | 0.6719 | 0.7868 | +0.1149 |
| beautifulsoup4 | 0.6788 | 0.7924 | +0.1136 |
| nox | 0.6648 | 0.7776 | +0.1128 |
| scikit-learn | 0.6670 | 0.7796 | +0.1125 |
| responses | 0.6324 | 0.7446 | +0.1122 |
| boto3 | 0.7435 | 0.8549 | +0.1114 |
| httpie | 0.6915 | 0.8024 | +0.1109 |
| httpcore | 0.6653 | 0.7762 | +0.1109 |
| kombu | 0.6462 | 0.7561 | +0.1099 |
| locust | 0.6931 | 0.8019 | +0.1088 |
| pyjwt | 0.6283 | 0.7366 | +0.1083 |
| werkzeug | 0.6308 | 0.7382 | +0.1074 |
| pandas | 0.5991 | 0.7010 | +0.1020 |
| sympy | 0.6854 | 0.7870 | +0.1016 |
| pillow | 0.7436 | 0.8430 | +0.0994 |
| django-rest-framework | 0.7247 | 0.8176 | +0.0930 |
| fabric | 0.6638 | 0.7543 | +0.0905 |
| urllib3 | 0.6047 | 0.6920 | +0.0873 |
| salt | 0.7522 | 0.8382 | +0.0860 |
| rich | 0.6378 | 0.7227 | +0.0849 |
| aiohttp | 0.5758 | 0.6589 | +0.0831 |
| typer | 0.6302 | 0.7079 | +0.0777 |
| httpx | 0.6098 | 0.6872 | +0.0774 |
| itsdangerous | 0.6308 | 0.7040 | +0.0732 |
| click | 0.5718 | 0.6435 | +0.0717 |
| flask | 0.5577 | 0.6294 | +0.0717 |
| requests | 0.6379 | 0.6980 | +0.0601 |
| networkx | 0.6806 | 0.7151 | +0.0346 |
| thefuck | 0.7194 | 0.7424 | +0.0230 |
| pygments | 0.8440 | 0.8540 | +0.0100 |

## Fix Summary

- **v1**: Baseline: stability=Martin's D (A=0 everywhere=mean(I)), acyclicity=sum_cyclic/total, modularity=(Q+0.5)/1.5, coupling=density
- **v2**: stability→instability_variance (per-node), acyclicity→largest_SCC/total, modularity→max(0,Q)/0.75 + n<10=0.5, coupling→mean_out_degree/threshold

