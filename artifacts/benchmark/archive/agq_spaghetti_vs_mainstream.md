# Spaghetti OSS vs Mainstream OSS - Comparison

- generated_at: `2026-03-07T08:05:28.289271+00:00`
- source_main: `artifacts/benchmark/agq_thesis_oss15.json`
- source_spaghetti: `artifacts/benchmark/agq_spaghetti_oss.json`

## Aggregate Comparison

| Metric | Mainstream OSS (15) | Spaghetti/Bad OSS (9) | Δ spaghetti-main |
|---|---:|---:|---:|
| AGQ mean | 0.6342 | 0.6943 | 0.0601 |
| AGQ median | 0.6378 | 0.6823 | 0.0445 |
| AGQ median runtime (s) | 0.156 | 0.007 | -0.149 |
| Sonar median runtime (s) | 14.012 | 11.200 | -2.813 |
| Code smells / KLOC mean | 12.20 | 43.04 | 30.85 |
| Code smells / KLOC median | 11.31 | 33.71 | 22.39 |
| Bugs / KLOC mean | 0.81 | 1.25 | 0.44 |
| Bugs / KLOC median | 0.38 | 0.04 | -0.33 |
| Graph nodes median | 97.0 | 7.0 | -90.0 |

## Spaghetti Repo Results

| Repo | Nodes | Edges | AGQ | Sonar Maint | Smells/KLOC | Bugs/KLOC |
|---|---:|---:|---:|---:|---:|---:|
| ue4_component_boilerplate_generator | 4 | 3 | 0.6458 | A | 84.11 | 9.35 |
| cheese_quest_spaghetti | 5 | 3 | 0.6577 | A | 74.71 | 0.37 |
| cucumber_diseases_python | 7 | 7 | 0.6688 | A | 33.71 | 0.00 |
| nickineering_spaghetti | 41 | 48 | 0.6706 | A | 19.54 | 1.22 |
| oddup_investors_spaghetti | 7 | 6 | 0.6823 | A | 95.89 | 0.00 |
| python_code_disasters | 33 | 14 | 0.7071 | A | 10.93 | 0.04 |
| python_bad_project | 46 | 72 | 0.7318 | A | 23.67 | 0.24 |
| python_anti_patterns | 7 | 5 | 0.7348 | A | 9.13 | 0.00 |
| python_spaghetti | 3 | 2 | 0.7500 | A | 35.71 | 0.00 |

## Notes

- Spaghetti set is much smaller (median graph nodes: 7 vs 97), so AGQ can be inflated by low structural complexity.
- Despite Sonar Maintainability=A almost everywhere, smells/KLOC and bugs/KLOC are clearly higher in spaghetti set.
- This comparison is exploratory, not a matched-cohort study.

