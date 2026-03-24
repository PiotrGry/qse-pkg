# AGQ Correlation Breakdown

- generated_at: `2026-03-07T11:58:02.624176+00:00`
- source_report: `artifacts/benchmark/agq_oss30_full.json`
- repos_used: `29`

## Key Findings

- code_smells vs bugs: pearson=0.5452, spearman=0.6647 (n=29)
- agq_score: strongest pearson with bugs_per_kloc = 0.3575 (weak)
- modularity: strongest pearson with bugs_per_kloc = 0.4335 (moderate)
- acyclicity: strongest pearson with sonar_runtime_s = 0.1920 (very_weak)
- stability: strongest pearson with bugs_per_kloc = 0.3783 (weak)
- cohesion: strongest pearson with complexity_per_kloc = -0.4497 (moderate)

## Sonar vs Sonar

| X | Y | n | Pearson | p | Spearman | p |
|---|---|---:|---:|---:|---:|---:|
| code_smells | bugs | 29 | 0.5452 | 0.0022 | 0.6647 | 0.0001 |
| code_smells | vulnerabilities | 29 | 0.2438 | 0.2025 | 0.5506 | 0.0020 |
| bugs | vulnerabilities | 29 | 0.1996 | 0.2991 | 0.3437 | 0.0679 |
| code_smells | complexity | 29 | 0.9768 | 0.0000 | 0.9069 | 0.0000 |
| code_smells | cognitive_complexity | 29 | 0.9620 | 0.0000 | 0.9148 | 0.0000 |
| smells_per_kloc | bugs_per_kloc | 29 | -0.0299 | 0.8777 | 0.2663 | 0.1626 |
| smells_per_kloc | vulns_per_kloc | 29 | 0.3300 | 0.0804 | 0.3337 | 0.0769 |
| bugs_per_kloc | vulns_per_kloc | 29 | -0.1136 | 0.5573 | -0.0685 | 0.7242 |
| complexity_per_kloc | smells_per_kloc | 29 | 0.4188 | 0.0238 | 0.4818 | 0.0081 |
| duplicated_lines_density | smells_per_kloc | 29 | -0.1298 | 0.5023 | -0.2090 | 0.2766 |

## AGQ Breakdown vs Sonar/Defect

| AGQ Metric | Target | n | Pearson | p | Spearman | p |
|---|---|---:|---:|---:|---:|---:|
| agq_score | bugfix_ratio | 29 | -0.1763 | 0.3602 | -0.1961 | 0.3081 |
| agq_score | bugs_per_kloc | 29 | 0.3575 | 0.0569 | 0.2040 | 0.2886 |
| agq_score | vulns_per_kloc | 29 | -0.1848 | 0.3373 | -0.2642 | 0.1660 |
| agq_score | smells_per_kloc | 29 | -0.0542 | 0.7799 | 0.1857 | 0.3348 |
| agq_score | complexity_per_kloc | 29 | -0.1471 | 0.4462 | -0.1921 | 0.3181 |
| agq_score | cognitive_complexity_per_kloc | 29 | -0.1327 | 0.4924 | -0.1862 | 0.3335 |
| agq_score | duplicated_lines_density | 29 | 0.0785 | 0.6855 | -0.0877 | 0.6509 |
| agq_score | sonar_runtime_s | 29 | -0.0624 | 0.7476 | 0.0507 | 0.7938 |
| modularity | bugfix_ratio | 29 | -0.0257 | 0.8947 | -0.0153 | 0.9373 |
| modularity | bugs_per_kloc | 29 | 0.4335 | 0.0188 | 0.0517 | 0.7899 |
| modularity | vulns_per_kloc | 29 | -0.1569 | 0.4162 | -0.1634 | 0.3970 |
| modularity | smells_per_kloc | 29 | 0.0987 | 0.6104 | -0.1897 | 0.3244 |
| modularity | complexity_per_kloc | 29 | 0.1493 | 0.4394 | 0.0990 | 0.6093 |
| modularity | cognitive_complexity_per_kloc | 29 | 0.1381 | 0.4749 | 0.0350 | 0.8571 |
| modularity | duplicated_lines_density | 29 | -0.0477 | 0.8058 | -0.0276 | 0.8870 |
| modularity | sonar_runtime_s | 29 | -0.0015 | 0.9940 | 0.1438 | 0.4566 |
| acyclicity | bugfix_ratio | 29 | 0.0546 | 0.7783 | 0.1754 | 0.3627 |
| acyclicity | bugs_per_kloc | 29 | 0.1541 | 0.4247 | 0.2480 | 0.1946 |
| acyclicity | vulns_per_kloc | 29 | -0.0872 | 0.6528 | 0.0476 | 0.8065 |
| acyclicity | smells_per_kloc | 29 | 0.1605 | 0.4056 | 0.3689 | 0.0490 |
| acyclicity | complexity_per_kloc | 29 | -0.0797 | 0.6810 | -0.0405 | 0.8346 |
| acyclicity | cognitive_complexity_per_kloc | 29 | 0.0988 | 0.6102 | 0.0925 | 0.6331 |
| acyclicity | duplicated_lines_density | 29 | -0.1109 | 0.5667 | -0.2114 | 0.2709 |
| acyclicity | sonar_runtime_s | 29 | 0.1920 | 0.3185 | 0.0865 | 0.6555 |
| stability | bugfix_ratio | 29 | -0.1684 | 0.3826 | -0.1419 | 0.4629 |
| stability | bugs_per_kloc | 29 | 0.3783 | 0.0430 | 0.3234 | 0.0870 |
| stability | vulns_per_kloc | 29 | -0.1191 | 0.5383 | -0.1815 | 0.3462 |
| stability | smells_per_kloc | 29 | -0.1438 | 0.4568 | 0.2010 | 0.2958 |
| stability | complexity_per_kloc | 29 | 0.0711 | 0.7140 | -0.0084 | 0.9656 |
| stability | cognitive_complexity_per_kloc | 29 | -0.1897 | 0.3244 | -0.1034 | 0.5933 |
| stability | duplicated_lines_density | 29 | 0.0577 | 0.7661 | -0.0015 | 0.9939 |
| stability | sonar_runtime_s | 29 | -0.2820 | 0.1384 | -0.0300 | 0.8770 |
| cohesion | bugfix_ratio | 29 | -0.1342 | 0.4875 | -0.1271 | 0.5111 |
| cohesion | bugs_per_kloc | 29 | -0.2616 | 0.1705 | -0.0483 | 0.8036 |
| cohesion | vulns_per_kloc | 29 | -0.0189 | 0.9227 | -0.0462 | 0.8120 |
| cohesion | smells_per_kloc | 29 | -0.0953 | 0.6227 | -0.0645 | 0.7394 |
| cohesion | complexity_per_kloc | 29 | -0.4497 | 0.0144 | -0.5565 | 0.0017 |
| cohesion | cognitive_complexity_per_kloc | 29 | -0.1705 | 0.3766 | -0.2249 | 0.2408 |
| cohesion | duplicated_lines_density | 29 | 0.1931 | 0.3156 | 0.0972 | 0.6158 |
| cohesion | sonar_runtime_s | 29 | 0.1378 | 0.4761 | 0.0921 | 0.6346 |

## Strongest Correlations

| X | Y | Method | r | |r| strength |
|---|---|---|---:|---|
| code_smells | complexity | pearson | 0.9768 | very_strong |
| code_smells | cognitive_complexity | pearson | 0.9620 | very_strong |
| code_smells | cognitive_complexity | spearman | 0.9148 | very_strong |
| code_smells | complexity | spearman | 0.9069 | very_strong |
| code_smells | bugs | spearman | 0.6647 | strong |
| cohesion | complexity_per_kloc | spearman | -0.5565 | moderate |
| code_smells | vulnerabilities | spearman | 0.5506 | moderate |
| code_smells | bugs | pearson | 0.5452 | moderate |
| complexity_per_kloc | smells_per_kloc | spearman | 0.4818 | moderate |
| cohesion | complexity_per_kloc | pearson | -0.4497 | moderate |
| modularity | bugs_per_kloc | pearson | 0.4335 | moderate |
| complexity_per_kloc | smells_per_kloc | pearson | 0.4188 | moderate |

## Mediation Analysis (AGQ → Mediator → Outcome)

| Chain | r(a) | p(a) | r(b) | p(b) | r(c) direct | Indirect | Sobel z | Sobel p | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| agq_score → complexity_per_kloc → bugs_per_kloc | -0.1471 | 0.4462 | -0.0149 | 0.9390 | 0.3575 | 0.0022 | 0.0768 | 0.9388 | no_mediation |
| agq_score → complexity_per_kloc → bugfix_ratio | -0.1471 | 0.4462 | -0.0487 | 0.8017 | -0.1763 | 0.0072 | 0.2409 | 0.8096 | no_mediation |
| agq_score → cognitive_complexity_per_kloc → bugs_per_kloc | -0.1327 | 0.4924 | -0.1559 | 0.4193 | 0.3575 | 0.0207 | 0.5307 | 0.5957 | no_mediation |
| agq_score → cognitive_complexity_per_kloc → bugfix_ratio | -0.1327 | 0.4924 | 0.3977 | 0.0326 | -0.1763 | -0.0528 | 0.6649 | 0.5061 | no_mediation |
| agq_score → smells_per_kloc → bugs_per_kloc | -0.0542 | 0.7799 | -0.0299 | 0.8777 | 0.3575 | 0.0016 | 0.1361 | 0.8918 | no_mediation |
| agq_score → smells_per_kloc → bugfix_ratio | -0.0542 | 0.7799 | 0.3603 | 0.0548 | -0.1763 | -0.0195 | 0.2795 | 0.7799 | no_mediation |

