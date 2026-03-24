# AGQ Ground Truth Analysis

Generated: 2026-03-07T12:27:36.096504+00:00
Source: `/home/pepus/dev/qse-pkg/artifacts/benchmark/agq_oss30_full.json`

## Thesis Checks

| ID | Thesis | Passed | Evidence |
|---|---|---|---|
| T6 | Blast radius correlates with AGQ stronger than bugfix_ratio | PASS | |r_s(AGQ, pct_cross_pkg)|=0.3132 vs |r_s(AGQ, bugfix_ratio)|=0.1961, n_blast=25, p_blast=0.12741849824747153 |
| T7 | Composite arch_quality_proxy correlates significantly with AGQ | FAIL | spearman=-0.0669, p=0.7505, n=25 |
| T8 | mean_files_per_fix negatively correlates with AGQ | PASS | spearman=-0.2247, p=0.2802, n=25 |

## Per-Repo Blast Radius

| Repo | AGQ | Files/fix | Dirs/fix | Pkgs/fix | Cross-pkg% | Wide% | GH bugs | MTTR(d) | Defect Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| flask | 0.558 | 1.6 | 1.2 | 1.2 | 15.4% | 7.7% | 36 | 36.8 | 0.764 |
| click | 0.572 | 1.2 | 1.0 | 1.0 | 0.0% | 0.0% | 141 | 439.8 | 0.442 |
| aiohttp | 0.576 | 1.5 | 1.0 | 1.0 | 2.7% | 1.3% | 895 | 13.4 | 0.696 |
| urllib3 | 0.605 | 1.3 | 1.1 | 1.1 | 6.7% | 0.0% | 0 | n/a | 0.431 |
| you-get | 0.606 | 2.2 | 1.2 | 1.0 | 0.0% | 5.6% | 0 | n/a | 0.445 |
| httpx | 0.610 | 1.5 | 1.0 | 1.0 | 0.0% | 0.0% | 0 | n/a | 0.369 |
| ansible | 0.613 | 10.6 | 2.6 | 1.0 | 1.6% | 4.8% | 394 | 2.5 | 0.686 |
| home-assistant | 0.617 | 1.2 | 1.0 | 1.0 | 0.0% | 0.0% | 0 | n/a | 0.237 |
| airflow | 0.621 | 1.3 | 1.2 | 1.1 | 5.1% | 0.0% | 0 | n/a | 0.397 |
| typer | 0.630 | 1.3 | 1.0 | 1.0 | 0.0% | 0.0% | 58 | 200.0 | 0.446 |
| rich | 0.638 | 1.1 | 1.0 | 1.0 | 2.5% | 0.0% | 74 | 3.2 | 0.357 |
| requests | 0.638 | 3.5 | 1.0 | 1.0 | 0.0% | 25.0% | 130 | 54.5 | 0.715 |
| youtube-dl | 0.644 | 1.2 | 1.1 | 1.0 | 0.0% | 0.0% | 0 | n/a | 0.195 |
| celery | 0.647 | 1.4 | 1.2 | 1.2 | 18.8% | 0.0% | 0 | n/a | 0.550 |
| marshmallow | 0.656 | 1.3 | 1.0 | 1.0 | 3.5% | 0.0% | 0 | n/a | 0.369 |
| starlette | 0.662 | 1.4 | 1.3 | 1.3 | 30.0% | 0.0% | 26 | 115.2 | 0.716 |
| scrapy | 0.663 | 1.8 | 1.5 | 1.4 | 17.9% | 3.6% | 390 | 35.4 | 0.843 |
| httpcore | 0.665 | 1.8 | 1.8 | 1.8 | 75.0% | 0.0% | 14 | 56.3 | 0.790 |
| pytest | 0.667 | n/a | n/a | n/a | n/a | n/a | 0 | n/a | n/a |
| pendulum | 0.672 | 1.0 | 1.0 | 1.0 | 0.0% | 0.0% | 43 | 13.8 | 0.289 |
| tornado | 0.674 | 1.1 | 1.0 | 1.0 | 0.0% | 0.0% | 0 | n/a | 0.168 |
| glances | 0.680 | 1.6 | 1.4 | 1.2 | 11.5% | 1.3% | 0 | n/a | 0.550 |
| sanic | 0.686 | 1.5 | 1.2 | 1.2 | 20.0% | 0.0% | 229 | 40.5 | 0.797 |
| arrow | 0.689 | 1.2 | 1.0 | 1.0 | 0.0% | 0.0% | 141 | 54.0 | 0.444 |
| fastapi | 0.709 | 1.1 | 1.1 | 1.1 | 14.3% | 0.0% | 117 | 23.6 | 0.444 |
| django | 0.711 | n/a | n/a | n/a | n/a | n/a | 0 | n/a | n/a |
| thefuck | 0.719 | n/a | n/a | n/a | n/a | n/a | 0 | n/a | n/a |
| salt | 0.752 | 1.3 | 1.2 | 1.2 | 15.8% | 1.2% | 0 | n/a | 0.508 |
| attrs | 0.842 | n/a | n/a | n/a | n/a | n/a | 79 | 33.9 | n/a |

## Correlation Matrix: AGQ vs Ground Truth

| AGQ metric | Target | n | Pearson | p | Spearman | p |
|---|---|---:|---:|---:|---:|---:|
| agq_score | bugfix_ratio | 29 | -0.1763 | 0.3602 | -0.1961 | 0.3081 |
| agq_score | mean_files_per_fix | 25 | -0.1669 | 0.4251 | -0.2247 | 0.2802 |
| agq_score | median_files_per_fix | 25 | 0.0225 | 0.9148 | -0.0311 | 0.8829 |
| agq_score | pct_cross_package_fixes | 25 | 0.2723 | 0.1878 | 0.3132 | 0.1274 |
| agq_score | pct_wide_fixes | 25 | -0.1775 | 0.3959 | -0.2414 | 0.2449 |
| agq_score | mean_packages_per_fix | 25 | 0.3165 | 0.1232 | 0.3228 | 0.1155 |
| agq_score | bug_issues_per_kloc | 29 | -0.1109 | 0.5668 | -0.1163 | 0.5479 |
| agq_score | median_close_time_days | 15 | -0.3113 | 0.2588 | -0.0750 | 0.7905 |
| agq_score | arch_quality_proxy | 25 | 0.0484 | 0.8181 | -0.0669 | 0.7505 |
| modularity | bugfix_ratio | 29 | -0.0257 | 0.8947 | -0.0153 | 0.9373 |
| modularity | mean_files_per_fix | 25 | 0.2065 | 0.3220 | 0.0927 | 0.6593 |
| modularity | median_files_per_fix | 25 | -0.2785 | 0.1777 | -0.2484 | 0.2312 |
| modularity | pct_cross_package_fixes | 25 | -0.2021 | 0.3327 | -0.0696 | 0.7411 |
| modularity | pct_wide_fixes | 25 | 0.1730 | 0.4082 | 0.1764 | 0.3988 |
| modularity | mean_packages_per_fix | 25 | -0.1987 | 0.3410 | -0.0433 | 0.8371 |
| modularity | bug_issues_per_kloc | 29 | -0.0032 | 0.9869 | -0.2047 | 0.2869 |
| modularity | median_close_time_days | 15 | -0.2401 | 0.3887 | -0.3929 | 0.1475 |
| modularity | arch_quality_proxy | 25 | 0.1368 | 0.5145 | 0.0873 | 0.6780 |
| acyclicity | bugfix_ratio | 29 | 0.0546 | 0.7783 | 0.1754 | 0.3627 |
| acyclicity | mean_files_per_fix | 25 | 0.1529 | 0.4655 | 0.1287 | 0.5399 |
| acyclicity | median_files_per_fix | 25 | 0.0114 | 0.9570 | -0.0631 | 0.7643 |
| acyclicity | pct_cross_package_fixes | 25 | 0.2002 | 0.3374 | 0.2087 | 0.3167 |
| acyclicity | pct_wide_fixes | 25 | 0.0582 | 0.7822 | 0.0157 | 0.9406 |
| acyclicity | mean_packages_per_fix | 25 | 0.2353 | 0.2575 | 0.2452 | 0.2374 |
| acyclicity | bug_issues_per_kloc | 29 | -0.2914 | 0.1251 | -0.1766 | 0.3595 |
| acyclicity | median_close_time_days | 15 | -0.2673 | 0.3354 | 0.0850 | 0.7631 |
| acyclicity | arch_quality_proxy | 25 | 0.0592 | 0.7787 | -0.1268 | 0.5458 |
| stability | bugfix_ratio | 29 | -0.1684 | 0.3826 | -0.1419 | 0.4629 |
| stability | mean_files_per_fix | 25 | -0.3560 | 0.0807 | -0.1805 | 0.3880 |
| stability | median_files_per_fix | 25 | 0.0718 | 0.7332 | 0.0670 | 0.7503 |
| stability | pct_cross_package_fixes | 25 | 0.3323 | 0.1046 | 0.4825 | 0.0146 |
| stability | pct_wide_fixes | 25 | -0.2223 | 0.2856 | -0.1300 | 0.5357 |
| stability | mean_packages_per_fix | 25 | 0.3848 | 0.0575 | 0.4794 | 0.0153 |
| stability | bug_issues_per_kloc | 29 | -0.0923 | 0.6338 | 0.0102 | 0.9581 |
| stability | median_close_time_days | 15 | -0.2813 | 0.3098 | -0.3036 | 0.2714 |
| stability | arch_quality_proxy | 25 | -0.1441 | 0.4918 | -0.2024 | 0.3319 |
| cohesion | bugfix_ratio | 29 | -0.1342 | 0.4875 | -0.1271 | 0.5111 |
| cohesion | mean_files_per_fix | 25 | -0.0100 | 0.9621 | -0.4048 | 0.0447 |
| cohesion | median_files_per_fix | 25 | 0.0541 | 0.7974 | 0.0556 | 0.7919 |
| cohesion | pct_cross_package_fixes | 25 | -0.0964 | 0.6468 | -0.3183 | 0.1209 |
| cohesion | pct_wide_fixes | 25 | -0.1321 | 0.5289 | -0.3631 | 0.0744 |
| cohesion | mean_packages_per_fix | 25 | -0.1300 | 0.5357 | -0.3367 | 0.0998 |
| cohesion | bug_issues_per_kloc | 29 | 0.1293 | 0.5039 | 0.0119 | 0.9512 |
| cohesion | median_close_time_days | 15 | 0.0066 | 0.9813 | -0.1429 | 0.6115 |
| cohesion | arch_quality_proxy | 25 | 0.1959 | 0.3481 | 0.4052 | 0.0445 |

## Top Correlations (|r_s| > 0.2)

| Pair | Spearman | p-value | Strength |
|---|---:|---:|---|
| stability vs pct_cross_package_fixes | 0.4825 | 0.0146 | moderate |
| stability vs mean_packages_per_fix | 0.4794 | 0.0153 | moderate |
| cohesion vs arch_quality_proxy | 0.4052 | 0.0445 | moderate |
| cohesion vs mean_files_per_fix | -0.4048 | 0.0447 | moderate |
| modularity vs median_close_time_days | -0.3929 | 0.1475 | weak |
| cohesion vs pct_wide_fixes | -0.3631 | 0.0744 | weak |
| cohesion vs mean_packages_per_fix | -0.3367 | 0.0998 | weak |
| agq_score vs mean_packages_per_fix | 0.3228 | 0.1155 | weak |
| cohesion vs pct_cross_package_fixes | -0.3183 | 0.1209 | weak |
| agq_score vs pct_cross_package_fixes | 0.3132 | 0.1274 | weak |
| stability vs median_close_time_days | -0.3036 | 0.2714 | weak |
| modularity vs median_files_per_fix | -0.2484 | 0.2312 | weak |
| acyclicity vs mean_packages_per_fix | 0.2452 | 0.2374 | weak |
| agq_score vs pct_wide_fixes | -0.2414 | 0.2449 | weak |
| agq_score vs mean_files_per_fix | -0.2247 | 0.2802 | weak |
| acyclicity vs pct_cross_package_fixes | 0.2087 | 0.3167 | weak |
| modularity vs bug_issues_per_kloc | -0.2047 | 0.2869 | weak |
| stability vs arch_quality_proxy | -0.2024 | 0.3319 | weak |

