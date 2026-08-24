use qse_core::{compute_agq, scan_repo, Language, ScanError};
use std::fs;
use std::path::Path;
use tempfile::TempDir;

fn write(root: &Path, relative: &str, contents: &str) {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().expect("fixture file has parent")).unwrap();
    fs::write(path, contents).unwrap();
}

fn has_edge(result: &qse_core::ScanResult, source: &str, target: &str) -> bool {
    result.internal_graph.edge_indices().any(|edge| {
        let (a, b) = result.internal_graph.edge_endpoints(edge).unwrap();
        result.internal_graph[a] == source && result.internal_graph[b] == target
    })
}

#[test]
fn invalid_path_returns_an_error() {
    let error = scan_repo("/path/that/does/not/exist").unwrap_err();
    assert!(matches!(error, ScanError::InvalidPath(_)));
}

#[test]
fn ambiguous_multilanguage_repo_is_rejected() {
    let fixture = TempDir::new().unwrap();
    write(fixture.path(), "app.py", "print('hello')\n");
    write(fixture.path(), "main.go", "package main\nfunc main() {}\n");
    let error = scan_repo(fixture.path().to_str().unwrap()).unwrap_err();
    assert!(matches!(error, ScanError::AmbiguousLanguage { .. }));
}

#[test]
fn python_tooling_file_does_not_override_a_java_codebase() {
    let fixture = TempDir::new().unwrap();
    write(fixture.path(), "setup.py", "print('build helper')\n");
    for name in ["One", "Two", "Three", "Four"] {
        write(
            fixture.path(),
            &format!("src/com/acme/{name}.java"),
            &format!("package com.acme; public class {name} {{}}\n"),
        );
    }
    let result = scan_repo(fixture.path().to_str().unwrap()).unwrap();
    assert_eq!(result.language, Language::Java);
    assert_eq!(result.internal_graph.node_count(), 4);
}

#[test]
fn python_relative_imports_and_init_files_are_internal() {
    let fixture = TempDir::new().unwrap();
    write(
        fixture.path(),
        "pyproject.toml",
        "[project]\nname = 'fixture'\nversion = '0.0.1'\n",
    );
    write(fixture.path(), "src/pkg/__init__.py", "from . import a\n");
    write(
        fixture.path(),
        "src/pkg/a.py",
        "from . import b\nimport requests\n",
    );
    write(fixture.path(), "src/pkg/b.py", "VALUE = 1\n");

    let result = scan_repo(fixture.path().to_str().unwrap()).unwrap();
    assert_eq!(result.language, Language::Python);
    assert_eq!(result.internal_graph.node_count(), 3);
    assert!(result.internal_nodes.contains("pkg"));
    assert!(result.internal_nodes.contains("pkg.a"));
    assert!(result.internal_nodes.contains("pkg.b"));
    assert!(has_edge(&result, "pkg", "pkg.a"));
    assert!(has_edge(&result, "pkg.a", "pkg.b"));
    assert!(!result
        .internal_graph
        .node_indices()
        .any(|node| result.internal_graph[node] == "requests"));
    assert!(result
        .graph
        .node_indices()
        .any(|node| result.graph[node] == "requests"));
}

#[test]
fn go_uses_package_nodes_and_renormalizes_missing_cohesion() {
    let fixture = TempDir::new().unwrap();
    write(
        fixture.path(),
        "go.mod",
        "module example.com/fixture\n\ngo 1.22\n",
    );
    write(
        fixture.path(),
        "main.go",
        "package fixture\nimport \"example.com/fixture/internal/service\"\nfunc Run() { service.Run() }\n",
    );
    write(
        fixture.path(),
        "internal/service/service.go",
        "package service\nfunc Run() {}\n",
    );

    let result = scan_repo(fixture.path().to_str().unwrap()).unwrap();
    assert_eq!(result.language, Language::Go);
    assert_eq!(result.internal_graph.node_count(), 2);
    assert!(has_edge(&result, ".", "internal/service"));
    let metrics = compute_agq(&result);
    assert_eq!(metrics.cohesion, None);
    assert!((0.0..=1.0).contains(&metrics.agq_score));
}

#[test]
fn java_resolves_same_package_types_and_unqualified_fields() {
    let fixture = TempDir::new().unwrap();
    write(fixture.path(), "pom.xml", "<project/>\n");
    write(
        fixture.path(),
        "src/main/java/com/acme/A.java",
        r#"package com.acme;
public class A {
    private int value;
    private B dependency;
    public int get() { return value; }
    public void increment() { value++; }
}
"#,
    );
    write(
        fixture.path(),
        "src/main/java/com/acme/B.java",
        "package com.acme; public class B {}\n",
    );
    write(
        fixture.path(),
        "src/main/java/com/acme/Service.java",
        "package com.acme; public interface Service { void left(); void right(); }\n",
    );

    let result = scan_repo(fixture.path().to_str().unwrap()).unwrap();
    assert_eq!(result.language, Language::Java);
    assert!(has_edge(&result, "com.acme.A", "com.acme.B"));
    assert!(result.classes["com.acme.Service"].is_abstract);
    let metrics = compute_agq(&result);
    assert_eq!(metrics.cohesion, Some(1.0));
}

#[test]
fn qualified_class_keys_preserve_duplicate_short_names() {
    let fixture = TempDir::new().unwrap();
    write(fixture.path(), "pom.xml", "<project/>\n");
    write(
        fixture.path(),
        "src/main/java/com/left/Config.java",
        "package com.left; public class Config { void a() {} void b() {} }\n",
    );
    write(
        fixture.path(),
        "src/main/java/com/right/Config.java",
        "package com.right; public class Config { void a() {} void b() {} }\n",
    );
    let result = scan_repo(fixture.path().to_str().unwrap()).unwrap();
    assert!(result.classes.contains_key("com.left.Config"));
    assert!(result.classes.contains_key("com.right.Config"));
}
