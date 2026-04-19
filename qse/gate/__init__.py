"""AI-Drift Firewall gate (Sprint 0).

Axiom-backed deterministic rules for CI/CD architecture gate.
Architecture-agnostic: no DDD, no AGQ blocker — AGQ stays advisory.

Public API:
    load_config(path) -> GateConfig
    run_gate(repo_path, config) -> GateResult
"""

from qse.gate.config import GateConfig, load_config
from qse.gate.rules import GateResult, RuleViolation, run_gate

__all__ = [
    "GateConfig",
    "GateResult",
    "RuleViolation",
    "load_config",
    "run_gate",
]
