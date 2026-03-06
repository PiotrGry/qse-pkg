"""QSE analysis pipeline: scan → trace → graph → metrics → defects → report."""

from qse.presets.ddd.config import QSEConfig
from qse.scanner import scan_repo
from qse.tracer import trace_repo, TraceResult
from qse.hybrid_graph import build_hybrid_graph, graph_stats
from qse.presets.ddd.metrics import compute_all_metrics
from qse.presets.ddd.aggregator import compute_qse_total
from qse.presets.ddd.detectors import detect_all
from qse.test_quality import compute_test_quality
from qse.presets.ddd.report import QSEReport


def analyze_repo(path: str, config: QSEConfig = None) -> QSEReport:
    """Run the full QSE pipeline on a repository."""
    if config is None:
        config = QSEConfig()

    analysis = scan_repo(path, layer_map=config.layer_map or None)

    if config.enable_trace:
        trace = trace_repo(path)
    else:
        trace = TraceResult()

    graph = build_hybrid_graph(analysis, trace)
    metrics = compute_all_metrics(
        analysis, graph,
        fat_threshold=config.fat_threshold,
        fat_steepness=config.fat_steepness,
    )
    qse = compute_qse_total(metrics, config.weights)
    defects = detect_all(analysis, graph, path, config)
    stats = graph_stats(graph)
    test_quality = compute_test_quality(path)

    return QSEReport(
        metrics=metrics,
        qse_total=qse,
        defects=defects,
        graph_stats=stats,
        weights=config.weights,
        enable_trace=config.enable_trace,
        test_quality=test_quality,
    )
