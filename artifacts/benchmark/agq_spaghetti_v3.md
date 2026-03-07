# AGQ Thesis Benchmark

- generated_at: `2026-03-07T22:13:14.927405+00:00`
- repos_target: `9`
- repos_with_agq: `9`
- repos_with_sonar: `9`

## Thesis Checks

| ID | Thesis | Result | Evidence |
|---|---|---|---|
| T1 | AGQ deterministic over repeated runs | PASS | max_score_delta=0.0000000000 (target <= 1e-9) |
| T2 | AGQ predicts code churn hotspots better than Sonar (hotspot_ratio) | FAIL | |r_s(AGQ,hotspot_ratio)|=1.0000 vs |r_s(Sonar,hotspot_ratio)|=1.0000 (n=2); r_s(AGQ,churn_gini)=-1.0000 |
| T3 | Complementarity: Sonar A but AGQ below mean-0.5*std exists | PASS | threshold=0.780 (mean=0.798 - 0.5*std=0.018); cases=3 (python_code_disasters, cucumber_diseases_python, nickineering_spaghetti) |
| T4 | AGQ median runtime is lower than SonarQube median runtime | PASS | median_agq_s=0.006 vs median_sonar_s=17.135 |
| T5 | AGQ discriminates quality across heterogeneous repos | FAIL | spread=0.0986, stddev=0.0358 |

## Correlations

- sonar predictor used: `code_smell_quality_score`
- pearson(AGQ, bugfix_ratio): `-0.0560`
- pearson(Sonar, bugfix_ratio): `-0.1260`
- spearman(AGQ, Sonar): `-0.1500`
- spearman(AGQ, hotspot_ratio): `-1.0000` (Sonar: `-1.0000`) n=2
- spearman(AGQ, churn_gini): `-1.0000` (Sonar: `-1.0000`)

## Repo Results

| Repo | AGQ(mean) | AGQ(delta) | Sonar Maint | Bugs | Smells | Bugfix% | Hotspot% | Churn Gini | AGQ time(s) | Sonar time(s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| python_code_disasters | 0.7543 | 0.000000 | A | 1 | 252 | 0.0000 | n/a | n/a | 0.321 | 22.090 |
| cucumber_diseases_python | 0.7666 | 0.000000 | A | 0 | 3 | 0.8571 | 0.3333 | 0.5238 | 0.002 | 16.139 |
| python_bad_project | 0.8474 | 0.000000 | A | 1 | 98 | 0.4444 | 0.0000 | 0.0705 | 0.048 | 18.056 |
| python_spaghetti | 0.8472 | 0.000000 | A | 0 | 1 | 0.0000 | n/a | n/a | 0.001 | 12.365 |
| cheese_quest_spaghetti | 0.7844 | 0.000000 | A | 3 | 600 | 0.0000 | n/a | n/a | 1.960 | 19.828 |
| oddup_investors_spaghetti | 0.7932 | 0.000000 | A | 0 | 35 | 0.0000 | n/a | n/a | 0.006 | 17.242 |
| ue4_component_boilerplate_generator | 0.8125 | 0.000000 | A | 1 | 9 | 0.0000 | n/a | n/a | 0.001 | 11.187 |
| nickineering_spaghetti | 0.7488 | 0.000000 | A | 1 | 16 | 0.0000 | n/a | n/a | 0.010 | 17.135 |
| python_anti_patterns | 0.8291 | 0.000000 | A | 0 | 2 | 0.0000 | n/a | n/a | 0.003 | 11.250 |

