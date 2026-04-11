"""
Namespace Depth i Namespace Concentration (Gini)
================================================
Kwiecien 2026 — metryki per jezyk, neutralne wobec Java/Python

NS_DEPTH : float [0,1]
    Znormalizowana srednia glebokos hierarchii pakietow.
    youtube-dl: depth~2 -> niski; netbox: depth~4 -> wysoki.
    Normalizacja: depth / MAX_DEPTH (MAX_DEPTH=8 empirycznie).

NS_GINI : float [0,1]
    Gini coefficient dla liczby wezlow per namespace (1 poziom powyzej klasy).
    0.0 = wszystkie klasy w jednym namespace (flat spaghetti).
    1.0 = kazdy namespace ma dokladnie 1 klase (zbyt rozdrobnione).
    Dobra architektura: 0.3-0.7 (kilka namespaceow ze srednio ~10-50 klas).
"""

import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional


MAX_DEPTH = 8  # empiryczny sufit: com.company.app.domain.model.cargo.Cargo = 7


def _fqn_depth(fqn: str) -> int:
    """Glebokosc FQN: liczba segmentow minus 1 (klasa) = liczba segmentow pakietu."""
    parts = fqn.split(".")
    return max(0, len(parts) - 1)  # pomiajamy klase, liczymy pakiet


def _parent_namespace(fqn: str) -> Optional[str]:
    """Bezposredni namespace (jeden poziom powyzej klasy)."""
    parts = fqn.split(".")
    if len(parts) < 2:
        return None
    return ".".join(parts[:-1])


def _gini(values: List[float]) -> float:
    """Gini coefficient. 0=rownosc (wszystko w jednym), 1=maxymalna nierownos."""
    if not values or len(values) == 1:
        return 0.0
    arr = sorted(values)
    n = len(arr)
    cumsum = sum((i + 1) * v for i, v in enumerate(arr))
    total = sum(arr)
    if total == 0:
        return 0.0
    return (2 * cumsum) / (n * total) - (n + 1) / n


@dataclass
class NamespaceMetricsResult:
    ns_depth: float        # znormalizowana srednia glebokosc [0,1]
    ns_gini: float         # Gini wspolczynnik koncentracji [0,1]
    mean_depth: float      # surowa srednia glebokosc
    max_depth: int         # maksymalna glebokosc w projekcie
    n_namespaces: int      # liczba unikalnych namespaceow (poziom rodzica)
    n_internal: int        # liczba wezlow wewnetrznych
    median_ns_size: float  # mediana liczby klas per namespace


def compute_namespace_metrics(graph_json: str) -> NamespaceMetricsResult:
    """
    Oblicza NS_depth i NS_gini na grafie z scan_to_graph_json().
    Tylko wezly wewnetrzne (internal=True).
    """
    g = json.loads(graph_json)
    internal = [n["id"] for n in g.get("nodes", []) if n.get("internal", False)]

    if not internal:
        return NamespaceMetricsResult(0.0, 0.0, 0.0, 0, 0, 0, 0.0)

    # Glebokosc per wezel
    depths = [_fqn_depth(fqn) for fqn in internal]
    mean_depth = sum(depths) / len(depths)
    max_depth = max(depths)
    ns_depth = min(mean_depth / MAX_DEPTH, 1.0)

    # Koncentracja: ile klas per namespace (poziom bezposredniego rodzica)
    ns_counter = Counter()
    for fqn in internal:
        ns = _parent_namespace(fqn)
        if ns:
            ns_counter[ns] += 1

    counts = list(ns_counter.values())
    n_namespaces = len(counts)

    if not counts:
        return NamespaceMetricsResult(
            round(ns_depth, 4), 0.0, round(mean_depth, 2),
            max_depth, 0, len(internal), 0.0
        )

    # Gini na liczbie klas per namespace
    # Uwaga: niski Gini (rowne nspc) moze byc dobry LUB zly
    # youtube-dl: 1000 klas w 1 ns -> Gini=0 (maksymalnie flat)
    # netbox: ~30 klas per ns -> Gini umiarkowany
    # Wiec invertujemy: ns_gini_score = 1 - Gini gdy Gini<0.5, else Gini
    # Nie - uzyjemy surowego Gini i sprawdzmy korelacje

    g_coef = _gini(counts)

    # Mediana rozmiaru ns
    sorted_counts = sorted(counts)
    mid = len(sorted_counts) // 2
    median_ns_size = (sorted_counts[mid] if len(sorted_counts) % 2 == 1
                      else (sorted_counts[mid-1] + sorted_counts[mid]) / 2)

    return NamespaceMetricsResult(
        ns_depth=round(ns_depth, 4),
        ns_gini=round(g_coef, 4),
        mean_depth=round(mean_depth, 2),
        max_depth=max_depth,
        n_namespaces=n_namespaces,
        n_internal=len(internal),
        median_ns_size=round(median_ns_size, 1),
    )
