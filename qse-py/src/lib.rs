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

#[pymodule]
fn _qse_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(scan_and_compute_agq, m)?)?;
    m.add_function(wrap_pyfunction!(scan_classes, m)?)?;
    m.add_function(wrap_pyfunction!(detect_language, m)?)?;
    Ok(())
}
