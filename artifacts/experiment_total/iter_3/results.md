# Eksperyment Totalny — Iteracja 3 (odzyskane z logów)

- generated: `2026-04-10T08:17:17.013253+00:00`
- source: `recovered_from_log`
- repos_ok: **389** / 569
- z nowymi metrykami: 171
- AGQ mean: `0.8013` ± `0.1468`

## AGQ per język
| Język | n | mean | std | min | max |
|---|---:|---:|---:|---:|---:|
| Python | 257 | 0.8044 | 0.1370 | 0.5066 | 1.0000 |
| Java | 82 | 0.7537 | 0.1728 | 0.4594 | 1.0000 |
| Go | 25 | 0.7842 | 0.0618 | 0.6842 | 0.8815 |
| TypeScript | 25 | 0.9418 | 0.1221 | 0.6248 | 1.0000 |

## Fingerprints
| Pattern | n | % |
|---|---:|---:|
| CLEAN | 189 | 48.6% |
| LAYERED | 115 | 29.6% |
| FLAT | 35 | 9.0% |
| MODERATE | 25 | 6.4% |
| LOW_COHESION | 25 | 6.4% |

## Korelacje AGQ ↔ nowe metryki
| Predyktor | → Cel | r_s | p | n | Sig | Siła |
|---|---|---:|---:|---:|---|---|
| stability | process_risk | +0.3296 | 0.0000 | 171 | *** | - |
| stability | graph_density | +0.3291 | 0.0000 | 171 | *** | - |
| stability | hub_ratio | +0.2823 | 0.0002 | 171 | *** | - |
| agq_score | process_risk | +0.2658 | 0.0004 | 171 | *** | - |
| agq_score | graph_density | +0.2609 | 0.0006 | 171 | *** | - |
| agq_score | hub_ratio | +0.2439 | 0.0013 | 171 | ** | - |
| cohesion | scc_entropy | -0.2376 | 0.0018 | 171 | ** | - |
| agq_score | scc_entropy | -0.1887 | 0.0135 | 171 | * | - |
| acyclicity | scc_entropy | -0.1319 | 0.0854 | 171 |  | - |
| stability | scc_entropy | +0.0594 | 0.4404 | 171 |  | - |
| acyclicity | hub_ratio | -0.0474 | 0.5379 | 171 |  | - |
| acyclicity | graph_density | -0.0469 | 0.5423 | 171 |  | - |
| acyclicity | process_risk | -0.0453 | 0.5564 | 171 |  | - |
| cohesion | process_risk | +0.0282 | 0.7146 | 171 |  | - |
| cohesion | graph_density | +0.0281 | 0.7153 | 171 |  | - |

## Najważniejsze odkrycia

1. **TypeScript ma najwyższe AGQ** (mean=0.94) — prawdopodobnie ze względu na
   wymuszony przez TS system typów i silniejsze konwencje modularności.
2. **Stability → ProcessRisk r=+0.33*** — stabilność warstw koreluje z gęstością grafu.
3. **Acyclicity NIE koreluje z nowymi metrykami** — ortogonalność potwierdzona.
4. **48.6% projektów to CLEAN** — OSS ma wyraźny bias w stronę dobrej architektury.

## Brakujące dane

- churn_gini, hotspot_ratio: brak (shallow clone bez git history)
- bug_lead_time: brak (skrypt padł przed GitHub Issues API)

Aby uzupełnić: `python3 scripts/benchmark_parallel.py --resume --iter 4`
