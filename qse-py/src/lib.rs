// PyO3 0.22's #[pyfunction] expansion triggers this lint on Rust 1.98.
#![allow(clippy::useless_conversion)]

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use qse_core::{compute_agq, scan_repo, ScanResult};

fn run_scan(py: Python<'_>, path: &str) -> PyResult<ScanResult> {
    py.allow_threads(|| scan_repo(path))
        .map_err(|error| PyValueError::new_err(error.to_string()))
}

fn diagnostics_dict<'py>(py: Python<'py>, result: &ScanResult) -> PyResult<Bound<'py, PyDict>> {
    let diagnostics = PyDict::new_bound(py);
    diagnostics.set_item("discovered_files", result.diagnostics.discovered_files)?;
    diagnostics.set_item("parsed_files", result.diagnostics.parsed_files)?;
    diagnostics.set_item("skipped_files", result.diagnostics.skipped_files)?;
    diagnostics.set_item("external_imports", result.diagnostics.external_imports)?;
    diagnostics.set_item("warnings", &result.diagnostics.warnings)?;
    Ok(diagnostics)
}

/// Scan a repository and compute AGQ metrics.
/// Cohesion is None when it is not measurable for the selected language.
#[pyfunction]
fn scan_and_compute_agq(py: Python<'_>, path: &str) -> PyResult<PyObject> {
    let result = run_scan(py, path)?;
    let metrics = compute_agq(&result);

    let dict = PyDict::new_bound(py);
    dict.set_item("modularity", metrics.modularity)?;
    dict.set_item("acyclicity", metrics.acyclicity)?;
    dict.set_item("stability", metrics.stability)?;
    dict.set_item("cohesion", metrics.cohesion)?;
    dict.set_item("agq_score", metrics.agq_score)?;
    dict.set_item("nodes", metrics.nodes)?;
    dict.set_item("edges", metrics.edges)?;
    dict.set_item("language", result.language.as_str())?;
    dict.set_item("diagnostics", diagnostics_dict(py, &result)?)?;
    Ok(dict.into())
}

/// Scan a repository and return a deterministic class list for inspection.
#[pyfunction]
fn scan_classes(py: Python<'_>, path: &str) -> PyResult<PyObject> {
    let result = run_scan(py, path)?;
    let list = PyList::empty_bound(py);
    let mut classes: Vec<_> = result.classes.values().collect();
    classes.sort_by(|left, right| left.qualified_name.cmp(&right.qualified_name));
    for class in classes {
        let item = PyDict::new_bound(py);
        item.set_item("name", &class.name)?;
        item.set_item("qualified_name", &class.qualified_name)?;
        item.set_item("file", &class.file_path)?;
        item.set_item("is_abstract", class.is_abstract)?;
        item.set_item("n_methods", class.method_attrs.len())?;
        list.append(item)?;
    }
    Ok(list.into())
}

/// Detect the repository language using the same validation as a full scan.
#[pyfunction]
fn detect_language(py: Python<'_>, path: &str) -> PyResult<String> {
    Ok(run_scan(py, path)?.language.as_str().to_string())
}

/// Return the true internal graph as JSON.
#[pyfunction]
fn scan_to_graph_json(py: Python<'_>, path: &str) -> PyResult<String> {
    let result = run_scan(py, path)?;
    let graph = &result.internal_graph;

    let nodes: Vec<_> = graph
        .node_indices()
        .map(|index| {
            let name = &graph[index];
            let files: Vec<String> = result
                .node_files
                .get(name)
                .into_iter()
                .flatten()
                .map(|path| path.to_string_lossy().into_owned())
                .collect();
            serde_json::json!({
                "id": name,
                "internal": true,
                "files": files,
            })
        })
        .collect();
    let edges: Vec<_> = graph
        .edge_indices()
        .filter_map(|edge| graph.edge_endpoints(edge))
        .map(|(source, target)| serde_json::json!([graph[source], graph[target]]))
        .collect();
    let output = serde_json::json!({
        "language": result.language.as_str(),
        "nodes": nodes,
        "edges": edges,
        "n_internal": result.internal_nodes.len(),
        "diagnostics": result.diagnostics,
    });
    serde_json::to_string(&output)
        .map_err(|error| PyRuntimeError::new_err(format!("failed to serialize graph: {error}")))
}

#[pymodule]
fn _qse_core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(scan_and_compute_agq, module)?)?;
    module.add_function(wrap_pyfunction!(scan_classes, module)?)?;
    module.add_function(wrap_pyfunction!(detect_language, module)?)?;
    module.add_function(wrap_pyfunction!(scan_to_graph_json, module)?)?;
    Ok(())
}
