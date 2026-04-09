# Benchmark Results

Data: 2026-03-06

## Konfiguracja wspolna

- przypadki: `1000:20000:100,3000:80000:180,3500:100000:220`
- seed: `42`
- kontrola poprawnosci: identyczny zbior `violations` + identyczny `score` (strict)

## Run A - baseline `exp4` (aktualna implementacja w repo)

Komenda:

```bash
python3 -u optimizations/constraints_benchmark/benchmark.py \
  --cases "1000:20000:100,3000:80000:180,3500:100000:220" \
  --repeats 8 \
  --seed 42 \
  --baseline-mode exp4
```

Wyniki:

| Case | base_med (s) | opt_med (s) | speedup |
|---|---:|---:|---:|
| 1000n:20000e:100r | 0.215058 | 0.216028 | 1.00x |
| 3000n:80000e:180r | 1.637967 | 1.700988 | 0.96x |
| 3500n:100000e:220r | 2.366528 | 2.453381 | 0.96x |
| **Median** |  |  | **0.96x** |

Wniosek: aktualny checker `exp4` jest juz zoptymalizowany i bardzo zblizony do nowej metody.

## Run B - baseline `legacy` (naiwna stara logika O(rules*edges))

Komenda:

```bash
python3 -u optimizations/constraints_benchmark/benchmark.py \
  --cases "1000:20000:100,3000:80000:180,3500:100000:220" \
  --repeats 6 \
  --seed 42 \
  --baseline-mode legacy
```

Wyniki:

| Case | base_med (s) | opt_med (s) | speedup |
|---|---:|---:|---:|
| 1000n:20000e:100r | 1.182195 | 0.217442 | 5.44x |
| 3000n:80000e:180r | 8.573858 | 1.608368 | 5.33x |
| 3500n:100000e:220r | 13.083110 | 2.466042 | 5.31x |
| **Median** |  |  | **5.33x** |

Wniosek: nowa metoda jest wyraznie lepsza od naiwnej wersji legacy.

