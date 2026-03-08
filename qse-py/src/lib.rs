use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use qse_core::{scan_repo, compute_agq};

/// Scan a repository and compute AGQ metrics.
/// Returns a dict with keys: modularity, acyclicity, stability, cohesion,
/// agq_score, nodes, edges, language.
#[pyfunction]
fn scan_and_compute_agq(py: Python<'_>, path: &str) -> PyResult<PyObject> {
    let result = scan_repo(path);
    let metrics = compute_agq(&result);

    let dict = PyDict::new_bound(py);
    dict.set_item("modularity",  metrics.modularity)?;
    dict.set_item("acyclicity",  metrics.acyclicity)?;
    dict.set_item("stability",   metrics.stability)?;
    dict.set_item("cohesion",    metrics.cohesion)?;
    dict.set_item("agq_score",   metrics.agq_score)?;
    dict.set_item("nodes",       metrics.nodes)?;
    dict.set_item("edges",       metrics.edges)?;
    dict.set_item("language",    format!("{:?}", result.language))?;
    Ok(dict.into())
}

/// Scan repository and return class list for inspection.
#[pyfunction]
fn scan_classes(py: Python<'_>, path: &str) -> PyResult<PyObject> {
    let result = scan_repo(path);
    let list = PyList::empty_bound(py);
    for (name, cls) in &result.classes {
        let d = PyDict::new_bound(py);
        d.set_item("name",        name)?;
        d.set_item("file",        &cls.file_path)?;
        d.set_item("is_abstract", cls.is_abstract)?;
        d.set_item("n_methods",   cls.method_attrs.len())?;
        list.append(d)?;
    }
    Ok(list.into())
}

/// Detect language of a repository.
#[pyfunction]
fn detect_language(path: &str) -> String {
    let result = scan_repo(path);
    format!("{:?}", result.language)
}

/// Scan repository and return graph as JSON string.
/// Format: {"nodes": [{"id": "mod.path", "file": "/src/..."}, ...],
///           "edges": [["src", "tgt"], ...],
///           "language": "Java"}
/// Suitable for feeding into qse.discover or networkx reconstruction.
#[pyfunction]
fn scan_to_graph_json(path: &str) -> PyResult<String> {
    let result = scan_repo(path);
    let g = &result.internal_graph;

    // Build nodes list with file metadata
    let mut nodes = serde_json::json!([]);
    for ni in g.node_indices() {
        let name = &g[ni];
        let file = result.node_index.get(name)
            .map(|_| name.clone())
            .unwrap_or_default();
        let is_internal = result.internal_nodes.contains(name);
        nodes.as_array_mut().unwrap().push(serde_json::json!({
            "id": name,
            "internal": is_internal,
        }));
    }

    // Build edges list
    let mut edges = serde_json::json!([]);
    for e in g.edge_indices() {
        let (a, b) = g.edge_endpoints(e).unwrap();
        edges.as_array_mut().unwrap().push(serde_json::json!([g[a], g[b]]));
    }

    let output = serde_json::json!({
        "language": format!("{:?}", result.language),
        "nodes": nodes,
        "edges": edges,
        "n_internal": result.internal_nodes.len(),
    });

    Ok(serde_json::to_string(&output).unwrap())
}

#[pymodule]
fn _qse_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(scan_and_compute_agq, m)?)?;
    m.add_function(wrap_pyfunction!(scan_classes, m)?)?;
    m.add_function(wrap_pyfunction!(detect_language, m)?)?;
    m.add_function(wrap_pyfunction!(scan_to_graph_json, m)?)?;
    Ok(())
}
