# AGQ Thesis Benchmark

- generated_at: `2026-03-07T08:05:28.289271+00:00`
- repos_target: `9`
- repos_with_agq: `9`
- repos_with_sonar: `9`

## Thesis Checks

| ID | Thesis | Result | Evidence |
|---|---|---|---|
| T1 | AGQ deterministic over repeated runs | PASS | max_score_delta=0.0000000000 (target <= 1e-9) |
| T2 | AGQ correlates stronger with defect proxy than Sonar maintainability | FAIL | predictor=code_smell_quality_score; |r(AGQ,defect_proxy)|=0.0570 vs |r(Sonar,defect_proxy)|=0.1260 |
| T3 | Complementarity: Sonar A but low AGQ exists | PASS | cases=5 (cucumber_diseases_python, cheese_quest_spaghetti, oddup_investors_spaghetti, ue4_component_boilerplate_generator, nickineering_spaghetti) |
| T4 | AGQ median runtime is lower than SonarQube median runtime | PASS | median_agq_s=0.007 vs median_sonar_s=11.200 |
| T5 | AGQ discriminates quality across heterogeneous repos | PASS | spread=0.1042, stddev=0.0355 |

## Correlations

- sonar predictor used: `code_smell_quality_score`
- pearson(AGQ, defect_proxy): `-0.0570`
- pearson(SonarPredictor, defect_proxy): `-0.1260`
- spearman(AGQ, SonarPredictor): `0.4833`

## Repo Results

| Repo | AGQ(mean) | AGQ(delta) | Sonar Maint | Bugs | Vulns | Smells | Defect proxy | AGQ time(s) | Sonar time(s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| python_code_disasters | 0.7071 | 0.000000 | A | 1 | 0 | 252 | 0.0000 | 0.297 | 18.998 |
| cucumber_diseases_python | 0.6688 | 0.000000 | A | 0 | 0 | 3 | 0.8571 | 0.003 | 10.921 |
| python_bad_project | 0.7318 | 0.000000 | A | 1 | 1 | 98 | 0.4444 | 0.045 | 16.938 |
| python_spaghetti | 0.7500 | 0.000000 | A | 0 | 0 | 1 | 0.0000 | 0.001 | 11.200 |
| cheese_quest_spaghetti | 0.6577 | 0.000000 | A | 3 | 0 | 600 | 0.0000 | 1.892 | 20.126 |
| oddup_investors_spaghetti | 0.6823 | 0.000000 | A | 0 | 0 | 35 | 0.0000 | 0.007 | 11.150 |
| ue4_component_boilerplate_generator | 0.6458 | 0.000000 | A | 1 | 0 | 9 | 0.0000 | 0.001 | 10.936 |
| nickineering_spaghetti | 0.6706 | 0.000000 | A | 1 | 0 | 16 | 0.0000 | 0.010 | 12.238 |
| python_anti_patterns | 0.7348 | 0.000000 | A | 0 | 0 | 2 | 0.0000 | 0.002 | 11.064 |

