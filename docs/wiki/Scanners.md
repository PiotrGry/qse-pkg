# Scanners

## Architecture

Both scanners follow the same pipeline:

1. **Parse**: Walk source files, extract classes/modules using tree-sitter AST
2. **Build graph**: Nodes = file-level modules (package.ClassName), edges = imports/dependencies
3. **Compute metrics**: Pass graph to `graph_metrics.compute_agq()`

## Python Scanner (`qse/scanner.py`)

- Uses tree-sitter for Python AST parsing
- Node granularity: module-level (one node per .py file)
- Edges: import statements (import, from...import)
- Handles: relative imports, __init__.py packages

## Java Scanner (`qse/java_scanner.py`)

- Uses tree-sitter-java for Java AST parsing
- **Pure Python** (no Rust dependency)
- Node granularity: **file-level** (package.ClassName per .java file)
- Edges: import statements
- Extracts: interfaces, abstract classes, method counts (for LCOM4)
- Returns `JavaScanResult` dataclass

### Usage

```python
from qse.java_scanner import scan_java_repo, scan_result_to_agq_inputs
from qse.graph_metrics import compute_agq

scan = scan_java_repo("/path/to/repo")
graph, abstract_modules, lcom4_values = scan_result_to_agq_inputs(scan)
metrics = compute_agq(graph, abstract_modules, lcom4_values, weights=(0.20, 0.20, 0.20, 0.20))
```

### Critical Bug History

- **v1 (broken)**: Used package-level nodes (20 nodes for yavi, A=0.400)
- **v2 (fixed)**: File-level nodes matching Rust scanner (687 nodes for yavi, A=0.994)
- Fix: Rewrite to create nodes as `package.ClassName` per .java file

## Rust Scanner (`_qse_core`)

- Original Rust implementation
- Uses `module_path()` for file-level nodes
- Not available in current Python-only environment
- Java scanner was validated against Rust scanner output
