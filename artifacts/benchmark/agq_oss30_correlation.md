# AGQ Correlation Breakdown

- generated_at: `2026-03-07T11:38:01.047928+00:00`
- source_report: `artifacts/benchmark/agq_oss30_nosq.json`
- repos_used: `30`

## Key Findings

- code_smells vs bugs: pearson=n/a, spearman=n/a (n=0)
- agq_score: strongest pearson with bugfix_ratio = -0.1680 (very_weak)
- modularity: strongest pearson with bugfix_ratio = -0.0278 (very_weak)
- acyclicity: strongest pearson with bugfix_ratio = 0.0402 (very_weak)
- stability: strongest pearson with bugfix_ratio = -0.1562 (very_weak)
- cohesion: strongest pearson with bugfix_ratio = -0.1217 (very_weak)

## Sonar vs Sonar

| X | Y | n | Pearson | p | Spearman | p |
|---|---|---:|---:|---:|---:|---:|
| code_smells | bugs | 0 | n/a | n/a | n/a | n/a |
| code_smells | vulnerabilities | 0 | n/a | n/a | n/a | n/a |
| bugs | vulnerabilities | 0 | n/a | n/a | n/a | n/a |
| code_smells | complexity | 0 | n/a | n/a | n/a | n/a |
| code_smells | cognitive_complexity | 0 | n/a | n/a | n/a | n/a |
| smells_per_kloc | bugs_per_kloc | 0 | n/a | n/a | n/a | n/a |
| smells_per_kloc | vulns_per_kloc | 0 | n/a | n/a | n/a | n/a |
| bugs_per_kloc | vulns_per_kloc | 0 | n/a | n/a | n/a | n/a |
| complexity_per_kloc | smells_per_kloc | 0 | n/a | n/a | n/a | n/a |
| duplicated_lines_density | smells_per_kloc | 0 | n/a | n/a | n/a | n/a |

## AGQ Breakdown vs Sonar/Defect

| AGQ Metric | Target | n | Pearson | p | Spearman | p |
|---|---|---:|---:|---:|---:|---:|
| agq_score | bugfix_ratio | 30 | -0.1680 | 0.3748 | -0.1684 | 0.3737 |
| agq_score | bugs_per_kloc | 0 | n/a | n/a | n/a | n/a |
| agq_score | vulns_per_kloc | 0 | n/a | n/a | n/a | n/a |
| agq_score | smells_per_kloc | 0 | n/a | n/a | n/a | n/a |
| agq_score | complexity_per_kloc | 0 | n/a | n/a | n/a | n/a |
| agq_score | cognitive_complexity_per_kloc | 0 | n/a | n/a | n/a | n/a |
| agq_score | duplicated_lines_density | 0 | n/a | n/a | n/a | n/a |
| agq_score | sonar_runtime_s | 0 | n/a | n/a | n/a | n/a |
| modularity | bugfix_ratio | 30 | -0.0278 | 0.8839 | -0.0020 | 0.9916 |
| modularity | bugs_per_kloc | 0 | n/a | n/a | n/a | n/a |
| modularity | vulns_per_kloc | 0 | n/a | n/a | n/a | n/a |
| modularity | smells_per_kloc | 0 | n/a | n/a | n/a | n/a |
| modularity | complexity_per_kloc | 0 | n/a | n/a | n/a | n/a |
| modularity | cognitive_complexity_per_kloc | 0 | n/a | n/a | n/a | n/a |
| modularity | duplicated_lines_density | 0 | n/a | n/a | n/a | n/a |
| modularity | sonar_runtime_s | 0 | n/a | n/a | n/a | n/a |
| acyclicity | bugfix_ratio | 30 | 0.0402 | 0.8329 | 0.1408 | 0.4581 |
| acyclicity | bugs_per_kloc | 0 | n/a | n/a | n/a | n/a |
| acyclicity | vulns_per_kloc | 0 | n/a | n/a | n/a | n/a |
| acyclicity | smells_per_kloc | 0 | n/a | n/a | n/a | n/a |
| acyclicity | complexity_per_kloc | 0 | n/a | n/a | n/a | n/a |
| acyclicity | cognitive_complexity_per_kloc | 0 | n/a | n/a | n/a | n/a |
| acyclicity | duplicated_lines_density | 0 | n/a | n/a | n/a | n/a |
| acyclicity | sonar_runtime_s | 0 | n/a | n/a | n/a | n/a |
| stability | bugfix_ratio | 30 | -0.1562 | 0.4097 | -0.0994 | 0.6011 |
| stability | bugs_per_kloc | 0 | n/a | n/a | n/a | n/a |
| stability | vulns_per_kloc | 0 | n/a | n/a | n/a | n/a |
| stability | smells_per_kloc | 0 | n/a | n/a | n/a | n/a |
| stability | complexity_per_kloc | 0 | n/a | n/a | n/a | n/a |
| stability | cognitive_complexity_per_kloc | 0 | n/a | n/a | n/a | n/a |
| stability | duplicated_lines_density | 0 | n/a | n/a | n/a | n/a |
| stability | sonar_runtime_s | 0 | n/a | n/a | n/a | n/a |
| cohesion | bugfix_ratio | 30 | -0.1217 | 0.5219 | -0.0977 | 0.6076 |
| cohesion | bugs_per_kloc | 0 | n/a | n/a | n/a | n/a |
| cohesion | vulns_per_kloc | 0 | n/a | n/a | n/a | n/a |
| cohesion | smells_per_kloc | 0 | n/a | n/a | n/a | n/a |
| cohesion | complexity_per_kloc | 0 | n/a | n/a | n/a | n/a |
| cohesion | cognitive_complexity_per_kloc | 0 | n/a | n/a | n/a | n/a |
| cohesion | duplicated_lines_density | 0 | n/a | n/a | n/a | n/a |
| cohesion | sonar_runtime_s | 0 | n/a | n/a | n/a | n/a |

## Strongest Correlations

| X | Y | Method | r | |r| strength |
|---|---|---|---:|---|
| agq_score | bugfix_ratio | spearman | -0.1684 | very_weak |
| agq_score | bugfix_ratio | pearson | -0.1680 | very_weak |
| stability | bugfix_ratio | pearson | -0.1562 | very_weak |
| acyclicity | bugfix_ratio | spearman | 0.1408 | very_weak |
| cohesion | bugfix_ratio | pearson | -0.1217 | very_weak |
| stability | bugfix_ratio | spearman | -0.0994 | very_weak |
| cohesion | bugfix_ratio | spearman | -0.0977 | very_weak |
| acyclicity | bugfix_ratio | pearson | 0.0402 | very_weak |
| modularity | bugfix_ratio | pearson | -0.0278 | very_weak |
| modularity | bugfix_ratio | spearman | -0.0020 | very_weak |

## Mediation Analysis (AGQ → Mediator → Outcome)

| Chain | r(a) | p(a) | r(b) | p(b) | r(c) direct | Indirect | Sobel z | Sobel p | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| agq_score → complexity_per_kloc → bugs_per_kloc | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | None |
| agq_score → complexity_per_kloc → bugfix_ratio | n/a | n/a | n/a | n/a | -0.1680 | n/a | n/a | n/a | None |
| agq_score → cognitive_complexity_per_kloc → bugs_per_kloc | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | None |
| agq_score → cognitive_complexity_per_kloc → bugfix_ratio | n/a | n/a | n/a | n/a | -0.1680 | n/a | n/a | n/a | None |
| agq_score → smells_per_kloc → bugs_per_kloc | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | None |
| agq_score → smells_per_kloc → bugfix_ratio | n/a | n/a | n/a | n/a | -0.1680 | n/a | n/a | n/a | None |

