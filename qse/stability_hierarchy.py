"""
E1: Stability Hierarchy Score (S_hierarchy)
===========================================
Kwiecień 2026 — eksperyment E1

Hipoteza: W dobrej architekturze (DDD, Clean, Hexagonal) hierarchy instability
jest poprawna: S(domain) < S(app) < S(infra)
tzn. domain jest NAJBARDZIEJ stabilna (wiele incomingów, mało outgoingów)
a infrastructure NAJMNIEJ stabilna (mało incomingów, wiele outgoingów).

Metryka: S_hierarchy ∈ [0.0, 1.0]
  1.0 = hierarchia w pełni poprawna (domain < app < infra)
  0.5 = częściowa (tylko część par w dobrej kolejności)
  0.0 = odwrócona hierarchia (brak architektonicznych granic)

Uzupełnienie: S_layer_detected (binary)
  True = znaleziono przynajmniej 2 warstwy ze słów kluczowych
  False = brak struktury warstwowej wykrywalnej po nazwach

Użycie:
    from qse.stability_hierarchy import compute_stability_hierarchy
    result = compute_stability_hierarchy(graph_json_str)
    # result.s_hierarchy, result.s_layer_detected, result.layer_instabilities
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Słowa kluczowe warstw — ordered od najbardziej stabilnej do instabilnej
# Priorytet: pierwsze dopasowanie wygrywa (order matters!)
# ---------------------------------------------------------------------------

LAYER_KEYWORDS: List[Tuple[str, List[str]]] = [
    # Warstwa domenowa — powinna być najbardziej stabilna
    ("domain", [
        "domain", "model", "entity", "entities", "aggregate",
        "valueobject", "vo", "core", "business", "ddd",
    ]),
    # Warstwa aplikacyjna — pośrednia
    ("application", [
        "application", "usecase", "usecases", "use_case",
        "service", "services", "command", "query", "handler",
        "port", "ports", "facade",
    ]),
    # Warstwa infrastrukturalna — powinna być najbardziej instabilna
    ("infrastructure", [
        "infrastructure", "infra", "adapter", "adapters",
        "persistence", "repository", "repositories", "dao",
        "jpa", "jdbc", "mybatis", "hibernate",
        "web", "rest", "http", "controller", "controllers",
        "api", "messaging", "kafka", "rabbitmq", "queue",
        "config", "configuration", "bootstrap", "impl",
    ]),
]

# Mapowanie: nazwa → poziom (0=domain=najbardziej stabilna, 2=infra=instabilna)
LAYER_LEVEL = {layer: i for i, (layer, _) in enumerate(LAYER_KEYWORDS)}


def classify_node(node_id: str) -> Optional[str]:
    """
    Klasyfikuje węzeł (fully-qualified class name) do warstwy architektonicznej.
    Przeszukuje segmenty nazwy pakietu (nie nazwę klasy — ostatni segment).
    Zwraca 'domain' | 'application' | 'infrastructure' | None.

    Algorytm trójfazowy (malejący priorytet):
    1. EXACT match: segment == keyword (np. segment "domain" → domain)
    2. STARTS_WITH: segment.startswith(keyword) (np. "domainmodel" → domain)
    3. CONTAINS: keyword in segment (ostateczność, np. "subdomain" → domain)

    Pierwsze dopasowanie w KAŻDEJ fazie wygrywa i przerywa poszukiwania.
    Segmenty sprawdzane w kolejności od lewej (bardziej ogólne) do prawej
    (bardziej szczegółowe) — pomijamy ostatni (nazwa klasy).

    Uwaga: "model" jako keyword domain może dawać false positives dla CRUD
    repos (np. MyBatis-generated DTOs w package "model"). Akceptowalna
    niedokładność przy n=13 — do poprawy gdy n>30.
    """
    parts = node_id.lower().split(".")
    if not parts:
        return None

    # Pakiet = wszystko poza ostatnim segmentem (nazwą klasy)
    package_parts = parts[:-1]
    if not package_parts:
        return None

    # FAZA 1: EXACT match — najwyższy priorytet
    for layer_name, keywords in LAYER_KEYWORDS:
        for part in package_parts:
            if part in keywords:
                return layer_name

    # FAZA 2: STARTS_WITH match
    for layer_name, keywords in LAYER_KEYWORDS:
        for kw in keywords:
            for part in package_parts:
                if part.startswith(kw):
                    return layer_name

    # FAZA 3: CONTAINS match (najniższy priorytet)
    for layer_name, keywords in LAYER_KEYWORDS:
        for kw in keywords:
            for part in package_parts:
                if kw in part and len(kw) >= 4:  # min 4 znaki żeby uniknąć false pos
                    return layer_name

    return None


def compute_instability(node_id: str,
                        fan_in: int,
                        fan_out: int) -> float:
    """Martin's instability: I = fan_out / (fan_in + fan_out). Range [0,1]."""
    total = fan_in + fan_out
    return fan_out / total if total > 0 else 0.5  # 0.5 = neutral gdy brak krawędzi


@dataclass
class StabilityHierarchyResult:
    """Wynik analizy hierarchii stabilności."""
    s_hierarchy: float          # [0,1] — główna metryka E1
    s_layer_detected: bool      # True gdy ≥2 warstwy wykryte
    n_layers_found: int         # liczba wykrytych warstw
    layer_instabilities: Dict[str, float]  # mean instability per warstwa
    layer_node_counts: Dict[str, int]      # liczba węzłów per warstwa
    hierarchy_correct: Dict[str, bool]     # która para jest poprawna
    unclassified_ratio: float   # jaki % węzłów nierozpoznanych


def compute_stability_hierarchy(graph_json: str) -> StabilityHierarchyResult:
    """
    Oblicza S_hierarchy na podstawie JSON grafu z scan_to_graph_json().

    Algorytm:
    1. Klasyfikuj każdy wewnętrzny węzeł do warstwy (domain/app/infra)
    2. Oblicz fan-in i fan-out dla każdego węzła
    3. Oblicz mean instability per warstwa
    4. Sprawdź czy hierarchia jest poprawna:
       domain_instability < app_instability < infra_instability
    5. S_hierarchy = % poprawnych par (z 3 możliwych: d<a, d<i, a<i)
    """
    g = json.loads(graph_json)
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])

    # Tylko węzły wewnętrzne
    internal_nodes = {n["id"] for n in nodes if n.get("internal", False)}

    # Oblicz fan-in i fan-out
    fan_in: Dict[str, int] = {n: 0 for n in internal_nodes}
    fan_out: Dict[str, int] = {n: 0 for n in internal_nodes}

    for src, dst in edges:
        if src in internal_nodes and dst in internal_nodes:
            fan_out[src] = fan_out.get(src, 0) + 1
            fan_in[dst]  = fan_in.get(dst, 0) + 1

    # Klasyfikuj węzły
    layer_nodes: Dict[str, List[str]] = {"domain": [], "application": [], "infrastructure": []}
    unclassified = 0

    for node_id in internal_nodes:
        layer = classify_node(node_id)
        if layer:
            layer_nodes[layer].append(node_id)
        else:
            unclassified += 1

    # Oblicz mean instability per warstwa
    layer_instabilities: Dict[str, float] = {}
    layer_node_counts: Dict[str, int] = {}

    for layer, node_list in layer_nodes.items():
        if not node_list:
            continue
        instabilities = [
            compute_instability(n, fan_in.get(n, 0), fan_out.get(n, 0))
            for n in node_list
        ]
        layer_instabilities[layer] = sum(instabilities) / len(instabilities)
        layer_node_counts[layer] = len(node_list)

    n_layers = len(layer_instabilities)
    s_layer_detected = n_layers >= 2

    # Oblicz S_hierarchy
    # Oczekiwana kolejność instability (rosnąco): domain < application < infrastructure
    hierarchy_correct: Dict[str, bool] = {}
    correct_pairs = 0
    total_pairs = 0

    pairs = [
        ("domain",      "application",    "d<a"),
        ("domain",      "infrastructure", "d<i"),
        ("application", "infrastructure", "a<i"),
    ]

    for layer_low, layer_high, pair_name in pairs:
        if layer_low in layer_instabilities and layer_high in layer_instabilities:
            is_correct = layer_instabilities[layer_low] < layer_instabilities[layer_high]
            hierarchy_correct[pair_name] = is_correct
            correct_pairs += int(is_correct)
            total_pairs += 1

    if total_pairs == 0:
        s_hierarchy = 0.0  # nie można ocenić — brak warstw
    else:
        s_hierarchy = correct_pairs / total_pairs

    unclassified_ratio = unclassified / len(internal_nodes) if internal_nodes else 1.0

    return StabilityHierarchyResult(
        s_hierarchy=round(s_hierarchy, 4),
        s_layer_detected=s_layer_detected,
        n_layers_found=n_layers,
        layer_instabilities={k: round(v, 4) for k, v in layer_instabilities.items()},
        layer_node_counts=layer_node_counts,
        hierarchy_correct=hierarchy_correct,
        unclassified_ratio=round(unclassified_ratio, 3),
    )
