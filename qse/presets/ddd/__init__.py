"""DDD (Domain-Driven Design) preset for QSE.

**STATUS: DEPRECATED (2026-04-18) — NOT IN MAIN PRODUCT FLOW.**

Per project decision: DDD is an imposed architecture by design and biases
architectural metrics in favor of DDD-patterned codebases. The AI-drift firewall
product (Sprint 0+) does NOT use this preset.

This module remains in place only because qse/cli.py and qse/trl4_gate.py
currently import QSEConfig + analyze_repo from here. Sprint 0 cleanup (TODOS.md
T6) will decouple those callers and move this entire module to _obsolete/.

Do NOT add new callers. Do NOT extend this preset.

Originally provided DDD-specific detectors (anemic entity, fat service,
zombie entity, layer violation), sub-metrics (S, T_ddd, G, E, Risk), and pipeline.
Activated when layer_map is configured or domain/ directory exists.
"""
