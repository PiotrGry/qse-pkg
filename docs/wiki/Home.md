# QSE / AGQ Project Wiki

**Quantitative Software Engineering — Architecture Quality (AGQ) Metric**

## Overview

QSE is a research project developing a composite metric (AGQ) for scoring software architecture quality from static source code analysis. The metric combines five graph-based components into a single 0–1 score that correlates with expert quality judgments.

## Quick Links

- [AGQ Formula](AGQ-Formula) — metric components, weights, versions
- [Ground Truth](Ground-Truth) — GT datasets (Java, Python), panel methodology
- [Scanners](Scanners) — Python scanner, Java scanner, architecture
- [Experiments](Experiments) — Java-S experiment, Python deep-dive, Jolak cross-validation
- [Roadmap](Roadmap) — current status, completed/pending tasks

## Key Results (April 2026)

| Metric | Java (n=59) | Python (n=30) |
|--------|-------------|---------------|
| POS mean AGQ | 0.571 | — |
| NEG mean AGQ | 0.486 | — |
| Mann-Whitney p | 0.000221 | — |
| Spearman ρ | 0.380 | — |
| AUC-ROC | 0.767 | — |

## Repository Structure

```
qse-pkg/
├── qse/                    # Core library
│   ├── scanner.py          # Python scanner (tree-sitter)
│   ├── java_scanner.py     # Java scanner (tree-sitter-java)
│   └── graph_metrics.py    # AGQ computation
├── artifacts/              # Ground truth, scan results
│   ├── gt_java_final_fixed.json    # Original Java GT (n=29)
│   ├── gt_java_expanded.json       # Expanded Java GT (n=59)
│   ├── java_gt_candidates.json     # 30 expansion candidates
│   ├── jolak_scan_results.json     # 8 Jolak repos
│   └── python_deepdive_results.json # 30 Python repos
└── _qse_core/              # Rust scanner (optional)
```

## Branch

All development on `perplexity` branch.
