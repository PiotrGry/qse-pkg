# AGQ Ground Truth Analysis

Generated: 2026-03-07T20:56:39.152155+00:00
Source: `artifacts/benchmark/agq_thesis_oss80.json`

## Thesis Checks

| ID | Thesis | Passed | Evidence |
|---|---|---|---|
| T6 | Blast radius correlates with AGQ stronger than bugfix_ratio | FAIL | |r_s(AGQ, pct_cross_pkg)|=0.1398 vs |r_s(AGQ, bugfix_ratio)|=0.1535, n_blast=68, p_blast=0.2554655928018925 |
| T7 | Composite arch_quality_proxy correlates significantly with AGQ | FAIL | spearman=0.0284, p=0.8179, n=68 |
| T8 | mean_files_per_fix negatively correlates with AGQ | PASS | spearman=-0.0702, p=0.5697, n=68 |

## Per-Repo Blast Radius

| Repo | AGQ | Files/fix | Dirs/fix | Pkgs/fix | Cross-pkg% | Wide% | GH bugs | MTTR(d) | Defect Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| flask | 0.558 | 2.0 | 1.4 | 1.2 | 20.0% | 10.0% | 36 | 36.8 | 0.666 |
| click | 0.572 | 1.6 | 1.5 | 1.0 | 0.0% | 0.0% | 141 | 439.8 | 0.454 |
| aiohttp | 0.576 | 3.3 | 2.0 | 1.1 | 9.1% | 18.2% | 895 | 13.4 | 0.665 |
| pandas | 0.599 | 2.7 | 2.3 | 1.9 | 72.7% | 6.8% | 0 | n/a | 0.679 |
| urllib3 | 0.605 | 7.1 | 2.5 | 1.6 | 33.3% | 8.3% | 0 | n/a | 0.627 |
| you-get | 0.606 | 2.2 | 1.2 | 1.1 | 5.6% | 5.6% | 0 | n/a | 0.401 |
| httpx | 0.610 | 1.5 | 1.2 | 1.0 | 0.0% | 0.0% | 0 | n/a | 0.241 |
| tox | 0.610 | 5.4 | 2.1 | 1.5 | 18.8% | 6.2% | 0 | n/a | 0.550 |
| ansible | 0.613 | 1.7 | 1.7 | 1.6 | 63.0% | 0.0% | 435 | 2.6 | 0.722 |
| home-assistant | 0.618 | 1.1 | 1.0 | 1.0 | 0.0% | 0.0% | 0 | n/a | 0.177 |
| airflow | 0.622 | 1.8 | 1.4 | 1.1 | 11.1% | 5.6% | 0 | n/a | 0.393 |
| sqlalchemy | 0.623 | 5.8 | 2.6 | 1.6 | 40.0% | 20.0% | 0 | n/a | 0.649 |
| matplotlib | 0.624 | 5.5 | 1.6 | 1.1 | 8.8% | 2.3% | 0 | n/a | 0.485 |
| hypothesis | 0.628 | 7.2 | 2.5 | 1.3 | 10.6% | 6.1% | 0 | n/a | 0.520 |
| pyjwt | 0.628 | 1.9 | 1.4 | 1.4 | 40.0% | 0.0% | 0 | n/a | 0.550 |
| typer | 0.630 | n/a | n/a | n/a | n/a | n/a | 58 | 200.0 | n/a |
| werkzeug | 0.631 | 1.8 | 1.7 | 1.5 | 40.0% | 0.0% | 0 | n/a | 0.535 |
| itsdangerous | 0.631 | n/a | n/a | n/a | n/a | n/a | 0 | n/a | n/a |
| sentry-sdk | 0.632 | 8.7 | 2.1 | 1.2 | 5.9% | 2.9% | 0 | n/a | 0.498 |
| responses | 0.632 | 1.8 | 1.4 | 1.0 | 0.0% | 0.0% | 0 | n/a | 0.311 |
| alembic | 0.633 | 8.3 | 2.7 | 2.2 | 58.3% | 16.7% | 0 | n/a | 0.704 |
| dulwich | 0.635 | 11.1 | 5.0 | 1.7 | 20.0% | 8.9% | 0 | n/a | 0.612 |
| rich | 0.638 | 1.4 | 1.3 | 1.0 | 2.1% | 0.0% | 74 | 3.2 | 0.416 |
| requests | 0.638 | 3.4 | 1.2 | 1.0 | 0.0% | 20.0% | 130 | 54.5 | 0.592 |
| youtube-dl | 0.644 | 1.3 | 1.1 | 1.0 | 0.0% | 0.0% | 0 | n/a | 0.187 |
| kombu | 0.646 | 2.3 | 2.3 | 2.1 | 84.6% | 0.0% | 0 | n/a | 0.662 |
| celery | 0.647 | 2.6 | 2.4 | 1.7 | 47.8% | 13.0% | 0 | n/a | 0.625 |
| yt-dlp | 0.650 | 36.8 | 1.7 | 1.2 | 9.1% | 3.0% | 0 | n/a | 0.557 |
| luigi | 0.651 | 1.4 | 1.1 | 1.1 | 5.9% | 2.9% | 0 | n/a | 0.279 |
| jinja | 0.655 | 5.1 | 1.5 | 1.5 | 36.4% | 27.3% | 0 | n/a | 0.620 |
| marshmallow | 0.656 | 2.0 | 1.5 | 1.0 | 3.9% | 0.0% | 0 | n/a | 0.366 |
| starlette | 0.662 | n/a | n/a | n/a | n/a | n/a | 26 | 115.2 | n/a |
| scrapy | 0.663 | 19.8 | 3.8 | 2.7 | 23.1% | 15.4% | 390 | 35.4 | 0.809 |
| fabric | 0.664 | n/a | n/a | n/a | n/a | n/a | 0 | n/a | n/a |
| nox | 0.665 | 1.5 | 1.1 | 1.0 | 0.0% | 2.9% | 0 | n/a | 0.246 |
| black | 0.665 | 2.2 | 1.8 | 1.1 | 5.3% | 0.0% | 0 | n/a | 0.386 |
| httpcore | 0.665 | 2.2 | 2.2 | 2.0 | 60.0% | 0.0% | 14 | 56.3 | 0.765 |
| pytest | 0.667 | 32.3 | 5.6 | 2.8 | 63.2% | 15.8% | 0 | n/a | 0.754 |
| scikit-learn | 0.667 | 1.8 | 1.7 | 1.5 | 48.1% | 0.0% | 0 | n/a | 0.565 |
| poetry | 0.668 | 1.6 | 1.3 | 1.3 | 10.5% | 0.0% | 0 | n/a | 0.346 |
| supervisor | 0.670 | 1.0 | 1.0 | 1.0 | 0.0% | 0.0% | 0 | n/a | 0.167 |
| bottle | 0.670 | 1.0 | 1.0 | 1.0 | 0.0% | 0.0% | 0 | n/a | 0.167 |
| cryptography | 0.670 | 1.7 | 1.7 | 1.7 | 33.3% | 0.0% | 0 | n/a | 0.478 |
| mypy | 0.670 | 91.8 | 10.6 | 2.1 | 57.9% | 15.8% | 0 | n/a | 0.744 |
| dramatiq | 0.671 | 1.3 | 1.2 | 1.1 | 13.0% | 0.0% | 0 | n/a | 0.306 |
| pendulum | 0.672 | 1.3 | 1.2 | 1.0 | 0.0% | 0.0% | 43 | 13.8 | 0.350 |
| tornado | 0.674 | 1.3 | 1.2 | 1.2 | 8.3% | 0.0% | 0 | n/a | 0.276 |
| paramiko | 0.677 | 1.7 | 1.3 | 1.3 | 33.3% | 0.0% | 0 | n/a | 0.478 |
| numpy | 0.678 | 184.0 | 14.5 | 5.2 | 23.6% | 14.9% | 0 | n/a | 0.669 |
| beautifulsoup4 | 0.679 | n/a | n/a | n/a | n/a | n/a | 0 | n/a | n/a |
| pydantic | 0.680 | 2.3 | 1.2 | 1.1 | 7.7% | 7.7% | 0 | n/a | 0.423 |
| glances | 0.680 | 9.1 | 4.2 | 1.4 | 11.8% | 8.8% | 0 | n/a | 0.552 |
| networkx | 0.681 | 2.0 | 1.6 | 1.3 | 20.0% | 6.7% | 0 | n/a | 0.495 |
| uvicorn | 0.681 | 1.8 | 1.0 | 1.0 | 0.0% | 0.0% | 0 | n/a | 0.286 |
| sympy | 0.685 | 4.3 | 1.8 | 1.4 | 19.9% | 3.4% | 0 | n/a | 0.545 |
| sanic | 0.686 | 1.3 | 1.1 | 1.1 | 12.5% | 0.0% | 229 | 40.5 | 0.491 |
| huey | 0.686 | n/a | n/a | n/a | n/a | n/a | 0 | n/a | n/a |
| arrow | 0.689 | 1.3 | 1.1 | 1.0 | 0.0% | 0.0% | 141 | 54.0 | 0.395 |
| httpie | 0.691 | 2.7 | 1.7 | 1.3 | 33.3% | 0.0% | 0 | n/a | 0.582 |
| locust | 0.693 | 1.5 | 1.3 | 1.2 | 11.8% | 0.0% | 0 | n/a | 0.344 |
| dask | 0.698 | 1.4 | 1.4 | 1.4 | 25.0% | 0.0% | 0 | n/a | 0.403 |
| falcon | 0.708 | 2.4 | 1.9 | 1.8 | 63.6% | 0.0% | 0 | n/a | 0.654 |
| fastapi | 0.709 | 1.0 | 1.0 | 1.0 | 0.0% | 0.0% | 117 | 23.6 | 0.308 |
| django | 0.711 | n/a | n/a | n/a | n/a | n/a | 0 | n/a | n/a |
| sphinx | 0.715 | 1.6 | 1.6 | 1.4 | 38.9% | 0.0% | 0 | n/a | 0.475 |
| prefect | 0.718 | 113.6 | 21.4 | 3.9 | 12.0% | 24.0% | 0 | n/a | 0.600 |
| thefuck | 0.719 | n/a | n/a | n/a | n/a | n/a | 0 | n/a | n/a |
| gunicorn | 0.723 | 1.9 | 1.3 | 1.3 | 26.3% | 5.3% | 0 | n/a | 0.515 |
| peewee | 0.723 | 1.3 | 1.3 | 1.2 | 16.7% | 0.0% | 0 | n/a | 0.346 |
| mako | 0.724 | 1.7 | 1.7 | 1.7 | 66.7% | 0.0% | 0 | n/a | 0.565 |
| django-rest-framework | 0.725 | 1.4 | 1.2 | 1.2 | 20.0% | 0.0% | 0 | n/a | 0.388 |
| textual | 0.729 | 7.4 | 1.5 | 1.3 | 15.3% | 4.3% | 0 | n/a | 0.560 |
| whoosh | 0.731 | n/a | n/a | n/a | n/a | n/a | 0 | n/a | n/a |
| boto3 | 0.743 | n/a | n/a | n/a | n/a | n/a | 0 | n/a | n/a |
| pillow | 0.744 | 22.1 | 2.1 | 1.4 | 25.0% | 10.4% | 0 | n/a | 0.647 |
| salt | 0.752 | 301.2 | 30.2 | 9.2 | 44.4% | 22.2% | 496 | 44.0 | 0.878 |
| attrs | 0.842 | 1.8 | 1.4 | 1.4 | 44.4% | 0.0% | 79 | 33.9 | 0.724 |
| pygments | 0.844 | 32.0 | 2.3 | 1.8 | 16.4% | 9.1% | 0 | n/a | 0.600 |

## Correlation Matrix: AGQ vs Ground Truth

| AGQ metric | Target | n | Pearson | p | Spearman | p |
|---|---|---:|---:|---:|---:|---:|
| agq_score | bugfix_ratio | 78 | -0.1659 | 0.1467 | -0.1535 | 0.1796 |
| agq_score | mean_files_per_fix | 68 | 0.2489 | 0.0407 | -0.0702 | 0.5697 |
| agq_score | median_files_per_fix | 68 | -0.2257 | 0.0642 | -0.3114 | 0.0097 |
| agq_score | pct_cross_package_fixes | 68 | 0.0985 | 0.4240 | 0.1398 | 0.2555 |
| agq_score | pct_wide_fixes | 68 | -0.0530 | 0.6678 | -0.1453 | 0.2372 |
| agq_score | mean_packages_per_fix | 68 | 0.2477 | 0.0417 | 0.1627 | 0.1849 |
| agq_score | bug_issues_per_kloc | 78 | -0.1556 | 0.1737 | -0.1287 | 0.2614 |
| agq_score | median_close_time_days | 16 | -0.3158 | 0.2334 | -0.0471 | 0.8626 |
| agq_score | arch_quality_proxy | 68 | -0.0853 | 0.4891 | 0.0284 | 0.8179 |
| modularity | bugfix_ratio | 78 | -0.0317 | 0.7830 | 0.0240 | 0.8347 |
| modularity | mean_files_per_fix | 68 | -0.0330 | 0.7896 | -0.0109 | 0.9297 |
| modularity | median_files_per_fix | 68 | -0.0312 | 0.8006 | -0.0753 | 0.5418 |
| modularity | pct_cross_package_fixes | 68 | 0.0240 | 0.8461 | -0.0085 | 0.9452 |
| modularity | pct_wide_fixes | 68 | -0.1728 | 0.1588 | -0.0808 | 0.5125 |
| modularity | mean_packages_per_fix | 68 | -0.0754 | 0.5411 | -0.0339 | 0.7835 |
| modularity | bug_issues_per_kloc | 78 | -0.0708 | 0.5379 | -0.2121 | 0.0623 |
| modularity | median_close_time_days | 16 | -0.2360 | 0.3789 | -0.3824 | 0.1439 |
| modularity | arch_quality_proxy | 68 | 0.0324 | 0.7933 | 0.0786 | 0.5239 |
| acyclicity | bugfix_ratio | 78 | 0.0785 | 0.4944 | 0.0768 | 0.5040 |
| acyclicity | mean_files_per_fix | 68 | 0.1070 | 0.3851 | 0.0620 | 0.6153 |
| acyclicity | median_files_per_fix | 68 | -0.1448 | 0.2388 | -0.1581 | 0.1979 |
| acyclicity | pct_cross_package_fixes | 68 | 0.1461 | 0.2347 | 0.0374 | 0.7623 |
| acyclicity | pct_wide_fixes | 68 | -0.0782 | 0.5263 | 0.0536 | 0.6644 |
| acyclicity | mean_packages_per_fix | 68 | 0.1263 | 0.3048 | 0.0918 | 0.4566 |
| acyclicity | bug_issues_per_kloc | 78 | -0.3613 | 0.0012 | -0.1396 | 0.2230 |
| acyclicity | median_close_time_days | 16 | -0.2746 | 0.3034 | 0.0930 | 0.7320 |
| acyclicity | arch_quality_proxy | 68 | 0.0551 | 0.6554 | 0.0057 | 0.9635 |
| stability | bugfix_ratio | 78 | -0.1044 | 0.3632 | -0.0391 | 0.7336 |
| stability | mean_files_per_fix | 68 | 0.3236 | 0.0071 | 0.0605 | 0.6241 |
| stability | median_files_per_fix | 68 | -0.2029 | 0.0971 | -0.2183 | 0.0737 |
| stability | pct_cross_package_fixes | 68 | 0.1989 | 0.1039 | 0.3245 | 0.0069 |
| stability | pct_wide_fixes | 68 | 0.1085 | 0.3784 | 0.0544 | 0.6592 |
| stability | mean_packages_per_fix | 68 | 0.3565 | 0.0028 | 0.3788 | 0.0014 |
| stability | bug_issues_per_kloc | 78 | -0.1027 | 0.3711 | -0.0295 | 0.7978 |
| stability | median_close_time_days | 16 | -0.2736 | 0.3052 | -0.2559 | 0.3388 |
| stability | arch_quality_proxy | 68 | -0.2540 | 0.0366 | -0.2059 | 0.0920 |
| cohesion | bugfix_ratio | 78 | -0.1840 | 0.1068 | -0.1239 | 0.2798 |
| cohesion | mean_files_per_fix | 68 | -0.0254 | 0.8374 | -0.1375 | 0.2635 |
| cohesion | median_files_per_fix | 68 | -0.0417 | 0.7356 | -0.0605 | 0.6243 |
| cohesion | pct_cross_package_fixes | 68 | -0.1873 | 0.1262 | -0.1976 | 0.1063 |
| cohesion | pct_wide_fixes | 68 | -0.1089 | 0.3765 | -0.1941 | 0.1128 |
| cohesion | mean_packages_per_fix | 68 | -0.0604 | 0.6248 | -0.2111 | 0.0840 |
| cohesion | bug_issues_per_kloc | 78 | 0.0933 | 0.4163 | 0.0270 | 0.8142 |
| cohesion | median_close_time_days | 16 | 0.0048 | 0.9860 | -0.1265 | 0.6407 |
| cohesion | arch_quality_proxy | 68 | 0.1445 | 0.2397 | 0.1809 | 0.1400 |

## Top Correlations (|r_s| > 0.2)

| Pair | Spearman | p-value | Strength |
|---|---:|---:|---|
| modularity vs median_close_time_days | -0.3824 | 0.1439 | weak |
| stability vs mean_packages_per_fix | 0.3788 | 0.0014 | weak |
| stability vs pct_cross_package_fixes | 0.3245 | 0.0069 | weak |
| agq_score vs median_files_per_fix | -0.3114 | 0.0097 | weak |
| stability vs median_close_time_days | -0.2559 | 0.3388 | weak |
| stability vs median_files_per_fix | -0.2183 | 0.0737 | weak |
| modularity vs bug_issues_per_kloc | -0.2121 | 0.0623 | weak |
| cohesion vs mean_packages_per_fix | -0.2111 | 0.0840 | weak |
| stability vs arch_quality_proxy | -0.2059 | 0.0920 | weak |

