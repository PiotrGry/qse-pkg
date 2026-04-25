"""Architectural hotspot detection — hybrid behavioral + structural metric.

A hotspot = file with high CHURN AND high STRUCTURAL IMPORTANCE.

Behavioral signal: number of commits touching the file in a time window
(Tornhill-style, Software Design X-Rays Ch. 1).

Structural signal: eigenvector centrality on the import graph — measures
"how much of the system depends on you (transitively)". Beats naive
fan_in × fan_out because it captures hub-of-hubs effect: file with one
direct importer that is itself central scores high.

The combined score = freq × centrality, normalized so both inputs land
in [0, 1] and the product also is. Hotspots = ranked by combined score.

This is the product moat versus competition:
- SonarQube: structural only (size, complexity), no churn awareness.
- CodeScene (Tornhill): behavioral only (churn × LOC), no graph structure.
- QSE hotspot: BOTH. Files high on one axis but low on the other are
  not hotspots; only the overlap matters.
"""
from __future__ import annotations

import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import networkx as nx


@dataclass
class HotspotEntry:
    file: str          # repo-relative path, e.g. "qse/cli.py"
    module: str        # dotted module name, e.g. "qse.cli"
    frequency: int     # commit count in window
    centrality: float  # eigenvector centrality on directed graph [0, 1]
    score: float       # freq_norm × centrality_norm  [0, 1]


def compute_change_frequency(
    repo_path: str, since: str = "1 year ago",
    head_ref: str | None = None,
) -> dict[str, int]:
    """Return {repo-relative-path: commit_count} for .py files changed
    in the time window. Uses git log --name-only.

    If `head_ref` is given, churn is anchored to that ref's history (so
    commits made after head_ref do not influence the ranking). This
    matters for gate-diff --check-hotspots when --head is not the
    current checkout.
    """
    cmd = ["git", "log", f"--since={since}", "--name-only",
           "--pretty=format:%H"]
    if head_ref:
        cmd.append(head_ref)
    r = subprocess.run(
        cmd,
        cwd=repo_path, capture_output=True, text=True, check=True,
    )
    counts: dict[str, int] = defaultdict(int)
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line or len(line) == 40:  # commit hash line
            continue
        if not line.endswith(".py"):
            continue
        # Filter same paths the scanner skips
        from qse.scanner import DEFAULT_EXCLUDES
        skip = any(seg in line.split("/") for seg in (
            "__pycache__", "_vendor", "vendor", "build", "dist",
            "node_modules", ".tox", ".venv", "venv", ".git",
            ".claude", ".gstack", ".pytest_cache", "artifacts",
        ))
        if skip:
            continue
        counts[line] += 1
    return dict(counts)


def _path_to_module(repo_relative: str) -> str:
    """Convert 'pkg/sub/mod.py' → 'pkg.sub.mod'. Strips __init__.py."""
    p = Path(repo_relative).with_suffix("")
    if p.name == "__init__":
        p = p.parent
    return ".".join(p.parts)


def _eigenvector_centrality_safe(G: nx.DiGraph) -> dict[str, float]:
    """Centrality measuring 'depended-on hub' importance.

    Convention: in QSE's import graph, edge importer→importee. A
    "depended-on hub" has many incoming edges (many things import it).

    Eigenvector centrality on a DiGraph counts a node's importance as
    proportional to importance of nodes pointing TO it. So computed on
    the original graph, central nodes are exactly depended-on hubs —
    no reversal needed.

    Falls back to PageRank for graphs where eigenvector iteration fails
    to converge (disconnected, no clear dominant eigenvector).
    """
    if G.number_of_nodes() == 0:
        return {}
    try:
        return nx.eigenvector_centrality(G, max_iter=500, tol=1e-4)
    except (nx.PowerIterationFailedConvergence, nx.NetworkXError):
        return nx.pagerank(G, alpha=0.85)


def compute_hotspot_score(
    G: nx.DiGraph, freq_dict: dict[str, int],
) -> list[HotspotEntry]:
    """Combine git frequency (behavioral) with structural centrality.

    Score = freq_normalized × centrality_normalized. Both in [0, 1] so
    the product is also bounded. Files with only one signal score low —
    only the overlap is interesting.
    """
    centrality = _eigenvector_centrality_safe(G)
    if not centrality:
        return []
    max_cen = max(centrality.values()) or 1.0
    max_freq = max(freq_dict.values()) if freq_dict else 1

    # Map files → modules and join
    entries: list[HotspotEntry] = []
    seen_modules: set[str] = set()
    for file, freq in freq_dict.items():
        module = _path_to_module(file)
        if module not in centrality:
            continue
        if module in seen_modules:
            continue
        seen_modules.add(module)
        cen = centrality[module]
        score = (freq / max_freq) * (cen / max_cen)
        entries.append(HotspotEntry(
            file=file, module=module,
            frequency=freq, centrality=cen, score=score,
        ))

    entries.sort(key=lambda e: -e.score)
    return entries


def find_hotspots(
    repo_path: str,
    since: str = "1 year ago",
    top: int = 10,
) -> list[HotspotEntry]:
    """End-to-end: scan repo, compute frequency, compute centrality, rank.

    Returns top-N hotspots sorted by combined score.
    """
    from qse.scanner import scan_dependency_graph
    G = scan_dependency_graph(repo_path)
    freq = compute_change_frequency(repo_path, since=since)
    return compute_hotspot_score(G, freq)[:top]
