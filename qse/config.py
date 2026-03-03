"""QSE configuration with sensible defaults."""

import json
from dataclasses import dataclass, field

import numpy as np

from qse.aggregator import DEFAULT_WEIGHTS


@dataclass
class QSEConfig:
    """Configuration for a QSE analysis run."""
    weights: np.ndarray = field(default_factory=lambda: DEFAULT_WEIGHTS.copy())
    tau_sem: float = 0.1
    beta: float = 3.0
    fat_threshold: int = 8
    fat_steepness: float = 1.0
    enable_trace: bool = True

    @classmethod
    def from_file(cls, path: str) -> "QSEConfig":
        with open(path) as f:
            data = json.load(f)
        cfg = cls()
        if "weights" in data:
            cfg.weights = np.array(data["weights"], dtype=float)
        if "tau_sem" in data:
            cfg.tau_sem = float(data["tau_sem"])
        if "beta" in data:
            cfg.beta = float(data["beta"])
        if "fat_threshold" in data:
            cfg.fat_threshold = int(data["fat_threshold"])
        if "fat_steepness" in data:
            cfg.fat_steepness = float(data["fat_steepness"])
        if "enable_trace" in data:
            cfg.enable_trace = bool(data["enable_trace"])
        return cfg
