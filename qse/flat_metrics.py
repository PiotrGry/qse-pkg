"""
Flat Metrics — metryki wykrywajace brak struktury hierarchicznej
================================================================
Kwiecien 2026 — dedykowane dla Pythona gdzie FLAT spaghetti jest
niewidoczne dla AGQ (youtube-dl: ratio=1.35 mimo braku struktury)

FLAT_RATIO : float [0,1]
    Odsetek wezlow ktore sa w "plytkich" namespacach (depth <= 2).
    youtube-dl: prawie wszystko w youtube_dl/ depth=2 -> FLAT_RATIO~0.9
    netbox:     klasy w netbox/dcim/models/ depth=3-4 -> FLAT_RATIO~0.1
    Interpretacja: NIZSZY = LEPSZY (bardziej hierarchiczny)
    Dla AGQ: uzywamy (1 - FLAT_RATIO) jako skladowa

MAX_NS_DEPTH : float [0,1]
    Maksymalna glebokos hierarchii pakietow (znormalizowana).
    Mierzy czy projekt MA hierarchie (chocby w jednym miejscu).
    youtube-dl: max_depth=2 -> 0.25
    netbox:     max_depth=5 -> 0.625
    Roznica od NS_depth (srednia): max jest odporne na duze plytkie moduły

LEAF_CONCENTRATION : float [0,1]
    Gini wspolczynnik dla wezlow na najplytszym poziomie.
    Wysoki = duzo klas skupionych w jednym plytkim namespace (spaghetti).
    Niski = klasy rozlozone po roznych, rownie licznych ns.
"""

import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional

MAX_DEPTH = 8


def _pkg_depth(fqn: str) -> int:
    parts = fqn.split(".")
    return max(0, len(parts) - 1)


def _parent_ns(fqn: str) -> Optional[str]:
    parts = fqn.split(".")
    return ".".join(parts[:-1]) if len(parts) >= 2 else None


def _gini(values: List[float]) -> float:
    if not values or len(values) < 2:
        return 0.0
    arr = sorted(values)
    n = len(arr)
    total = sum(arr)
    if total == 0:
        return 0.0
    cumsum = sum((i + 1) * v for i, v in enumerate(arr))
    return (2 * cumsum) / (n * total) - (n + 1) / n


@dataclass
class FlatMetricsResult:
    flat_ratio: float        # % wezlow z depth<=2 [0,1] — nizszy=lepszy
    flat_score: float        # 1 - flat_ratio — wyzszy=lepszy (do AGQ)
    max_ns_depth: float      # znorm. max glebokosc [0,1]
    mean_ns_depth: float     # znorm. srednia glebokosc [0,1]
    leaf_concentration: float  # Gini wezlow na plytkim poziomie [0,1]
    n_flat_nodes: int        # ile wezlow ma depth<=2
    n_internal: int


SHALLOW_THRESHOLD = 2  # depth <= 2 = "flat"


def compute_flat_metrics(graph_json: str,
                         shallow_threshold: int = SHALLOW_THRESHOLD) -> FlatMetricsResult:
    """
    Oblicza metryki flat na grafie z scan_to_graph_json().
    Tylko wezly wewnetrzne.
    """
    g = json.loads(graph_json)
    internal = [n["id"] for n in g.get("nodes", []) if n.get("internal", False)]

    if not internal:
        return FlatMetricsResult(1.0, 0.0, 0.0, 0.0, 0.0, 0, 0)

    depths = [_pkg_depth(fqn) for fqn in internal]
    n_flat = sum(1 for d in depths if d <= shallow_threshold)
    flat_ratio = n_flat / len(depths)
    flat_score = 1.0 - flat_ratio

    max_depth  = max(depths) if depths else 0
    mean_depth = sum(depths) / len(depths) if depths else 0

    max_ns_depth  = round(min(max_depth  / MAX_DEPTH, 1.0), 4)
    mean_ns_depth = round(min(mean_depth / MAX_DEPTH, 1.0), 4)

    # Leaf concentration: Gini dla wezlow w plytkich ns
    shallow_ns = Counter()
    for fqn in internal:
        d = _pkg_depth(fqn)
        if d <= shallow_threshold:
            ns = _parent_ns(fqn) or "__root__"
            shallow_ns[ns] += 1

    leaf_conc = _gini(list(shallow_ns.values())) if shallow_ns else 0.0

    return FlatMetricsResult(
        flat_ratio=round(flat_ratio, 4),
        flat_score=round(flat_score, 4),
        max_ns_depth=max_ns_depth,
        mean_ns_depth=mean_ns_depth,
        leaf_concentration=round(leaf_conc, 4),
        n_flat_nodes=n_flat,
        n_internal=len(internal),
    )
