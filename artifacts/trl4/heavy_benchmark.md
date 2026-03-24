# TRL4 Heavy Benchmark

- generated_at: `2026-03-07T08:19:02.428253+00:00`
- overall_pass: `True`

## Acceptance thresholds

- legacy median speedup >= `2.0`
- exp4 parity range: `0.8..1.2`

## Suite: legacy

- baseline_checker: `legacy_fallback_baseline`
- repeats: `6`
- median_speedup_x: `5.3701`

| Case | Baseline median (s) | Optimized median (s) | Speedup x |
|---|---:|---:|---:|
| 1000n:20000e:100r | 1.143660 | 0.212266 | 5.388 |
| 3000n:80000e:180r | 8.240651 | 1.579780 | 5.216 |
| 3500n:100000e:220r | 12.550320 | 2.337065 | 5.370 |

## Suite: exp4

- baseline_checker: `experiments.exp4_constraints.run::check_constraints`
- repeats: `8`
- median_speedup_x: `0.9934`

| Case | Baseline median (s) | Optimized median (s) | Speedup x |
|---|---:|---:|---:|
| 1000n:20000e:100r | 0.215868 | 0.219121 | 0.985 |
| 3000n:80000e:180r | 1.625606 | 1.576666 | 1.031 |
| 3500n:100000e:220r | 2.536013 | 2.552764 | 0.993 |

