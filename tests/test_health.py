"""Smoke tests for qse health."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import networkx as nx
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_compute_health_on_self() -> None:
    """qse health on qse-pkg itself returns sane numbers."""
    from qse.health import compute_health
    rep = compute_health(str(REPO_ROOT))
    assert rep.nodes > 50, "qse-pkg has > 50 modules"
    assert rep.edges > 0
    assert 0.0 <= rep.agq <= 1.0
    assert 0.0 <= rep.cycle_pct <= 100.0
    assert 0.0 <= rep.isolated_pct <= 100.0
    assert rep.language == "python"
    assert rep.top_hubs, "should have at least one hub"


def test_compute_health_filters_artifacts() -> None:
    """Vendored / build paths must be filtered from the graph."""
    from qse.health import compute_health, SKIP_PARTS
    rep = compute_health(str(REPO_ROOT))
    # No node should contain a SKIP_PARTS segment in its dotted name.
    # We can't verify directly without graph access, but isolated_pct
    # should be reasonable (qse-pkg has tightly-coupled internals).
    assert rep.isolated_pct < 60, (
        f"isolated_pct {rep.isolated_pct} too high; vendored paths leaking?")


def test_render_text_smoke() -> None:
    """Text rendering produces expected sections."""
    from qse.health import compute_health, render_text
    rep = compute_health(str(REPO_ROOT))
    text = render_text(rep)
    assert "QSE Health Report" in text
    assert "AGQ score" in text
    assert "Topology" in text


def test_health_cli_json() -> None:
    """`qse health --json` produces valid JSON with expected keys."""
    r = subprocess.run(
        [sys.executable, "-m", "qse.cli", "health", str(REPO_ROOT), "--json"],
        capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    for key in ("agq", "modularity", "acyclicity", "stability", "cohesion",
                "nodes", "edges", "cycle_pct", "isolated_pct", "top_hubs"):
        assert key in payload, f"missing {key} in JSON output"


def test_percentile_computation() -> None:
    from qse.health import _percentile_of
    vals = [0.1, 0.2, 0.3, 0.4, 0.5]
    assert _percentile_of(0.3, vals) == 60.0  # 3 of 5 ≤ 0.3
    assert _percentile_of(0.0, vals) == 0.0
    assert _percentile_of(1.0, vals) == 100.0
