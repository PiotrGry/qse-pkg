# AGQ Correlation Breakdown

- generated_at: `2026-03-07T08:06:04.255860+00:00`
- source_report: `artifacts/benchmark/agq_spaghetti_oss.json`
- repos_used: `9`

## Key Findings

- code_smells vs bugs: pearson=0.8906, spearman=0.7668 (n=9)
- agq_score: strongest pearson with smells_per_kloc = -0.5931 (moderate)
- modularity: strongest pearson with smells_per_kloc = -0.7492 (strong)
- stability: strongest pearson with bugs_per_kloc = -0.3343 (weak)
- cohesion: strongest pearson with complexity_per_kloc = -0.7622 (strong)

## Sonar vs Sonar

| X | Y | n | Pearson | Spearman |
|---|---|---:|---:|---:|
| code_smells | bugs | 9 | 0.8906 | 0.7668 |
| code_smells | vulnerabilities | 9 | -0.0279 | 0.2739 |
| bugs | vulnerabilities | 9 | 0.0857 | 0.2250 |
| code_smells | complexity | 9 | 0.3080 | 0.9500 |
| code_smells | cognitive_complexity | 9 | 0.4954 | 0.9500 |
| smells_per_kloc | bugs_per_kloc | 9 | 0.4458 | 0.1132 |
| smells_per_kloc | vulns_per_kloc | 9 | -0.2200 | -0.1369 |
| bugs_per_kloc | vulns_per_kloc | 9 | -0.1232 | 0.1430 |
| complexity_per_kloc | smells_per_kloc | 9 | -0.3069 | -0.0333 |
| duplicated_lines_density | smells_per_kloc | 9 | 0.2781 | -0.0792 |

## AGQ Breakdown vs Sonar/Defect

| AGQ Metric | Target | n | Pearson | Spearman |
|---|---|---:|---:|---:|
| agq_score | bugfix_ratio | 9 | -0.0570 | -0.0456 |
| agq_score | bugs_per_kloc | 9 | -0.5269 | -0.6180 |
| agq_score | vulns_per_kloc | 9 | 0.3731 | 0.2739 |
| agq_score | smells_per_kloc | 9 | -0.5931 | -0.4833 |
| agq_score | complexity_per_kloc | 9 | -0.0416 | -0.6167 |
| agq_score | cognitive_complexity_per_kloc | 9 | -0.3081 | -0.5167 |
| agq_score | duplicated_lines_density | 9 | -0.2501 | -0.0792 |
| agq_score | sonar_runtime_s | 9 | -0.0186 | 0.1333 |
| modularity | bugfix_ratio | 9 | 0.1598 | 0.0928 |
| modularity | bugs_per_kloc | 9 | -0.4182 | -0.1505 |
| modularity | vulns_per_kloc | 9 | 0.2181 | 0.1393 |
| modularity | smells_per_kloc | 9 | -0.7492 | -0.8645 |
| modularity | complexity_per_kloc | 9 | 0.5324 | 0.1695 |
| modularity | cognitive_complexity_per_kloc | 9 | 0.1728 | 0.0000 |
| modularity | duplicated_lines_density | 9 | -0.3460 | 0.0403 |
| modularity | sonar_runtime_s | 9 | 0.1845 | 0.1356 |
| acyclicity | bugfix_ratio | 9 | n/a | n/a |
| acyclicity | bugs_per_kloc | 9 | n/a | n/a |
| acyclicity | vulns_per_kloc | 9 | n/a | n/a |
| acyclicity | smells_per_kloc | 9 | n/a | n/a |
| acyclicity | complexity_per_kloc | 9 | n/a | n/a |
| acyclicity | cognitive_complexity_per_kloc | 9 | n/a | n/a |
| acyclicity | duplicated_lines_density | 9 | n/a | n/a |
| acyclicity | sonar_runtime_s | 9 | n/a | n/a |
| stability | bugfix_ratio | 9 | 0.0730 | 0.3195 |
| stability | bugs_per_kloc | 9 | -0.3343 | -0.4526 |
| stability | vulns_per_kloc | 9 | -0.0119 | 0.1369 |
| stability | smells_per_kloc | 9 | -0.3193 | -0.3667 |
| stability | complexity_per_kloc | 9 | 0.0923 | 0.0833 |
| stability | cognitive_complexity_per_kloc | 9 | -0.1612 | -0.0667 |
| stability | duplicated_lines_density | 9 | -0.1473 | 0.2970 |
| stability | sonar_runtime_s | 9 | -0.0392 | 0.3000 |
| cohesion | bugfix_ratio | 9 | -0.3215 | -0.4529 |
| cohesion | bugs_per_kloc | 9 | 0.2270 | -0.1500 |
| cohesion | vulns_per_kloc | 9 | 0.1683 | -0.1430 |
| cohesion | smells_per_kloc | 9 | 0.5297 | 0.4700 |
| cohesion | complexity_per_kloc | 9 | -0.7622 | -0.7572 |
| cohesion | cognitive_complexity_per_kloc | 9 | -0.3922 | -0.4526 |
| cohesion | duplicated_lines_density | 9 | 0.2709 | -0.3826 |
| cohesion | sonar_runtime_s | 9 | -0.2009 | -0.3307 |

## Strongest Correlations

| X | Y | Method | r | |r| strength |
|---|---|---|---:|---|
| code_smells | complexity | spearman | 0.9500 | very_strong |
| code_smells | cognitive_complexity | spearman | 0.9500 | very_strong |
| code_smells | bugs | pearson | 0.8906 | very_strong |
| modularity | smells_per_kloc | spearman | -0.8645 | very_strong |
| code_smells | bugs | spearman | 0.7668 | strong |
| cohesion | complexity_per_kloc | pearson | -0.7622 | strong |
| cohesion | complexity_per_kloc | spearman | -0.7572 | strong |
| modularity | smells_per_kloc | pearson | -0.7492 | strong |
| agq_score | bugs_per_kloc | spearman | -0.6180 | strong |
| agq_score | complexity_per_kloc | spearman | -0.6167 | strong |
| agq_score | smells_per_kloc | pearson | -0.5931 | moderate |
| modularity | complexity_per_kloc | pearson | 0.5324 | moderate |

