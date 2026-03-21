#!/usr/bin/env python3
"""Compare QSE AGQ results with Dai et al. (2026) published results.

Paper: "An integrated graph neural network model for joint software defect
prediction and code quality assessment", Scientific Reports 16:1677.

Usage:
    python3 scripts/dai_et_al_comparison.py
"""
import json
import math
from datetime import datetime
from pathlib import Path


# === Dai et al. Table 5 + Table 8 data ===
DAI_PROJECTS = {
    "ant": {
        "full_name": "Apache Ant",
        "language": "Java",
        "file_count": 1248,
        "defect_count": 345,
        "lines_of_code": 158426,
        "defect_density": 345 / 1248,  # defects per file
        "defect_density_kloc": 345 / 158.426,  # defects per KLOC
        "dai_complexity": "Low",
        "dai_baseline_f1": 0.755,
        "dai_model_f1": 0.811,
        "dai_improvement": "+7.4%",
        # Table 10: quality dimensions (proposed method accuracy)
        "dai_maintainability": 0.822,
        "dai_readability": 0.826,
        "dai_complexity_acc": 0.858,
        "dai_testability": 0.799,
        "dai_architectural_integrity": 0.800,
    },
    "apache-camel": {
        "full_name": "Apache Camel",
        "language": "Java",
        "file_count": 3874,
        "defect_count": 789,
        "lines_of_code": 452891,
        "defect_density": 789 / 3874,
        "defect_density_kloc": 789 / 452.891,
        "dai_complexity": "High",
        "dai_baseline_f1": 0.729,
        "dai_model_f1": 0.811,
        "dai_improvement": "+11.2%",
        "dai_maintainability": 0.804,
        "dai_readability": 0.826,
        "dai_complexity_acc": 0.863,
        "dai_testability": 0.780,
        "dai_architectural_integrity": 0.801,
    },
    "apache-hadoop": {
        "full_name": "Apache Hadoop",
        "language": "Java",
        "file_count": 2893,
        "defect_count": 678,
        "lines_of_code": 567234,
        "defect_density": 678 / 2893,
        "defect_density_kloc": 678 / 567.234,
        "dai_complexity": "Medium",
        "dai_baseline_f1": 0.746,
        "dai_model_f1": 0.809,
        "dai_improvement": "+8.4%",
        "dai_maintainability": 0.834,
        "dai_readability": 0.785,
        "dai_complexity_acc": 0.836,
        "dai_testability": 0.787,
        "dai_architectural_integrity": 0.815,
    },
    # Eclipse JDT excluded — scanner crash on 9267 files
}

# QSE results (from scan)
QSE_RESULTS = {
    "ant": {
        "agq_score": 0.5487,
        "modularity": 0.4972,
        "acyclicity": 0.9685,
        "stability": 0.468,
        "cohesion": 0.2611,
    },
    "apache-camel": {
        "agq_score": 0.5700,
        "modularity": 0.7872,
        "acyclicity": 0.9984,
        "stability": 0.1504,
        "cohesion": 0.3441,
    },
    "apache-hadoop": {
        "agq_score": 0.6262,
        "modularity": 0.6646,
        "acyclicity": 0.9902,
        "stability": 0.5901,
        "cohesion": 0.2597,
    },
}


def spearman_rank(xs, ys):
    """Spearman rank correlation for small n."""
    n = len(xs)
    if n < 3:
        return None
    rx = [sorted(xs).index(x) + 1 for x in xs]
    ry = [sorted(ys).index(y) + 1 for y in ys]
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - 6 * d2 / (n * (n * n - 1))


def main():
    projects = list(DAI_PROJECTS.keys())

    print("=" * 70)
    print("QSE AGQ vs Dai et al. (2026) — comparison on same Java repos")
    print("=" * 70)

    # Table
    print(f"\n{'Project':<16} {'AGQ':>6} {'Mod':>5} {'Acy':>5} {'Stab':>5} {'Coh':>5} "
          f"{'DefDens':>7} {'DaiF1':>6} {'DaiArch':>7}")
    print("-" * 75)

    agqs, defect_densities, dai_archs = [], [], []

    for name in projects:
        dai = DAI_PROJECTS[name]
        qse = QSE_RESULTS[name]

        agqs.append(qse["agq_score"])
        defect_densities.append(dai["defect_density"])
        dai_archs.append(dai["dai_architectural_integrity"])

        print(f"{dai['full_name']:<16} {qse['agq_score']:>6.3f} "
              f"{qse['modularity']:>5.2f} {qse['acyclicity']:>5.2f} "
              f"{qse['stability']:>5.2f} {qse['cohesion']:>5.2f} "
              f"{dai['defect_density']:>7.3f} {dai['dai_model_f1']:>6.3f} "
              f"{dai['dai_architectural_integrity']:>7.3f}")

    # Rankings
    print(f"\n=== RANKING COMPARISON (n=3) ===")
    agq_rank = [projects[i] for i in sorted(range(3), key=lambda i: -agqs[i])]
    defect_rank = [projects[i] for i in sorted(range(3), key=lambda i: defect_densities[i])]
    arch_rank = [projects[i] for i in sorted(range(3), key=lambda i: -dai_archs[i])]

    print(f"  By AGQ (best→worst):           {' > '.join(agq_rank)}")
    print(f"  By defect density (best→worst): {' > '.join(defect_rank)}")
    print(f"  By Dai arch integrity (best):   {' > '.join(arch_rank)}")

    # Concordance
    rho_agq_defect = spearman_rank(agqs, [-d for d in defect_densities])
    rho_agq_arch = spearman_rank(agqs, dai_archs)

    print(f"\n=== RANK CORRELATIONS ===")
    print(f"  AGQ vs defect density (inverted): rho={rho_agq_defect}")
    print(f"  AGQ vs Dai architectural integrity: rho={rho_agq_arch}")

    # Qualitative analysis
    print(f"\n=== QUALITATIVE ANALYSIS ===")
    for name in projects:
        dai = DAI_PROJECTS[name]
        qse = QSE_RESULTS[name]
        issues = []
        if qse["stability"] < 0.3:
            issues.append(f"very low stability ({qse['stability']:.2f}) — flat architecture")
        if qse["cohesion"] < 0.3:
            issues.append(f"low cohesion ({qse['cohesion']:.2f}) — god classes")
        if qse["acyclicity"] < 0.95:
            issues.append(f"cycles detected (acy={qse['acyclicity']:.2f})")
        print(f"  {dai['full_name']}: AGQ={qse['agq_score']:.3f}")
        if issues:
            for iss in issues:
                print(f"    - {iss}")
        else:
            print(f"    - no major issues detected")

    # Save
    output = {
        "generated_at": datetime.now().isoformat(),
        "paper": {
            "title": "An integrated graph neural network model for joint software defect prediction and code quality assessment",
            "authors": "Dai, Zhu, Wu, He",
            "journal": "Scientific Reports",
            "year": 2026,
            "doi": "10.1038/s41598-025-31209-5",
        },
        "methodology": {
            "qse_scanner": "Rust qse-core (tree-sitter-java)",
            "qse_metrics": "AGQ with default equal weights (0.25 each)",
            "dai_data": "Extracted from Table 5, Table 8, Table 10 of paper",
            "note": "Eclipse JDT excluded — scanner crash on 9267 files",
        },
        "comparison": [],
        "rank_correlations": {
            "agq_vs_defect_density_inverted": rho_agq_defect,
            "agq_vs_dai_architectural_integrity": rho_agq_arch,
        },
    }

    for name in projects:
        dai = DAI_PROJECTS[name]
        qse = QSE_RESULTS[name]
        output["comparison"].append({
            "project": dai["full_name"],
            "qse": qse,
            "dai": {k: v for k, v in dai.items() if k != "full_name"},
        })

    out_path = Path("artifacts/benchmark/dai_et_al_comparison.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
