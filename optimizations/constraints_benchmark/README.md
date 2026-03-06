# Constraints Benchmark (Baseline vs Optimization)

Ten folder jest celowo odseparowany od produkcyjnego kodu `qse/`.

Cel:
- porownac stara metode z nowa optymalizacja,
- na identycznych danych i identycznych regułach,
- z twarda walidacja, ze wyniki sa 1:1 zgodne.

## Co jest porownywane

- **Baseline (stara implementacja):** `experiments/exp4_constraints/run.py::check_constraints`
- **Optimized:** `optimizations/constraints_benchmark/optimized_constraints.py::check_constraints_optimized`

## Gwarancja porownywalnosci

Benchmark wymusza:
1. Ten sam graf i te same constraints dla obu metod.
2. Deterministyczna generacja danych (`--seed`).
3. Sprawdzenie identycznosci:
   - zbioru violations,
   - constraint score.

Tryb baseline:
- `--baseline-mode auto` (domyslny): bierze checker z `exp4`, fallback na legacy.
- `--baseline-mode exp4`: wymusza checker z `exp4`.
- `--baseline-mode legacy`: wymusza naiwna stara logike O(rules*edges).

Jesli wynik nie jest identyczny, benchmark przerywa wykonanie (`AssertionError`).

## Jak uruchomic

Z katalogu repo:

```bash
python3 optimizations/constraints_benchmark/benchmark.py
```

Wersja krotsza (szybki test):

```bash
python3 optimizations/constraints_benchmark/benchmark.py \
  --cases "200:2000:30,800:10000:60" \
  --repeats 10 \
  --seed 42 \
  --baseline-mode auto
```

Wersja ciezsza (bardziej reprezentatywna):

```bash
python3 optimizations/constraints_benchmark/benchmark.py \
  --cases "500:6000:60,2000:30000:120,4000:70000:180" \
  --repeats 20 \
  --seed 42 \
  --baseline-mode legacy
```

## Interpretacja

- `base_med` i `opt_med` to mediany czasu dla jednego przebiegu checkera.
- `speedup` > 1.0 oznacza, ze nowa metoda jest szybsza.
- Najwazniejsze: wynik jest uznany za poprawny tylko przy 100% zgodnosci violations + score.

Przykladowe uruchomienia i wyniki referencyjne sa w `RESULTS.md`.
