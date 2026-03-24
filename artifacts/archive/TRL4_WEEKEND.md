# TRL4 Weekend Runbook

Cel: uzyskac powtarzalny pakiet dowodowy TRL4 (lab validation) dla QSE.

## Kryteria akceptacji

1. `qse trl4` przechodzi dla badanego repo przy polityce constraints.
2. Walidacja zintegrowana (`scripts/trl4_weekend_validation.py`) zwraca `overall_pass=true`.
3. Heavy benchmark (`scripts/trl4_heavy_benchmark.py`) zwraca:
   - legacy speedup >= 2.0x,
   - exp4 parity w zakresie 0.8x..1.2x.
4. Testy jednostkowe dla gate i metryk przechodza.

## Szybkie uruchomienie

```bash
pytest -q tests/test_metrics.py tests/test_gate.py tests/test_trl4_gate.py

python3 scripts/trl4_weekend_validation.py \
  --config scripts/trl4_weekend_config.json \
  --output-json artifacts/trl4/validation.json \
  --output-md artifacts/trl4/validation.md

python3 scripts/trl4_heavy_benchmark.py \
  --output-json artifacts/trl4/heavy_benchmark.json \
  --output-md artifacts/trl4/heavy_benchmark.md
```

## Artefakty dowodowe

- `artifacts/trl4/validation.json`
- `artifacts/trl4/validation.md`
- `artifacts/trl4/heavy_benchmark.json`
- `artifacts/trl4/heavy_benchmark.md`
