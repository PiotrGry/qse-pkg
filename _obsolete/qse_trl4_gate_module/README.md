# qse/trl4_gate.py (obsolete)

Moved here 2026-04-19 during **Sprint 0 Slice 2b** (DDD decouple).

This was the original QSE quality gate: QSE threshold + forbidden-edge
constraints + ratchet baseline. It tightly coupled to `qse.presets.ddd.config`
and `qse.presets.ddd.pipeline`.

The product pivoted to the **AI-Drift Firewall** — axiom-backed rules gate
(CYCLE_NEW, LAYER_VIOLATION, BOUNDARY_LEAK), architecture-agnostic, TOML config.
The new gate lives at [qse/gate/](../../qse/gate/) with `qse-gate` entry point.

Per Sprint 0 design R-AGQ-1, AGQ is now **advisory**, not a blocker. The
`qse agq` subcommand still computes and prints the AGQ score; it just doesn't
block PRs.

The forbidden-edge constraint logic from `check_constraints_graph` and
`compute_constraint_score` is superseded by the rules engine in
[qse/gate/rules.py](../../qse/gate/rules.py). Ratchet baseline is replaced by
Δ mode (two-scan comparison via `--base-ref`).

**Test file moved alongside:** [../tests_removed/test_trl4_gate.py](../tests_removed/test_trl4_gate.py).

**Kept for:** git history reference, restoration if the rewrite has gaps.
