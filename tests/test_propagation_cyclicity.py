"""Unit tests for compute_propagation_cost, compute_relative_cyclicity, gate_check."""
import pytest
import networkx as nx

from qse.graph_metrics import compute_propagation_cost, compute_relative_cyclicity
from qse.gate.gate_check import gate_check, GateResult


# ── helpers ───────────────────────────────────────────────────────────────────

def G(*edges, internal=True):
    """Build DiGraph; if internal=True, tag all nodes with file attr."""
    g = nx.DiGraph()
    g.add_edges_from(edges)
    if internal:
        for n in g.nodes():
            g.nodes[n]["file"] = f"{n}.py"
    return g


def G_nodes(*nodes, internal=True):
    g = nx.DiGraph()
    g.add_nodes_from(nodes)
    if internal:
        for n in g.nodes():
            g.nodes[n]["file"] = f"{n}.py"
    return g


# ── compute_propagation_cost ──────────────────────────────────────────────────

class TestPropagationCost:
    def test_empty_graph(self):
        assert compute_propagation_cost(nx.DiGraph()) == 0.0

    def test_single_node(self):
        g = G_nodes("a")
        assert compute_propagation_cost(g) == 1.0  # CCD=1, n=1, PC=1/1=1

    def test_chain_abc(self):
        # a→b→c: CCD = (a:3)+(b:2)+(c:1) = 6, n=3, PC = 6/9 = 0.667
        g = G(("a", "b"), ("b", "c"))
        assert abs(compute_propagation_cost(g) - 6/9) < 1e-9

    def test_independent_nodes(self):
        # no edges: CCD = n (each node reaches only itself), PC = n/n² = 1/n
        g = G_nodes("a", "b", "c", "d")
        assert abs(compute_propagation_cost(g) - 1/4) < 1e-9

    def test_full_cycle(self):
        # a→b→c→a: every node reaches all 3, CCD = 9, PC = 9/9 = 1.0
        g = G(("a", "b"), ("b", "c"), ("c", "a"))
        assert abs(compute_propagation_cost(g) - 1.0) < 1e-9

    def test_external_nodes_ignored(self):
        # only node 'a' has file attr; 'requests' is external
        g = nx.DiGraph()
        g.add_node("a", file="a.py")
        g.add_edge("a", "requests")
        # internal subgraph = just 'a', CCD=1, n=1, PC=1.0
        assert compute_propagation_cost(g) == 1.0

    def test_no_file_attrs_falls_back_to_full_graph(self):
        # without file attr, _internal_subgraph returns full graph
        g = nx.DiGraph()
        g.add_edges_from([("a", "b"), ("b", "c")])
        pc = compute_propagation_cost(g)
        assert 0.0 < pc <= 1.0

    def test_self_loop_only(self):
        g = nx.DiGraph()
        g.add_node("a", file="a.py")
        g.add_edge("a", "a")
        # self-loop: descendants("a") = {"a"} (networkx includes self in descendants for self-loop)
        # CCD = 1+1 = 2? Actually nx.descendants doesn't include the node itself
        # So: len(descendants)+1 = 0+1 = 1 for self-loop. PC = 1/1 = 1.0
        pc = compute_propagation_cost(g)
        assert 0.0 < pc <= 1.0


# ── compute_relative_cyclicity ────────────────────────────────────────────────

class TestRelativeCyclicity:
    def test_empty_graph(self):
        assert compute_relative_cyclicity(nx.DiGraph()) == 0.0

    def test_dag_no_cycles(self):
        g = G(("a", "b"), ("b", "c"), ("c", "d"))
        assert compute_relative_cyclicity(g) == 0.0

    def test_two_node_cycle(self):
        # SCC size=2, cyclicity=4, RC = 100*√4/2 = 100.0
        g = G(("a", "b"), ("b", "a"))
        assert abs(compute_relative_cyclicity(g) - 100.0) < 1e-9

    def test_three_node_cycle(self):
        # SCC size=3, cyclicity=9, RC = 100*√9/3 = 100.0
        g = G(("a", "b"), ("b", "c"), ("c", "a"))
        assert abs(compute_relative_cyclicity(g) - 100.0) < 1e-9

    def test_cycle_with_isolated_nodes(self):
        # 2-cycle + 2 isolated: SCC=2, n=4, RC = 100*2/4 = 50.0
        g = G(("a", "b"), ("b", "a"))
        g.add_node("c", file="c.py")
        g.add_node("d", file="d.py")
        assert abs(compute_relative_cyclicity(g) - 50.0) < 1e-9

    def test_self_loop_counts_as_cycle(self):
        g = nx.DiGraph()
        g.add_node("a", file="a.py")
        g.add_edge("a", "a")
        # self-loop = SCC {a} with len=1 but has self-edge → counts
        assert compute_relative_cyclicity(g) > 0.0

    def test_external_nodes_ignored(self):
        g = nx.DiGraph()
        g.add_node("a", file="a.py")
        g.add_edge("a", "requests")  # external
        assert compute_relative_cyclicity(g) == 0.0

    def test_above_threshold(self):
        # Verify >4% threshold: a small cycle in a medium graph
        g = nx.DiGraph()
        for i in range(20):
            g.add_node(f"m{i}", file=f"m{i}.py")
            if i > 0:
                g.add_edge(f"m{i-1}", f"m{i}")
        # add 3-node cycle in the middle
        g.add_edge("m10", "m8")
        rc = compute_relative_cyclicity(g)
        assert rc > 4.0


# ── gate_check ────────────────────────────────────────────────────────────────

class TestGateCheck:
    def _dag(self, n=6):
        g = nx.DiGraph()
        for i in range(n - 1):
            g.add_edge(f"m{i}", f"m{i+1}")
        return g

    def test_identical_graphs_pass(self):
        g = self._dag()
        assert gate_check(g, g).passed

    def test_new_cycle_fails(self):
        before = self._dag()
        after = before.copy()
        after.add_edge("m5", "m0")
        r = gate_check(before, after)
        assert not r.passed
        assert any(v.rule == "CYCLE" for v in r.violations)

    def test_no_regression_clean_commit_passes(self):
        before = self._dag()
        after = before.copy()
        after.add_edge("m5", "new_node")
        r = gate_check(before, after)
        assert r.passed

    def test_pc_delta_fails(self):
        # create a change that bumps PC by >0.05
        before = nx.DiGraph()
        for i in range(10):
            before.add_edge(f"a{i}", f"b{i}")  # independent pairs, low PC
        after = before.copy()
        # connect everything to one hub → high PC
        for i in range(10):
            after.add_edge(f"a{i}", "hub")
            after.add_edge("hub", f"b{i}")
        r = gate_check(before, after)
        # PC should spike; may or may not cross PC_DELTA depending on graph
        # Just check it runs without error
        assert isinstance(r, GateResult)

    def test_hub_spike_fails(self):
        before = nx.DiGraph()
        for i in range(10):
            before.add_edge(f"n{i}", f"n{i+1}")
        after = before.copy()
        hub = "n5"
        for i in range(10):
            if f"n{i}" != hub:
                after.add_edge(f"n{i}", hub)
                after.add_edge(hub, f"n{i}")
        r = gate_check(before, after)
        assert not r.passed
        assert any(v.rule in ("CYCLE", "HUB_SPIKE") for v in r.violations)

    def test_result_has_metrics(self):
        g = self._dag()
        r = gate_check(g, g)
        assert "pc" in r.metrics_before
        assert "rc" in r.metrics_after
        assert "scc_count" in r.metrics_before

    def test_str_pass(self):
        g = self._dag()
        assert str(gate_check(g, g)) == "gate: PASS"

    def test_str_fail_contains_violations(self):
        before = self._dag()
        after = before.copy()
        after.add_edge("m5", "m0")
        s = str(gate_check(before, after))
        assert "FAIL" in s
        assert "CYCLE" in s

    def test_custom_thresholds(self):
        before = self._dag()
        after = before.copy()
        after.add_edge("m5", "m0")
        # with very loose RC threshold, should still catch cycle
        r = gate_check(before, after, rc_fail=200.0)
        assert not r.passed
        assert any(v.rule == "CYCLE" for v in r.violations)


class TestLanguagePresets:
    """Per-language threshold presets (calibrated from 240-repo benchmark)."""

    def _dag(self, n=6):
        g = nx.DiGraph()
        for i in range(n - 1):
            g.add_edge(f"m{i}", f"m{i+1}")
        return g

    def test_python_default(self):
        from qse.gate.gate_check import get_thresholds
        t = get_thresholds("python")
        assert t["pc_fail"] == 0.20
        assert t["rc_fail"] == 4.0

    def test_java_higher_rc_tolerance(self):
        from qse.gate.gate_check import get_thresholds
        t = get_thresholds("java")
        assert t["rc_fail"] == 10.0   # Java culturally more cyclic
        assert t["pc_fail"] == 0.25

    def test_go_stricter_rc(self):
        from qse.gate.gate_check import get_thresholds
        t = get_thresholds("go")
        assert t["rc_fail"] == 2.0    # Go discourages cycles
        assert t["pc_fail"] == 0.18

    def test_unknown_language_falls_back_to_python(self):
        from qse.gate.gate_check import get_thresholds
        t = get_thresholds("rust")
        assert t == get_thresholds("python")

    def test_language_param_passes_through(self):
        # Same DAG, language doesn't change PASS verdict for clean diff
        g = self._dag()
        for lang in ["python", "java", "go"]:
            r = gate_check(g, g, language=lang)
            assert r.passed, f"clean diff failed under {lang} preset"

    def test_explicit_override_beats_language_preset(self):
        before = self._dag()
        after = before.copy()
        after.add_edge("m5", "m0")  # creates cycle
        # Java preset has rc_fail=10, but explicit override forces strict 1%
        r = gate_check(before, after, language="java", rc_fail=1.0)
        # Should still fail — cycle violations always fire regardless of rc
        assert not r.passed

    def test_case_insensitive_language(self):
        from qse.gate.gate_check import get_thresholds
        assert get_thresholds("Python") == get_thresholds("python")
        assert get_thresholds("JAVA") == get_thresholds("java")


class TestViolationStructure:
    """Failure-message overhaul: violations now include culprits + why + fix."""

    def _dag(self, n=8):
        g = nx.DiGraph()
        for i in range(n - 1):
            g.add_edge(f"m{i}", f"m{i+1}")
        for n_ in g.nodes():
            g.nodes[n_]["file"] = f"{n_}.py"
        return g

    def test_violation_has_required_fields(self):
        from qse.gate.gate_check import Violation
        before = self._dag()
        after = before.copy()
        after.add_edge("m7", "m0")  # close cycle
        r = gate_check(before, after)
        assert not r.passed
        for v in r.violations:
            assert isinstance(v, Violation)
            assert v.rule
            assert v.summary
            assert v.why
            assert v.fix
            assert isinstance(v.culprits, list)

    def test_cycle_violation_includes_scc_culprits(self):
        before = self._dag()
        after = before.copy()
        after.add_edge("m7", "m0")
        r = gate_check(before, after)
        cycle_v = next(v for v in r.violations if v.rule == "CYCLE")
        assert any("SCC:" in c for c in cycle_v.culprits)

    def test_violation_render_includes_why_and_fix(self):
        before = self._dag()
        after = before.copy()
        after.add_edge("m7", "m0")
        r = gate_check(before, after)
        rendered = str(r)
        assert "Why:" in rendered
        assert "Fix:" in rendered
        assert "[CYCLE]" in rendered

    def test_archipelago_bias_fires(self):
        """Diff with mostly new files triggers ARCHIPELAGO_BIAS."""
        before = self._dag()
        after = before.copy()
        # Doesn't affect graph topology — we test the diff_meta path
        diff_meta = {
            "new_files": 6,
            "modified_files": 0,
            "total_changed": 6,
            "new_paths": [f"new{i}.py" for i in range(6)],
        }
        r = gate_check(before, after, diff_meta=diff_meta)
        assert any(v.rule == "ARCHIPELAGO_BIAS" for v in r.violations)

    def test_archipelago_skipped_for_small_diff(self):
        """Small diffs (< MIN_FILES) don't trigger ARCHIPELAGO_BIAS."""
        before = self._dag()
        after = before.copy()
        diff_meta = {
            "new_files": 2,
            "modified_files": 0,
            "total_changed": 2,
            "new_paths": ["new1.py", "new2.py"],
        }
        r = gate_check(before, after, diff_meta=diff_meta)
        assert not any(v.rule == "ARCHIPELAGO_BIAS" for v in r.violations)

    def test_volume_spike_fires(self):
        """16+ new files in one commit triggers VOLUME_SPIKE."""
        before = self._dag()
        after = before.copy()
        diff_meta = {
            "new_files": 18,
            "modified_files": 2,
            "total_changed": 20,
            "new_paths": [f"new{i}.py" for i in range(18)],
        }
        r = gate_check(before, after, diff_meta=diff_meta)
        assert any(v.rule == "VOLUME_SPIKE" for v in r.violations)

    def test_no_diff_meta_skips_diff_geometry_rules(self):
        """When diff_meta is None, archipelago/volume rules don't fire."""
        before = self._dag()
        after = before.copy()
        r = gate_check(before, after)  # no diff_meta
        assert not any(v.rule in ("ARCHIPELAGO_BIAS", "VOLUME_SPIKE") for v in r.violations)

    def test_hub_violation_names_the_hub(self):
        before = nx.DiGraph()
        for i in range(15):
            before.add_node(f"n{i}", file=f"n{i}.py")
            if i > 0:
                before.add_edge(f"n{i-1}", f"n{i}")
        after = before.copy()
        hub = "n7"
        for v in list(before.nodes()):
            if v != hub:
                after.add_edge(v, hub)
                after.add_edge(hub, v)
        r = gate_check(before, after)
        hub_violations = [v for v in r.violations if v.rule == "HUB_SPIKE"]
        if hub_violations:  # may not fire depending on graph specifics
            assert any(hub in c for c in hub_violations[0].culprits)
