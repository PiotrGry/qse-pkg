# AGQ Formula

## Components

AGQ (Architecture Graph Quality) is a composite metric of five normalized [0,1] components computed from the dependency graph:

| Component | Symbol | What it measures |
|-----------|--------|-----------------|
| **Modularity** | M | Louvain community detection quality (Newman's Q) |
| **Acyclicity** | A | 1 − (fraction of edges in cycles). DAG-like = higher |
| **Stability** | S | Mean abstractness of modules (interfaces + abstract classes / total) |
| **Cohesion** | C | 1 − mean(LCOM4). How well classes group related methods |
| **Coupling Density** | CD | 1 − (actual edges / possible edges). Sparsity of dependency graph |

## Versions

### v3c (Java, current)

Equal weights:

```
AGQ_v3c = 0.20·M + 0.20·A + 0.20·S + 0.20·C + 0.20·CD
```

- Used for Java GT validation
- Mann-Whitney p=0.000221 (n=59)
- AUC-ROC = 0.767

### v3c (Python)

Python-specific weights with flat_score:

```
AGQ_v3c = 0.15·M + 0.05·A + 0.20·S + 0.10·C + 0.15·CD + 0.35·flat_score
```

- Python GT: n=30 (13 POS, 17 NEG)

### Historical versions

- **v1**: 0.35M + 0.25A + 0.20S + 0.20C (no CD)
- **v2**: 0.30M + 0.20A + 0.15S + 0.15C + 0.20CD

## Constraints

From the Java-S experiment protocol:
- No non-linear models
- No brute-force weight optimization
- No new metrics without explicit justification
- Changes must survive falsification testing
