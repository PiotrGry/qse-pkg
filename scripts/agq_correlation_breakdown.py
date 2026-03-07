#!/usr/bin/env python3
"""Correlation analysis for AGQ OSS benchmark report.

Computes:
1) Sonar-vs-Sonar correlations (including code_smells vs bugs).
2) AGQ breakdown (modularity/acyclicity/stability/cohesion) vs Sonar + defect proxy.
3) Top strongest pairwise correlations for quick interpretation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def _float(x: object) -> Optional[float]:
    if isinstance(x, (int, float)):
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    return None


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    den = denx * deny
    if den == 0.0:
        return None
    return num / den


def _p_value(r: Optional[float], n: int) -> Optional[float]:
    """Two-tailed p-value for Pearson/Spearman r via t-distribution approximation."""
    if r is None or n < 3:
        return None
    r2 = r * r
    if r2 >= 1.0:
        return 0.0
    df = n - 2
    t_stat = abs(r) * math.sqrt(df / (1.0 - r2))
    # Approximate two-tailed p using regularized incomplete beta function
    # P(T > |t|) for Student's t with df degrees of freedom
    x = df / (df + t_stat * t_stat)
    p = _betai(0.5 * df, 0.5, x)
    return p


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b) via continued fraction."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    # Use symmetry relation when x > (a+1)/(a+b+2)
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _betai(b, a, 1.0 - x)
    # Log of the beta-function coefficient
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x)) / a
    # Lentz's continued fraction
    f = 1.0
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    f = d
    for m in range(1, 200):
        # Even step
        num = m * (b - m) * x / ((a + 2.0 * m - 1.0) * (a + 2.0 * m))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        f *= d * c
        # Odd step
        num = -(a + m) * (a + b + m) * x / ((a + 2.0 * m) * (a + 2.0 * m + 1.0))
        d = 1.0 + num * d
        if abs(d) < 1e-30:
            d = 1e-30
        d = 1.0 / d
        c = 1.0 + num / c
        if abs(c) < 1e-30:
            c = 1e-30
        delta = d * c
        f *= delta
        if abs(delta - 1.0) < 1e-10:
            break
    return front * f


def _ranks(values: Sequence[float]) -> List[float]:
    indexed = sorted((v, i) for i, v in enumerate(values))
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][0] == indexed[i][0]:
            j += 1
        rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[indexed[k][1]] = rank
        i = j + 1
    return ranks


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    return _pearson(_ranks(xs), _ranks(ys))


def _pair_values(
    rows: Sequence[Dict[str, object]],
    field_x: str,
    field_y: str,
) -> Tuple[List[float], List[float]]:
    xs: List[float] = []
    ys: List[float] = []
    for row in rows:
        vx = _float(row.get(field_x))
        vy = _float(row.get(field_y))
        if vx is None or vy is None:
            continue
        xs.append(vx)
        ys.append(vy)
    return xs, ys


def _corr_entry(
    rows: Sequence[Dict[str, object]],
    field_x: str,
    field_y: str,
) -> Dict[str, object]:
    xs, ys = _pair_values(rows, field_x, field_y)
    r_p = _pearson(xs, ys)
    r_s = _spearman(xs, ys)
    n = len(xs)
    return {
        "x": field_x,
        "y": field_y,
        "n": n,
        "pearson": r_p,
        "pearson_p": _p_value(r_p, n),
        "spearman": r_s,
        "spearman_p": _p_value(r_s, n),
    }


def _correlation_matrix(
    rows: Sequence[Dict[str, object]],
    fields_x: Sequence[str],
    fields_y: Sequence[str],
) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for x in fields_x:
        for y in fields_y:
            out.append(_corr_entry(rows, x, y))
    return out


def _fmt(value: Optional[float], digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _strength(abs_r: Optional[float]) -> str:
    if abs_r is None:
        return "n/a"
    if abs_r < 0.2:
        return "very_weak"
    if abs_r < 0.4:
        return "weak"
    if abs_r < 0.6:
        return "moderate"
    if abs_r < 0.8:
        return "strong"
    return "very_strong"


def _to_markdown(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# AGQ Correlation Breakdown")
    lines.append("")
    lines.append(f"- generated_at: `{report['generated_at']}`")
    lines.append(f"- source_report: `{report['source_report']}`")
    lines.append(f"- repos_used: `{report['summary']['repos_used']}`")
    lines.append("")

    lines.append("## Key Findings")
    lines.append("")
    for finding in report["summary"]["key_findings"]:
        lines.append(f"- {finding}")
    lines.append("")

    lines.append("## Sonar vs Sonar")
    lines.append("")
    lines.append("| X | Y | n | Pearson | p | Spearman | p |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for row in report["sonar_vs_sonar"]:
        lines.append(
            f"| {row['x']} | {row['y']} | {row['n']} | "
            f"{_fmt(row['pearson'])} | {_fmt(row.get('pearson_p'))} | "
            f"{_fmt(row['spearman'])} | {_fmt(row.get('spearman_p'))} |"
        )
    lines.append("")

    lines.append("## AGQ Breakdown vs Sonar/Defect")
    lines.append("")
    lines.append("| AGQ Metric | Target | n | Pearson | p | Spearman | p |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for row in report["agq_breakdown"]:
        lines.append(
            f"| {row['x']} | {row['y']} | {row['n']} | "
            f"{_fmt(row['pearson'])} | {_fmt(row.get('pearson_p'))} | "
            f"{_fmt(row['spearman'])} | {_fmt(row.get('spearman_p'))} |"
        )
    lines.append("")

    lines.append("## Strongest Correlations")
    lines.append("")
    lines.append("| X | Y | Method | r | |r| strength |")
    lines.append("|---|---|---|---:|---|")
    for row in report["top_correlations"]:
        lines.append(
            f"| {row['x']} | {row['y']} | {row['method']} | {_fmt(row['r'])} | {row['strength']} |"
        )
    lines.append("")

    # Mediation analysis section
    mediation = report.get("mediation_analysis", {})
    chains = mediation.get("chains", [])
    if chains:
        lines.append("## Mediation Analysis (AGQ → Mediator → Outcome)")
        lines.append("")
        lines.append("| Chain | r(a) | p(a) | r(b) | p(b) | r(c) direct | Indirect | Sobel z | Sobel p | Interpretation |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
        for ch in chains:
            lines.append(
                f"| {ch['chain']} | {_fmt(ch.get('r_a'))} | {_fmt(ch.get('r_a_p'))} | "
                f"{_fmt(ch.get('r_b'))} | {_fmt(ch.get('r_b_p'))} | "
                f"{_fmt(ch.get('r_c_direct'))} | {_fmt(ch.get('indirect_effect'))} | "
                f"{_fmt(ch.get('sobel_z'))} | {_fmt(ch.get('sobel_p'))} | "
                f"{ch.get('interpretation', 'n/a')} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def _flatten_row(raw_row: Dict[str, object]) -> Dict[str, object]:
    out: Dict[str, object] = {"repo": raw_row["name"]}

    agq = raw_row.get("agq", {})
    run1 = agq.get("run1", {}) if isinstance(agq, dict) else {}
    out["agq_score"] = agq.get("score_mean")
    out["modularity"] = run1.get("modularity")
    out["acyclicity"] = run1.get("acyclicity")
    out["stability"] = run1.get("stability")
    out["cohesion"] = run1.get("cohesion")
    out["agq_runtime_s"] = agq.get("runtime_s_mean")
    out["graph_nodes"] = run1.get("nodes")
    out["graph_edges"] = run1.get("edges")

    sonar = raw_row.get("sonar", {})
    if isinstance(sonar, dict):
        out["bugs"] = sonar.get("bugs")
        out["vulnerabilities"] = sonar.get("vulnerabilities")
        out["code_smells"] = sonar.get("code_smells")
        out["ncloc"] = sonar.get("ncloc")
        out["complexity"] = sonar.get("complexity")
        out["cognitive_complexity"] = sonar.get("cognitive_complexity")
        out["duplicated_lines_density"] = sonar.get("duplicated_lines_density")
        out["maintainability_quality_score"] = sonar.get("maintainability_quality_score")
        out["code_smell_quality_score"] = sonar.get("code_smell_quality_score")
        out["sonar_runtime_s"] = sonar.get("runtime_s")

    defect = raw_row.get("defect_proxy", {})
    if isinstance(defect, dict):
        out["bugfix_ratio"] = defect.get("bugfix_ratio")
        out["bugfix_commits"] = defect.get("bugfix_commits")
        out["total_commits"] = defect.get("total_commits")

    # Blast radius ground truth (from agq_ground_truth_collector.py)
    blast = raw_row.get("blast_radius", {})
    if isinstance(blast, dict) and not blast.get("insufficient_data"):
        out["mean_files_per_fix"] = blast.get("mean_files_per_fix")
        out["median_files_per_fix"] = blast.get("median_files_per_fix")
        out["pct_cross_package_fixes"] = blast.get("pct_cross_package_fixes")
        out["pct_wide_fixes"] = blast.get("pct_wide_fixes")
        out["mean_packages_per_fix"] = blast.get("mean_packages_per_fix")

    # GitHub bug issues ground truth
    gh = raw_row.get("github", {})
    if isinstance(gh, dict):
        out["bug_issues_per_kloc"] = gh.get("bug_issues_per_kloc")
        out["median_close_time_days"] = gh.get("median_close_time_days")

    # Composite architectural quality proxy
    out["arch_quality_proxy"] = raw_row.get("arch_quality_proxy")

    ncloc = _float(out.get("ncloc"))
    bugs = _float(out.get("bugs"))
    vulns = _float(out.get("vulnerabilities"))
    smells = _float(out.get("code_smells"))
    comp = _float(out.get("complexity"))
    ccomp = _float(out.get("cognitive_complexity"))
    if ncloc and ncloc > 0:
        scale = ncloc / 1000.0
        out["bugs_per_kloc"] = bugs / scale if bugs is not None else None
        out["vulns_per_kloc"] = vulns / scale if vulns is not None else None
        out["smells_per_kloc"] = smells / scale if smells is not None else None
        out["complexity_per_kloc"] = comp / scale if comp is not None else None
        out["cognitive_complexity_per_kloc"] = ccomp / scale if ccomp is not None else None
    else:
        out["bugs_per_kloc"] = None
        out["vulns_per_kloc"] = None
        out["smells_per_kloc"] = None
        out["complexity_per_kloc"] = None
        out["cognitive_complexity_per_kloc"] = None

    return out


def _mediation_analysis(rows: Sequence[Dict[str, object]]) -> Dict[str, object]:
    """
    Mediation analysis: AGQ → Mediator → Outcome.

    Tests whether complexity mediates the AGQ→bugs relationship.
    Chain: AGQ --a--> complexity --b--> bugs
    Direct: AGQ --c'--> bugs
    Indirect effect = a * b
    Sobel z = (a*b) / sqrt(b²·SE_a² + a²·SE_b²)
    """
    mediators = ["complexity_per_kloc", "cognitive_complexity_per_kloc", "smells_per_kloc"]
    outcomes = ["bugs_per_kloc", "bugfix_ratio", "mean_files_per_fix", "pct_cross_package_fixes"]
    predictor = "agq_score"

    results = []
    for mediator in mediators:
        for outcome in outcomes:
            xs_a, ys_a = _pair_values(rows, predictor, mediator)
            xs_b, ys_b = _pair_values(rows, mediator, outcome)
            xs_c, ys_c = _pair_values(rows, predictor, outcome)

            r_a = _pearson(xs_a, ys_a)  # AGQ → mediator
            r_b = _pearson(xs_b, ys_b)  # mediator → outcome
            r_c = _pearson(xs_c, ys_c)  # AGQ → outcome (direct)

            n_a = len(xs_a)
            n_b = len(xs_b)

            entry: Dict[str, object] = {
                "chain": f"{predictor} → {mediator} → {outcome}",
                "r_a": r_a,
                "r_a_p": _p_value(r_a, n_a),
                "n_a": n_a,
                "r_b": r_b,
                "r_b_p": _p_value(r_b, n_b),
                "n_b": n_b,
                "r_c_direct": r_c,
                "r_c_p": _p_value(r_c, len(xs_c)),
                "n_c": len(xs_c),
                "indirect_effect": None,
                "sobel_z": None,
                "sobel_p": None,
                "interpretation": None,
            }

            if r_a is not None and r_b is not None:
                indirect = r_a * r_b
                entry["indirect_effect"] = indirect

                # Sobel test: z = a*b / sqrt(b²·SE_a² + a²·SE_b²)
                # SE for correlation ≈ sqrt((1-r²)/(n-2))
                if n_a > 2 and n_b > 2:
                    se_a = math.sqrt((1 - r_a * r_a) / max(n_a - 2, 1))
                    se_b = math.sqrt((1 - r_b * r_b) / max(n_b - 2, 1))
                    denom = math.sqrt(r_b * r_b * se_a * se_a + r_a * r_a * se_b * se_b)
                    if denom > 0:
                        z = abs(indirect) / denom
                        entry["sobel_z"] = z
                        # Approximate two-tailed p from z: p ≈ 2 * Φ(-|z|)
                        # Using Abramowitz & Stegun approximation for normal CDF
                        t = 1.0 / (1.0 + 0.2316419 * abs(z))
                        phi = 0.3989422802 * math.exp(-z * z / 2.0) * t * (
                            0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429)))
                        )
                        entry["sobel_p"] = 2.0 * phi

                # Interpretation
                both_sig = (entry.get("r_a_p") or 1) < 0.05 and (entry.get("r_b_p") or 1) < 0.05
                direct_weak = r_c is None or abs(r_c) < 0.3
                if both_sig and abs(indirect) > 0.1:
                    if direct_weak:
                        entry["interpretation"] = "full_mediation"
                    else:
                        entry["interpretation"] = "partial_mediation"
                elif (entry.get("r_a_p") or 1) < 0.05 and abs(r_a) > 0.3:
                    entry["interpretation"] = "path_a_significant"
                else:
                    entry["interpretation"] = "no_mediation"

            results.append(entry)

    return {"chains": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Correlation breakdown for AGQ benchmark report")
    parser.add_argument(
        "--input-json",
        default="artifacts/benchmark/agq_thesis_oss15.json",
        help="Input benchmark JSON generated by agq_oss_thesis_benchmark.py",
    )
    parser.add_argument(
        "--output-json",
        default="artifacts/benchmark/agq_correlation_breakdown.json",
    )
    parser.add_argument(
        "--output-md",
        default="artifacts/benchmark/agq_correlation_breakdown.md",
    )
    args = parser.parse_args()

    inp = Path(args.input_json)
    data = json.loads(inp.read_text())
    raw_rows = [r for r in data["results"] if "error" not in r]
    rows = [_flatten_row(r) for r in raw_rows]

    sonar_pairs = [
        ("code_smells", "bugs"),
        ("code_smells", "vulnerabilities"),
        ("bugs", "vulnerabilities"),
        ("code_smells", "complexity"),
        ("code_smells", "cognitive_complexity"),
        ("smells_per_kloc", "bugs_per_kloc"),
        ("smells_per_kloc", "vulns_per_kloc"),
        ("bugs_per_kloc", "vulns_per_kloc"),
        ("complexity_per_kloc", "smells_per_kloc"),
        ("duplicated_lines_density", "smells_per_kloc"),
    ]
    sonar_vs_sonar = [_corr_entry(rows, x, y) for x, y in sonar_pairs]

    agq_metrics = ["agq_score", "modularity", "acyclicity", "stability", "cohesion"]
    targets = [
        "bugfix_ratio",
        "mean_files_per_fix",
        "median_files_per_fix",
        "pct_cross_package_fixes",
        "pct_wide_fixes",
        "mean_packages_per_fix",
        "bug_issues_per_kloc",
        "median_close_time_days",
        "arch_quality_proxy",
        "bugs_per_kloc",
        "vulns_per_kloc",
        "smells_per_kloc",
        "complexity_per_kloc",
        "cognitive_complexity_per_kloc",
        "duplicated_lines_density",
        "sonar_runtime_s",
    ]
    agq_breakdown = _correlation_matrix(rows, agq_metrics, targets)

    all_corr_rows: List[Dict[str, object]] = []
    for src in (sonar_vs_sonar, agq_breakdown):
        for row in src:
            p = row.get("pearson")
            s = row.get("spearman")
            if p is not None:
                all_corr_rows.append(
                    {
                        "x": row["x"],
                        "y": row["y"],
                        "method": "pearson",
                        "r": p,
                        "abs_r": abs(p),
                    }
                )
            if s is not None:
                all_corr_rows.append(
                    {
                        "x": row["x"],
                        "y": row["y"],
                        "method": "spearman",
                        "r": s,
                        "abs_r": abs(s),
                    }
                )
    all_corr_rows.sort(key=lambda r: r["abs_r"], reverse=True)
    top = []
    for row in all_corr_rows[:12]:
        top.append(
            {
                "x": row["x"],
                "y": row["y"],
                "method": row["method"],
                "r": row["r"],
                "abs_r": row["abs_r"],
                "strength": _strength(row["abs_r"]),
            }
        )

    def pick(corr_list: List[Dict[str, object]], x: str, y: str) -> Optional[Dict[str, object]]:
        for row in corr_list:
            if row["x"] == x and row["y"] == y:
                return row
        return None

    key_findings: List[str] = []
    cs_bugs = pick(sonar_vs_sonar, "code_smells", "bugs")
    if cs_bugs:
        key_findings.append(
            f"code_smells vs bugs: pearson={_fmt(cs_bugs['pearson'])}, "
            f"spearman={_fmt(cs_bugs['spearman'])} (n={cs_bugs['n']})"
        )

    def best_target_for(metric: str) -> Optional[Dict[str, object]]:
        rows_metric = [r for r in agq_breakdown if r["x"] == metric and r["pearson"] is not None]
        if not rows_metric:
            return None
        rows_metric.sort(key=lambda r: abs(float(r["pearson"])), reverse=True)
        return rows_metric[0]

    for metric in agq_metrics:
        best = best_target_for(metric)
        if best:
            key_findings.append(
                f"{metric}: strongest pearson with {best['y']} = {_fmt(best['pearson'])} "
                f"({ _strength(abs(float(best['pearson']))) })"
            )

    report: Dict[str, object] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_report": str(inp),
        "summary": {
            "repos_used": len(rows),
            "key_findings": key_findings,
        },
        "sonar_vs_sonar": sonar_vs_sonar,
        "agq_breakdown": agq_breakdown,
        "top_correlations": top,
        "mediation_analysis": _mediation_analysis(rows),
    }

    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2))
    out_md.write_text(_to_markdown(report))

    print(f"Correlation report generated: {out_json} and {out_md}")


if __name__ == "__main__":
    main()
