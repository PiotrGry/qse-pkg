"""LLM code generation loop with QSE quality gate."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from qse.config import QSEConfig
from qse.gate import GateResult, GateRules, quality_gate


@dataclass
class GenerationAttempt:
    """Record of a single generation attempt."""
    attempt: int
    result: GateResult
    prompt_used: str


def _read_specs(template_dir: str) -> str:
    """Read all spec/*.md files and concatenate as LLM context."""
    spec_dir = os.path.join(template_dir, "spec")
    if not os.path.isdir(spec_dir):
        return ""
    parts = []
    for fname in sorted(os.listdir(spec_dir)):
        if fname.endswith(".md"):
            path = os.path.join(spec_dir, fname)
            with open(path) as f:
                parts.append(f"## {fname}\n{f.read()}")
    return "\n\n".join(parts)


def _build_initial_prompt(specs: str, readme_path: str) -> str:
    """Build the initial generation prompt from specs and README."""
    parts = [
        "Generate a DDD-structured Python project based on these specifications.",
        "Follow clean DDD layering: domain contains business logic, "
        "application orchestrates, presentation delegates to application.",
        "",
    ]
    if os.path.isfile(readme_path):
        with open(readme_path) as f:
            parts.append(f"# Project Rules\n{f.read()}")
    parts.append(f"# Specifications\n{specs}")
    return "\n".join(parts)


def generate_and_validate(
    template_dir: str,
    llm_callable: Callable[[str], str],
    rules: Optional[GateRules] = None,
    config: Optional[QSEConfig] = None,
    max_retries: Optional[int] = None,
    output_dir: Optional[str] = None,
) -> Tuple[bool, GateResult, List[GenerationAttempt]]:
    """Run the generate-validate-retry loop.

    Args:
        template_dir: Path to the DDD scaffold template.
        llm_callable: Function that takes a prompt string, returns generated code string.
                      The callable is responsible for writing files to output_dir.
        rules: Quality gate rules. Loaded from template qse_rules.json if None.
        config: QSE analysis config. Uses defaults if None.
        max_retries: Override rules.max_retries if set.
        output_dir: Directory to analyze. Defaults to template_dir.

    Returns:
        (passed, final_result, attempts)
    """
    if rules is None:
        rules_path = os.path.join(template_dir, "qse_rules.json")
        if os.path.isfile(rules_path):
            rules = GateRules.from_file(rules_path)
        else:
            rules = GateRules()

    retries = max_retries if max_retries is not None else rules.max_retries
    target_dir = output_dir or template_dir

    specs = _read_specs(template_dir)
    readme = os.path.join(template_dir, "README.md")
    prompt = _build_initial_prompt(specs, readme)

    attempts: List[GenerationAttempt] = []
    best_result: Optional[GateResult] = None

    for i in range(retries + 1):
        # Call LLM to generate code
        llm_callable(prompt)

        # Run quality gate
        result = quality_gate(target_dir, rules, config)
        attempts.append(GenerationAttempt(attempt=i, result=result, prompt_used=prompt))

        if best_result is None or result.qse_total > best_result.qse_total:
            best_result = result

        if result.passed:
            return True, result, attempts

        # Build retry prompt with feedback
        prompt = (
            f"{prompt}\n\n"
            f"# QSE Feedback (attempt {i + 1}/{retries + 1})\n"
            f"{result.feedback_prompt}"
        )

    return False, best_result, attempts
