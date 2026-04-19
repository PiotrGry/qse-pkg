"""TOML config loader for Sprint 0 gate.

Schema (qse-gate.toml):

    [gate]
    language = "python"                  # python | java | go (future)

    [layers]
    domain = ["src/domain/**"]
    application = ["src/application/**"]
    infrastructure = ["src/infra/**"]

    [[rules.layer_violation.forbidden]]
    from = "domain"
    to = "infrastructure"

    [[rules.boundary_leak.protected]]
    module = "src.payments.core.*"
    allowed_callers = ["src.payments.api.*"]

    [rules.cycle_new]
    mode = "any"                          # any | delta (delta requires base graph)
    enabled = true

    [telemetry]
    jsonl_path = "artifacts/gate-telemetry.jsonl"
    webhook_url = ""                      # optional
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    import tomllib  # type: ignore  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


@dataclass
class ForbiddenEdge:
    from_layer: str
    to_layer: str


@dataclass
class ProtectedModule:
    module: str                         # glob pattern (dotted)
    allowed_callers: List[str] = field(default_factory=list)


@dataclass
class CycleNewRule:
    enabled: bool = True
    mode: str = "any"                   # "any" | "delta"


@dataclass
class LayerViolationRule:
    enabled: bool = True
    forbidden: List[ForbiddenEdge] = field(default_factory=list)


@dataclass
class BoundaryLeakRule:
    enabled: bool = True
    protected: List[ProtectedModule] = field(default_factory=list)


@dataclass
class TelemetryConfig:
    jsonl_path: Optional[str] = None
    webhook_url: Optional[str] = None


DEFAULT_SCAN_EXCLUDES: list[str] = [
    "**/.git/**",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/node_modules/**",
    "**/target/**",             # Rust build output
    "**/build/**",
    "**/dist/**",
    "**/_obsolete/**",
    "**/artifacts/**",
    "**/results/**",
    "**/experiments/**",
    "**/papiers/**",
    "**/*.egg-info/**",
    "**/venv/**",
    "**/.venv/**",
    "**/site-packages/**",
]


@dataclass
class ScanConfig:
    """File-scope filter for graph construction.

    Default `include` matches every .py file; the default `exclude` list
    knocks out vendored trees, build output, generated artefacts, and
    research scratch space — the noise that makes a 200-module product
    look like a 2500-module one. Projects with unusual layouts can
    override both lists explicitly in `[scan]`.
    """
    include: list[str] = field(default_factory=lambda: ["**/*.py"])
    exclude: list[str] = field(default_factory=lambda: list(DEFAULT_SCAN_EXCLUDES))


@dataclass
class GateConfig:
    language: str = "python"
    layers: dict = field(default_factory=dict)       # layer_name -> [glob]
    scan: ScanConfig = field(default_factory=ScanConfig)
    cycle_new: CycleNewRule = field(default_factory=CycleNewRule)
    layer_violation: LayerViolationRule = field(default_factory=LayerViolationRule)
    boundary_leak: BoundaryLeakRule = field(default_factory=BoundaryLeakRule)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)


def load_config(path: str | Path) -> GateConfig:
    path = Path(path)
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    gate = raw.get("gate", {})
    layers_raw = raw.get("layers", {})
    rules = raw.get("rules", {})
    telemetry = raw.get("telemetry", {})

    layers: dict[str, list[str]] = {}
    for name, globs in layers_raw.items():
        if not isinstance(globs, list):
            raise ValueError(
                f"[layers].{name} must be a list of glob strings, got {type(globs).__name__}. "
                f"Example: {name} = [\"src/{name}/**\"]"
            )
        layers[name] = [str(g) for g in globs]

    cycle_raw = rules.get("cycle_new", {})
    mode = str(cycle_raw.get("mode", "any"))
    if mode not in {"any", "delta"}:
        raise ValueError(
            f"[rules.cycle_new].mode must be 'any' or 'delta', got {mode!r}."
        )
    cycle = CycleNewRule(
        enabled=bool(cycle_raw.get("enabled", True)),
        mode=mode,
    )

    lv_raw = rules.get("layer_violation", {})
    forbidden_list = lv_raw.get("forbidden", [])
    lv = LayerViolationRule(
        enabled=bool(lv_raw.get("enabled", True)),
        forbidden=[
            ForbiddenEdge(from_layer=x["from"], to_layer=x["to"])
            for x in forbidden_list
        ],
    )

    bl_raw = rules.get("boundary_leak", {})
    protected_list = bl_raw.get("protected", [])
    bl = BoundaryLeakRule(
        enabled=bool(bl_raw.get("enabled", True)),
        protected=[
            ProtectedModule(
                module=x["module"],
                allowed_callers=list(x.get("allowed_callers", [])),
            )
            for x in protected_list
        ],
    )

    tel = TelemetryConfig(
        jsonl_path=telemetry.get("jsonl_path"),
        webhook_url=telemetry.get("webhook_url"),
    )

    scan_raw = raw.get("scan", {})
    include = scan_raw.get("include")
    exclude = scan_raw.get("exclude")
    scan_cfg = ScanConfig()
    if include is not None:
        if not isinstance(include, list):
            raise ValueError("[scan].include must be a list of glob strings.")
        scan_cfg.include = [str(g) for g in include]
    if exclude is not None:
        if not isinstance(exclude, list):
            raise ValueError("[scan].exclude must be a list of glob strings.")
        scan_cfg.exclude = [str(g) for g in exclude]

    return GateConfig(
        language=str(gate.get("language", "python")),
        layers=layers,
        scan=scan_cfg,
        cycle_new=cycle,
        layer_violation=lv,
        boundary_leak=bl,
        telemetry=tel,
    )
