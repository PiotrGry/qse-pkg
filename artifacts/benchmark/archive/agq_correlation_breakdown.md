# AGQ Correlation Breakdown

- generated_at: `2026-03-07T19:33:38.351774+00:00`
- source_report: `artifacts/benchmark/agq_thesis_oss80.json`
- repos_used: `78`

## Key Findings

- code_smells vs bugs: pearson=0.3508, spearman=0.7305 (n=78)
- agq_score: strongest pearson with bugfix_ratio = -0.1659 (very_weak)
- modularity: strongest pearson with smells_per_kloc = 0.2241 (weak)
- acyclicity: strongest pearson with duplicated_lines_density = -0.1604 (very_weak)
- stability: strongest pearson with bugs_per_kloc = 0.1632 (very_weak)
- cohesion: strongest pearson with complexity_per_kloc = -0.2600 (weak)

## Sonar vs Sonar

| X | Y | n | Pearson | p | Spearman | p |
|---|---|---:|---:|---:|---:|---:|
| code_smells | bugs | 78 | 0.3508 | 0.0016 | 0.7305 | 0.0000 |
| code_smells | vulnerabilities | 78 | 0.0613 | 0.5938 | 0.2509 | 0.0267 |
| bugs | vulnerabilities | 78 | -0.0016 | 0.9889 | 0.1107 | 0.3345 |
| code_smells | complexity | 78 | 0.9060 | 0.0000 | 0.9278 | 0.0000 |
| code_smells | cognitive_complexity | 78 | 0.9168 | 0.0000 | 0.9326 | 0.0000 |
| smells_per_kloc | bugs_per_kloc | 78 | -0.0561 | 0.6255 | 0.1069 | 0.3515 |
| smells_per_kloc | vulns_per_kloc | 78 | 0.0225 | 0.8451 | -0.0278 | 0.8092 |
| bugs_per_kloc | vulns_per_kloc | 78 | -0.0962 | 0.4023 | -0.1765 | 0.1222 |
| complexity_per_kloc | smells_per_kloc | 78 | 0.3529 | 0.0015 | 0.4003 | 0.0003 |
| duplicated_lines_density | smells_per_kloc | 78 | -0.1454 | 0.2041 | -0.1651 | 0.1487 |

## AGQ Breakdown vs Sonar/Defect

| AGQ Metric | Target | n | Pearson | p | Spearman | p |
|---|---|---:|---:|---:|---:|---:|
| agq_score | bugfix_ratio | 78 | -0.1659 | 0.1467 | -0.1535 | 0.1796 |
| agq_score | mean_files_per_fix | 0 | n/a | n/a | n/a | n/a |
| agq_score | median_files_per_fix | 0 | n/a | n/a | n/a | n/a |
| agq_score | pct_cross_package_fixes | 0 | n/a | n/a | n/a | n/a |
| agq_score | pct_wide_fixes | 0 | n/a | n/a | n/a | n/a |
| agq_score | mean_packages_per_fix | 0 | n/a | n/a | n/a | n/a |
| agq_score | bug_issues_per_kloc | 0 | n/a | n/a | n/a | n/a |
| agq_score | median_close_time_days | 0 | n/a | n/a | n/a | n/a |
| agq_score | arch_quality_proxy | 0 | n/a | n/a | n/a | n/a |
| agq_score | bugs_per_kloc | 78 | 0.1050 | 0.3603 | -0.0480 | 0.6762 |
| agq_score | vulns_per_kloc | 78 | -0.1560 | 0.1725 | -0.1627 | 0.1547 |
| agq_score | smells_per_kloc | 78 | 0.0328 | 0.7756 | 0.2362 | 0.0373 |
| agq_score | complexity_per_kloc | 78 | -0.1409 | 0.2185 | -0.0310 | 0.7875 |
| agq_score | cognitive_complexity_per_kloc | 78 | -0.0686 | 0.5507 | 0.0235 | 0.8383 |
| agq_score | duplicated_lines_density | 78 | 0.0080 | 0.9447 | -0.0048 | 0.9668 |
| agq_score | sonar_runtime_s | 78 | -0.0938 | 0.4142 | 0.0192 | 0.8673 |
| modularity | bugfix_ratio | 78 | -0.0317 | 0.7830 | 0.0240 | 0.8347 |
| modularity | mean_files_per_fix | 0 | n/a | n/a | n/a | n/a |
| modularity | median_files_per_fix | 0 | n/a | n/a | n/a | n/a |
| modularity | pct_cross_package_fixes | 0 | n/a | n/a | n/a | n/a |
| modularity | pct_wide_fixes | 0 | n/a | n/a | n/a | n/a |
| modularity | mean_packages_per_fix | 0 | n/a | n/a | n/a | n/a |
| modularity | bug_issues_per_kloc | 0 | n/a | n/a | n/a | n/a |
| modularity | median_close_time_days | 0 | n/a | n/a | n/a | n/a |
| modularity | arch_quality_proxy | 0 | n/a | n/a | n/a | n/a |
| modularity | bugs_per_kloc | 78 | 0.1934 | 0.0897 | -0.1252 | 0.2747 |
| modularity | vulns_per_kloc | 78 | -0.0927 | 0.4193 | 0.0464 | 0.6866 |
| modularity | smells_per_kloc | 78 | 0.2241 | 0.0485 | 0.0736 | 0.5220 |
| modularity | complexity_per_kloc | 78 | 0.0319 | 0.7816 | -0.0452 | 0.6946 |
| modularity | cognitive_complexity_per_kloc | 78 | 0.0128 | 0.9112 | -0.0467 | 0.6847 |
| modularity | duplicated_lines_density | 78 | -0.0841 | 0.4642 | -0.1533 | 0.1802 |
| modularity | sonar_runtime_s | 78 | -0.0335 | 0.7712 | -0.0364 | 0.7520 |
| acyclicity | bugfix_ratio | 78 | 0.0785 | 0.4944 | 0.0768 | 0.5040 |
| acyclicity | mean_files_per_fix | 0 | n/a | n/a | n/a | n/a |
| acyclicity | median_files_per_fix | 0 | n/a | n/a | n/a | n/a |
| acyclicity | pct_cross_package_fixes | 0 | n/a | n/a | n/a | n/a |
| acyclicity | pct_wide_fixes | 0 | n/a | n/a | n/a | n/a |
| acyclicity | mean_packages_per_fix | 0 | n/a | n/a | n/a | n/a |
| acyclicity | bug_issues_per_kloc | 0 | n/a | n/a | n/a | n/a |
| acyclicity | median_close_time_days | 0 | n/a | n/a | n/a | n/a |
| acyclicity | arch_quality_proxy | 0 | n/a | n/a | n/a | n/a |
| acyclicity | bugs_per_kloc | 78 | 0.1134 | 0.3229 | 0.1075 | 0.3488 |
| acyclicity | vulns_per_kloc | 78 | -0.0835 | 0.4674 | -0.0331 | 0.7738 |
| acyclicity | smells_per_kloc | 78 | 0.1587 | 0.1652 | 0.1485 | 0.1944 |
| acyclicity | complexity_per_kloc | 78 | 0.0007 | 0.9948 | 0.0529 | 0.6452 |
| acyclicity | cognitive_complexity_per_kloc | 78 | 0.1016 | 0.3762 | 0.1123 | 0.3278 |
| acyclicity | duplicated_lines_density | 78 | -0.1604 | 0.1607 | -0.1567 | 0.1707 |
| acyclicity | sonar_runtime_s | 78 | 0.1322 | 0.2487 | 0.0459 | 0.6896 |
| stability | bugfix_ratio | 78 | -0.1044 | 0.3632 | -0.0391 | 0.7336 |
| stability | mean_files_per_fix | 0 | n/a | n/a | n/a | n/a |
| stability | median_files_per_fix | 0 | n/a | n/a | n/a | n/a |
| stability | pct_cross_package_fixes | 0 | n/a | n/a | n/a | n/a |
| stability | pct_wide_fixes | 0 | n/a | n/a | n/a | n/a |
| stability | mean_packages_per_fix | 0 | n/a | n/a | n/a | n/a |
| stability | bug_issues_per_kloc | 0 | n/a | n/a | n/a | n/a |
| stability | median_close_time_days | 0 | n/a | n/a | n/a | n/a |
| stability | arch_quality_proxy | 0 | n/a | n/a | n/a | n/a |
| stability | bugs_per_kloc | 78 | 0.1632 | 0.1533 | 0.1526 | 0.1824 |
| stability | vulns_per_kloc | 78 | -0.1039 | 0.3654 | -0.1401 | 0.2210 |
| stability | smells_per_kloc | 78 | 0.0106 | 0.9269 | 0.1764 | 0.1223 |
| stability | complexity_per_kloc | 78 | -0.0154 | 0.8937 | 0.0139 | 0.9036 |
| stability | cognitive_complexity_per_kloc | 78 | -0.0025 | 0.9828 | 0.0100 | 0.9306 |
| stability | duplicated_lines_density | 78 | -0.0038 | 0.9734 | 0.1377 | 0.2292 |
| stability | sonar_runtime_s | 78 | -0.1110 | 0.3331 | 0.1652 | 0.1483 |
| cohesion | bugfix_ratio | 78 | -0.1840 | 0.1068 | -0.1239 | 0.2798 |
| cohesion | mean_files_per_fix | 0 | n/a | n/a | n/a | n/a |
| cohesion | median_files_per_fix | 0 | n/a | n/a | n/a | n/a |
| cohesion | pct_cross_package_fixes | 0 | n/a | n/a | n/a | n/a |
| cohesion | pct_wide_fixes | 0 | n/a | n/a | n/a | n/a |
| cohesion | mean_packages_per_fix | 0 | n/a | n/a | n/a | n/a |
| cohesion | bug_issues_per_kloc | 0 | n/a | n/a | n/a | n/a |
| cohesion | median_close_time_days | 0 | n/a | n/a | n/a | n/a |
| cohesion | arch_quality_proxy | 0 | n/a | n/a | n/a | n/a |
| cohesion | bugs_per_kloc | 78 | -0.2139 | 0.0600 | -0.1871 | 0.1010 |
| cohesion | vulns_per_kloc | 78 | -0.0420 | 0.7150 | -0.0290 | 0.8010 |
| cohesion | smells_per_kloc | 78 | -0.1759 | 0.1234 | -0.1132 | 0.3238 |
| cohesion | complexity_per_kloc | 78 | -0.2600 | 0.0215 | -0.3333 | 0.0029 |
| cohesion | cognitive_complexity_per_kloc | 78 | -0.1865 | 0.1021 | -0.1437 | 0.2094 |
| cohesion | duplicated_lines_density | 78 | 0.1578 | 0.1675 | 0.0353 | 0.7591 |
| cohesion | sonar_runtime_s | 78 | -0.0684 | 0.5516 | -0.0118 | 0.9183 |

## Strongest Correlations

| X | Y | Method | r | |r| strength |
|---|---|---|---:|---|
| code_smells | cognitive_complexity | spearman | 0.9326 | very_strong |
| code_smells | complexity | spearman | 0.9278 | very_strong |
| code_smells | cognitive_complexity | pearson | 0.9168 | very_strong |
| code_smells | complexity | pearson | 0.9060 | very_strong |
| code_smells | bugs | spearman | 0.7305 | strong |
| complexity_per_kloc | smells_per_kloc | spearman | 0.4003 | moderate |
| complexity_per_kloc | smells_per_kloc | pearson | 0.3529 | weak |
| code_smells | bugs | pearson | 0.3508 | weak |
| cohesion | complexity_per_kloc | spearman | -0.3333 | weak |
| cohesion | complexity_per_kloc | pearson | -0.2600 | weak |
| code_smells | vulnerabilities | spearman | 0.2509 | weak |
| agq_score | smells_per_kloc | spearman | 0.2362 | weak |

## Mediation Analysis (AGQ → Mediator → Outcome)

| Chain | r(a) | p(a) | r(b) | p(b) | r(c) direct | Indirect | Sobel z | Sobel p | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| agq_score → complexity_per_kloc → bugs_per_kloc | -0.1409 | 0.2185 | -0.0489 | 0.6709 | 0.1050 | 0.0069 | 0.4034 | 0.6867 | no_mediation |
| agq_score → complexity_per_kloc → bugfix_ratio | -0.1409 | 0.2185 | -0.1250 | 0.2756 | -0.1659 | 0.0176 | 0.8223 | 0.4109 | no_mediation |
| agq_score → complexity_per_kloc → mean_files_per_fix | -0.1409 | 0.2185 | n/a | n/a | n/a | n/a | n/a | n/a | None |
| agq_score → complexity_per_kloc → pct_cross_package_fixes | -0.1409 | 0.2185 | n/a | n/a | n/a | n/a | n/a | n/a | None |
| agq_score → cognitive_complexity_per_kloc → bugs_per_kloc | -0.0686 | 0.5507 | -0.0931 | 0.4173 | 0.1050 | 0.0064 | 0.4830 | 0.6291 | no_mediation |
| agq_score → cognitive_complexity_per_kloc → bugfix_ratio | -0.0686 | 0.5507 | 0.0948 | 0.4089 | -0.1659 | -0.0065 | 0.4861 | 0.6269 | no_mediation |
| agq_score → cognitive_complexity_per_kloc → mean_files_per_fix | -0.0686 | 0.5507 | n/a | n/a | n/a | n/a | n/a | n/a | None |
| agq_score → cognitive_complexity_per_kloc → pct_cross_package_fixes | -0.0686 | 0.5507 | n/a | n/a | n/a | n/a | n/a | n/a | None |
| agq_score → smells_per_kloc → bugs_per_kloc | 0.0328 | 0.7756 | -0.0561 | 0.6255 | 0.1050 | -0.0018 | 0.2470 | 0.8049 | no_mediation |
| agq_score → smells_per_kloc → bugfix_ratio | 0.0328 | 0.7756 | -0.0535 | 0.6417 | -0.1659 | -0.0018 | 0.2439 | 0.8073 | no_mediation |
| agq_score → smells_per_kloc → mean_files_per_fix | 0.0328 | 0.7756 | n/a | n/a | n/a | n/a | n/a | n/a | None |
| agq_score → smells_per_kloc → pct_cross_package_fixes | 0.0328 | 0.7756 | n/a | n/a | n/a | n/a | n/a | n/a | None |

