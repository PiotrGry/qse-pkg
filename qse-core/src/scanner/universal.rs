/// Universal tree-sitter based scanner for Python, Java, Go, TypeScript.
///
/// Produces a dependency graph + class metadata from source files,
/// regardless of language. Same output format for all languages —
/// AGQ metrics are computed identically.
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use petgraph::graph::DiGraph;
use petgraph::graph::NodeIndex;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use tree_sitter::{Language as TSLanguage, Parser, Node};

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Language {
    Python,
    Java,
    Go,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClassInfo {
    pub name: String,
    pub file_path: String,
    pub is_abstract: bool,
    /// (method_name, {attribute_names}) for LCOM4
    pub method_attrs: Vec<(String, HashSet<String>)>,
}

#[derive(Debug)]
pub struct ScanResult {
    /// Full import dependency graph (internal + external nodes)
    pub graph: DiGraph<String, ()>,
    /// Internal-only graph: source files + their direct import targets.
    /// Mirrors Python's _build_internal_graph(). Use this for AGQ metrics
    /// to avoid stdlib/third-party nodes inflating the graph.
    pub internal_graph: DiGraph<String, ()>,
    /// Node indices keyed by module path
    pub node_index: HashMap<String, NodeIndex>,
    /// Class metadata keyed by class name
    pub classes: HashMap<String, ClassInfo>,
    /// All scanned file paths
    pub files: Vec<PathBuf>,
    /// Language detected
    pub language: Language,
    /// Set of internal node names (files we actually scanned)
    pub internal_nodes: std::collections::HashSet<String>,
}

// ---------------------------------------------------------------------------
// Language detection
// ---------------------------------------------------------------------------

fn walkdir_shallow(dir: &Path, max_depth: usize) -> Vec<PathBuf> {
    let mut result = Vec::new();
    walkdir_rec(dir, max_depth, &mut result);
    result
}

fn walkdir_rec(dir: &Path, depth: usize, out: &mut Vec<PathBuf>) {
    if depth == 0 { return; }
    let Ok(entries) = std::fs::read_dir(dir) else { return };
    for e in entries.flatten() {
        let p = e.path();
        if p.is_dir() {
            let n = p.file_name().and_then(|n| n.to_str()).unwrap_or("");
            if !n.starts_with('.') && !matches!(n, "target" | "__pycache__" | "node_modules") {
                walkdir_rec(&p, depth - 1, out);
            }
        } else {
            out.push(p);
        }
    }
}

fn detect_language(dir: &Path) -> Option<Language> {
    let mut py = 0usize;
    let mut java = 0usize;
    let mut go = 0usize;

    if let Ok(entries) = std::fs::read_dir(dir) {
        for e in entries.flatten().take(200) {
            match e.path().extension().and_then(|s| s.to_str()) {
                Some("py")   => py   += 1,
                Some("java") => java += 1,
                Some("go")   => go   += 1,
                _ => {}
            }
        }
    }
    // Recurse one level
    if let Ok(entries) = std::fs::read_dir(dir) {
        for e in entries.flatten() {
            if e.path().is_dir() {
                if let Ok(sub) = std::fs::read_dir(e.path()) {
                    for f in sub.flatten().take(50) {
                        match f.path().extension().and_then(|s| s.to_str()) {
                            Some("py")   => py   += 1,
                            Some("java") => java += 1,
                            Some("go")   => go   += 1,
                            _ => {}
                        }
                    }
                }
            }
        }
    }

    // Deep scan fallback — skip test directories to find main sources
    if py == 0 && java == 0 && go == 0 {
        for entry in walkdir_shallow(dir, 8) {
            let path_str = entry.to_string_lossy();
            // Skip test paths so main source files are detected
            if path_str.contains("/test/") || path_str.contains("/tests/") {
                continue;
            }
            match entry.extension().and_then(|s| s.to_str()) {
                Some("py")   => py   += 1,
                Some("java") => java += 1,
                Some("go")   => go   += 1,
                _ => {}
            }
            if py + java + go > 20 { break; }
        }
    }
    // Last resort: count all Java files including tests
    if py == 0 && java == 0 && go == 0 {
        for entry in walkdir_shallow(dir, 8) {
            match entry.extension().and_then(|s| s.to_str()) {
                Some("java") => java += 1,
                _ => {}
            }
            if java > 5 { break; }
        }
    }
    if py == 0 && java == 0 && go == 0 { return None; }

    // FIX: require minimum 5 source files to avoid misclassifying
    // documentation/config repos that have 1-2 .py build scripts.
    // Examples: the-book-of-secret-knowledge, gitignore, prompts.chat
    // all have 0-2 .py files but are pure Markdown repos.
    let max_count = py.max(java).max(go);
    if max_count < 5 { return None; }

    // For mixed repos (e.g. Go project with Python build scripts):
    // trust Go/Java over Python if they have any meaningful presence
    // Python build scripts are common in non-Python projects
    if go > 0 && py > 0 && go >= py / 4 { return Some(Language::Go); }
    if java > 0 && py > 0 && java >= py / 4 { return Some(Language::Java); }
    if java >= py && java >= go { return Some(Language::Java); }
    if go   >= py && go   >= java { return Some(Language::Go); }
    Some(Language::Python)
}

fn ts_language(lang: &Language) -> TSLanguage {
    match lang {
        Language::Python => tree_sitter_python::LANGUAGE.into(),
        Language::Java   => tree_sitter_java::LANGUAGE.into(),
        Language::Go     => tree_sitter_go::LANGUAGE.into(),
    }
}

fn file_extension(lang: &Language) -> &'static str {
    match lang {
        Language::Python => "py",
        Language::Java   => "java",
        Language::Go     => "go",
    }
}

// ---------------------------------------------------------------------------
// Module path helpers
// ---------------------------------------------------------------------------

fn module_path(file: &Path, base: &Path, lang: &Language) -> String {
    match lang {
        Language::Java => {
            // For Java: read package declaration from file → "com.google.common.collect"
            // Then append class name → "com.google.common.collect.ImmutableList"
            // This gives semantically correct node names regardless of directory layout.
            if let Ok(src) = std::fs::read_to_string(file) {
                if let Some(pkg) = _java_package(&src) {
                    let class_name = file.file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or("Unknown");
                    return format!("{}.{}", pkg, class_name);
                }
            }
            // Fallback: path-based (strips leading path segments up to src/main/java/)
            _java_path_fallback(file, base)
        }
        Language::Go => {
            // Go: strip base + extension, use directory as package
            let rel = file.strip_prefix(base).unwrap_or(file);
            rel.to_string_lossy()
                .replace(std::path::MAIN_SEPARATOR, ".")
                .trim_end_matches(".go")
                .to_string()
        }
        Language::Python => {
            let rel = file.strip_prefix(base).unwrap_or(file);
            let s = rel.to_string_lossy()
                .replace(std::path::MAIN_SEPARATOR, ".")
                .trim_end_matches(".py")
                .to_string();
            if s.ends_with(".__init__") { s[..s.len()-9].to_string() } else { s }
        }
    }
}

/// Extract Java package declaration: "package com.google.common.collect;" → "com.google.common.collect"
fn _java_package(source: &str) -> Option<String> {
    for line in source.lines().take(30) {
        let t = line.trim();
        if t.starts_with("package ") && t.ends_with(';') {
            let pkg = t.trim_start_matches("package ").trim_end_matches(';').trim();
            if !pkg.is_empty() {
                return Some(pkg.to_string());
            }
        }
        // Stop scanning after first non-comment, non-blank, non-package line
        if !t.is_empty() && !t.starts_with("//") && !t.starts_with("/*")
            && !t.starts_with("*") && !t.starts_with("package ")
            && !t.starts_with("import ")
        {
            break;
        }
    }
    None
}

/// Fallback Java module path: find "src/main/java/" or "src/" prefix and strip it.
fn _java_path_fallback(file: &Path, base: &Path) -> String {
    let rel = file.strip_prefix(base).unwrap_or(file);
    let s = rel.to_string_lossy().replace(std::path::MAIN_SEPARATOR, ".");
    // Strip common Maven prefixes: src.main.java., src.java., etc.
    for prefix in &["src.main.java.", "src.java.", "main.java.", "java."] {
        if let Some(stripped) = s.strip_prefix(prefix) {
            return stripped.trim_end_matches(".java").to_string();
        }
    }
    s.trim_end_matches(".java").to_string()
}

// ---------------------------------------------------------------------------
// File collection
// ---------------------------------------------------------------------------

fn collect_files(base: &Path, ext: &str) -> Vec<PathBuf> {
    let mut result = Vec::new();
    collect_recursive(base, ext, &mut result);
    result.sort();
    result
}

fn collect_recursive(dir: &Path, ext: &str, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else { return };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");

            // Skip hidden dirs, build artifacts, test directories
            if name.starts_with('.')
                || matches!(name, "node_modules" | "target" | "__pycache__" | ".git"
                            | "dist" | "build" | "out" | "bin" | "gen" | "generated")
            {
                continue;
            }

            // For Java: skip test source directories
            if ext == "java"
                && (matches!(name, "test" | "tests" | "androidTest" | "testFixtures"
                             | "workspace" | "it" | "integrationTest")
                    || name.contains(".tests.")
                    || name.contains(".test."))
            {
                continue;
            }

            // FIX: Java multi-module optimization
            // If this subdir has src/main/java/, recurse into that directly
            // instead of scanning the whole subdir tree.
            // This correctly handles: spring-cloud, spring-data, hibernate
            // which have structure: module-name/src/main/java/...
            if ext == "java" {
                let smj = path.join("src").join("main").join("java");
                if smj.is_dir() {
                    collect_recursive(&smj, ext, out);
                    continue; // Don't also recurse into path itself
                }
            }

            collect_recursive(&path, ext, out);
        } else if path.extension().and_then(|e| e.to_str()) == Some(ext) {
            let fname = path.file_name().and_then(|n| n.to_str()).unwrap_or("");

            // Python: skip __init__.py (scanner adds it separately)
            if ext == "py" && fname == "__init__.py" {
                continue;
            }
            // Python: skip common non-source files
            if ext == "py" && matches!(fname, "setup.py" | "conftest.py"
                | "manage.py" | "wsgi.py" | "asgi.py") {
                continue;
            }

            out.push(path);
        }
    }
}

// ---------------------------------------------------------------------------
// Language-specific AST extraction
// ---------------------------------------------------------------------------

fn extract_python(source: &[u8], tree: &tree_sitter::Tree, file: &Path, base: &Path)
    -> (Vec<String>, Vec<ClassInfo>)
{
    let root = tree.root_node();
    let text = std::str::from_utf8(source).unwrap_or("");
    let mut imports = Vec::new();
    let mut classes = Vec::new();

    extract_python_node(root, text, file, base, &mut imports, &mut classes);
    (imports, classes)
}

fn node_text<'a>(node: Node, source: &'a str) -> &'a str {
    source.get(node.start_byte()..node.end_byte()).unwrap_or("")
}

fn extract_python_node(
    node: Node,
    source: &str,
    file: &Path,
    base: &Path,
    imports: &mut Vec<String>,
    classes: &mut Vec<ClassInfo>,
) {
    match node.kind() {
        "import_statement" => {
            // import os, sys
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                if child.kind() == "dotted_name" || child.kind() == "aliased_import" {
                    let name = node_text(child, source).split(" as ").next().unwrap_or("").trim();
                    imports.push(name.to_string());
                }
            }
        }
        "import_from_statement" => {
            // from os.path import join
            let mut cursor = node.walk();
            let mut module = String::new();
            for child in node.children(&mut cursor) {
                if child.kind() == "dotted_name" && module.is_empty() {
                    module = node_text(child, source).to_string();
                    break;
                }
                if child.kind() == "relative_import" {
                    // from . import x — skip relative
                    return;
                }
            }
            if !module.is_empty() {
                imports.push(module);
            }
        }
        "class_definition" => {
            let mut name = String::new();
            let mut bases: Vec<String> = Vec::new();
            let mut method_attrs: Vec<(String, HashSet<String>)> = Vec::new();
            let mut is_abstract = false;

            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                match child.kind() {
                    "identifier" if name.is_empty() => {
                        name = node_text(child, source).to_string();
                    }
                    "argument_list" => {
                        let mut c2 = child.walk();
                        for base in child.children(&mut c2) {
                            let b = node_text(base, source);
                            if matches!(b, "ABC" | "ABCMeta" | "Protocol") {
                                is_abstract = true;
                            }
                            bases.push(b.to_string());
                        }
                    }
                    "block" => {
                        extract_python_methods(child, source, &mut method_attrs, &mut is_abstract);
                    }
                    _ => {}
                }
            }

            if !name.is_empty() {
                classes.push(ClassInfo {
                    name,
                    file_path: file.to_string_lossy().into_owned(),
                    is_abstract,
                    method_attrs,
                });
            }
        }
        _ => {
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                extract_python_node(child, source, file, base, imports, classes);
            }
        }
    }
}

fn extract_python_methods(
    block: Node,
    source: &str,
    methods: &mut Vec<(String, HashSet<String>)>,
    is_abstract: &mut bool,
) {
    let mut cursor = block.walk();
    for child in block.children(&mut cursor) {
        if child.kind() == "function_definition" || child.kind() == "decorated_definition" {
            let actual = if child.kind() == "decorated_definition" {
                // Check for @abstractmethod
                let mut c = child.walk();
                let mut func_node = None;
                for n in child.children(&mut c) {
                    if n.kind() == "decorator" {
                        let dtext = node_text(n, source);
                        if dtext.contains("abstractmethod") {
                            *is_abstract = true;
                        }
                    }
                    if n.kind() == "function_definition" {
                        func_node = Some(n);
                    }
                }
                match func_node { Some(n) => n, None => continue }
            } else {
                child
            };

            let mut fname = String::new();
            let mut attrs: HashSet<String> = HashSet::new();
            let mut c2 = actual.walk();
            for n in actual.children(&mut c2) {
                if n.kind() == "identifier" && fname.is_empty() {
                    fname = node_text(n, source).to_string();
                }
                if n.kind() == "block" {
                    collect_self_attrs(n, source, &mut attrs);
                }
            }
            if !fname.is_empty() {
                methods.push((fname, attrs));
            }
        }
    }
}

fn collect_self_attrs(node: Node, source: &str, attrs: &mut HashSet<String>) {
    if node.kind() == "attribute" {
        let mut cursor = node.walk();
        let children: Vec<Node> = node.children(&mut cursor).collect();
        if children.len() >= 3 {
            let obj = node_text(children[0], source);
            let attr = node_text(children[2], source);
            if obj == "self" {
                attrs.insert(attr.to_string());
            }
        }
        return;
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_self_attrs(child, source, attrs);
    }
}

// ---------------------------------------------------------------------------
// Java AST extraction
// ---------------------------------------------------------------------------

fn extract_java(source: &[u8], tree: &tree_sitter::Tree, file: &Path, base: &Path)
    -> (Vec<String>, Vec<ClassInfo>)
{
    let root = tree.root_node();
    let text = std::str::from_utf8(source).unwrap_or("");
    let mut imports = Vec::new();
    let mut classes = Vec::new();

    let mut cursor = root.walk();
    for child in root.children(&mut cursor) {
        match child.kind() {
            "import_declaration" => {
                // import com.example.service.OrderService;
                let imp = node_text(child, text)
                    .trim_start_matches("import ")
                    .trim_start_matches("static ")
                    .trim_end_matches(';')
                    .trim()
                    .trim_end_matches(".*");
                if !imp.is_empty() {
                    imports.push(imp.to_string());
                }
            }
            "class_declaration" | "interface_declaration" | "enum_declaration" => {
                if let Some(ci) = extract_java_class(child, text, file, base) {
                    classes.push(ci);
                }
            }
            _ => {}
        }
    }
    (imports, classes)
}

fn extract_java_class(node: Node, source: &str, file: &Path, _base: &Path) -> Option<ClassInfo> {
    let mut name = String::new();
    let mut is_abstract = false;
    let mut method_attrs: Vec<(String, HashSet<String>)> = Vec::new();

    // Check modifiers for abstract
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        match child.kind() {
            "modifiers" => {
                if node_text(child, source).contains("abstract") {
                    is_abstract = true;
                }
            }
            "identifier" if name.is_empty() => {
                name = node_text(child, source).to_string();
            }
            "class_body" | "interface_body" | "enum_body" => {
                extract_java_methods(child, source, &mut method_attrs);
            }
            _ => {}
        }
    }

    // interface is always abstract
    if node.kind() == "interface_declaration" {
        is_abstract = true;
    }

    if name.is_empty() { return None; }

    Some(ClassInfo {
        name,
        file_path: file.to_string_lossy().into_owned(),
        is_abstract,
        method_attrs,
    })
}

fn extract_java_methods(node: Node, source: &str, methods: &mut Vec<(String, HashSet<String>)>) {
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        if child.kind() == "method_declaration" || child.kind() == "constructor_declaration" {
            let mut fname = String::new();
            let mut attrs: HashSet<String> = HashSet::new();
            let mut c2 = child.walk();
            for n in child.children(&mut c2) {
                if n.kind() == "identifier" && fname.is_empty() {
                    fname = node_text(n, source).to_string();
                }
                if n.kind() == "block" {
                    collect_java_fields(n, source, &mut attrs);
                }
            }
            if !fname.is_empty() {
                methods.push((fname, attrs));
            }
        }
    }
}

fn collect_java_fields(node: Node, source: &str, attrs: &mut HashSet<String>) {
    // Collect this.fieldName accesses
    if node.kind() == "field_access" {
        let mut cursor = node.walk();
        let children: Vec<Node> = node.children(&mut cursor).collect();
        if children.len() >= 3 {
            let obj = node_text(children[0], source);
            let field = node_text(children[2], source);
            if obj == "this" {
                attrs.insert(field.to_string());
            }
        }
        return;
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_java_fields(child, source, attrs);
    }
}

// ---------------------------------------------------------------------------
// Go AST extraction
// ---------------------------------------------------------------------------

fn extract_go(source: &[u8], tree: &tree_sitter::Tree, file: &Path, _base: &Path)
    -> (Vec<String>, Vec<ClassInfo>)
{
    let root = tree.root_node();
    let text = std::str::from_utf8(source).unwrap_or("");
    let mut imports = Vec::new();
    let mut classes = Vec::new(); // Go structs as "classes"

    let mut cursor = root.walk();
    for child in root.children(&mut cursor) {
        match child.kind() {
            "import_declaration" => {
                extract_go_imports(child, text, &mut imports);
            }
            "type_declaration" => {
                if let Some(ci) = extract_go_struct(child, text, file) {
                    classes.push(ci);
                }
            }
            _ => {}
        }
    }
    (imports, classes)
}

fn extract_go_imports(node: Node, source: &str, imports: &mut Vec<String>) {
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        if child.kind() == "import_spec" || child.kind() == "import_spec_list" {
            let mut c2 = child.walk();
            for n in child.children(&mut c2) {
                if n.kind() == "interpreted_string_literal" {
                    let path = node_text(n, source).trim_matches('"');
                    imports.push(path.to_string());
                }
                if n.kind() == "import_spec" {
                    let mut c3 = n.walk();
                    for m in n.children(&mut c3) {
                        if m.kind() == "interpreted_string_literal" {
                            let path = node_text(m, source).trim_matches('"');
                            imports.push(path.to_string());
                        }
                    }
                }
            }
        }
    }
}

fn extract_go_struct(node: Node, source: &str, file: &Path) -> Option<ClassInfo> {
    let mut name = String::new();
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        if child.kind() == "type_spec" {
            let mut c2 = child.walk();
            for n in child.children(&mut c2) {
                if n.kind() == "type_identifier" && name.is_empty() {
                    name = node_text(n, source).to_string();
                }
            }
        }
    }
    if name.is_empty() { return None; }
    Some(ClassInfo {
        name,
        file_path: file.to_string_lossy().into_owned(),
        is_abstract: false,
        method_attrs: vec![],
    })
}

// ---------------------------------------------------------------------------
// Main scan_repo function
// ---------------------------------------------------------------------------

/// Per-file parse result (produced in parallel, merged serially)
struct FileResult {
    mod_path: String,
    imports: Vec<String>,
    classes: Vec<ClassInfo>,
}

/// Find the actual source root for any language.
/// Python: tries src/<name>/, src/, <name>/  (pip/poetry layout)
/// Java:   tries src/main/java/, src/main/  (Maven/Gradle layout)
/// Go:     repo root is typically correct
fn find_source_root(base: &Path) -> PathBuf {
    let name = base.file_name().and_then(|n| n.to_str()).unwrap_or("");

    // Java: try standard Maven layout first
    let java_root = base.join("src").join("main").join("java");
    if java_root.is_dir() && walkdir_shallow(&java_root, 2).iter()
        .any(|p| p.extension().and_then(|e| e.to_str()) == Some("java"))
    {
        return java_root;
    }

    // Java multi-module (FIX): projects like spring-cloud, spring-data-jpa
    // have structure: root/module-name/src/main/java/...
    // walkdir_shallow(base, 4) finds .java files but collect_files needs
    // to start from base so it can find ALL submodule src/main/java trees.
    // Previously returned base which is correct — but detect_language was
    // returning None because shallow scan didn't find enough files.
    // The real fix is in detect_language (minimum 5 files) + collect_recursive
    // skipping test dirs. This path is still correct.
    if walkdir_shallow(base, 6).iter()
        .any(|p| p.extension().and_then(|e| e.to_str()) == Some("java"))
    {
        return base.to_path_buf();
    }

    // Python: try common source layouts
    // (src/<name>/, src/, <name>/) — pip/poetry/hatch conventions
    let py_candidates = [
        base.join("src").join(name),
        base.join("src"),
        base.join(name),
        // FIX: also try direct root — many flat Python libs live at root level
        base.to_path_buf(),
    ];
    for c in &py_candidates {
        if c.is_dir() && walkdir_shallow(c, 2).iter()
            .filter(|p| {
                // Only count non-test, non-generated .py files
                let s = p.to_string_lossy();
                !s.contains("/test") && !s.contains("setup.py")
                    && !s.contains("conftest.py")
            })
            .any(|p| p.extension().and_then(|e| e.to_str()) == Some("py"))
        {
            return c.clone();
        }
    }
    base.to_path_buf()
}

pub fn scan_repo(base_dir: &str) -> ScanResult {
    let base_root = find_source_root(Path::new(base_dir));
    let base = base_root.as_path();
    let lang = detect_language(base).unwrap_or(Language::Python);
    let ext = file_extension(&lang);
    let ts_lang = ts_language(&lang);

    let files = collect_files(base, ext);

    // Parse files in parallel using rayon — each thread gets its own Parser
    let file_results: Vec<FileResult> = files.par_iter().filter_map(|file_path| {
        let Ok(source) = std::fs::read(file_path) else { return None };
        // Skip files >1MB (likely generated/fixture data) and non-UTF-8
        if source.len() > 1_048_576 { return None; }
        if std::str::from_utf8(&source).is_err() { return None; }
        let mut parser = Parser::new();
        parser.set_language(&ts_lang).ok()?;
        let tree = parser.parse(&source, None)?;
        let mod_path = module_path(file_path, base, &lang);
        let (imports, classes) = match lang {
            Language::Python => extract_python(&source, &tree, file_path, base),
            Language::Java   => extract_java(&source, &tree, file_path, base),
            Language::Go     => extract_go(&source, &tree, file_path, base),
        };
        Some(FileResult { mod_path, imports, classes })
    }).collect();

    // Merge results into graph (serial — graph is not thread-safe)
    let mut graph: DiGraph<String, ()> = DiGraph::new();
    let mut node_index: HashMap<String, NodeIndex> = HashMap::new();
    let mut classes: HashMap<String, ClassInfo> = HashMap::new();

    let get_node = |g: &mut DiGraph<String, ()>,
                        idx: &mut HashMap<String, NodeIndex>,
                        name: String| -> NodeIndex {
        if let Some(&ni) = idx.get(&name) { ni }
        else { let ni = g.add_node(name.clone()); idx.insert(name, ni); ni }
    };

    let mut scanned_files = Vec::new();
    let mut internal_nodes: std::collections::HashSet<String> = std::collections::HashSet::new();

    for fr in file_results {
        internal_nodes.insert(fr.mod_path.clone());
        let src_node = get_node(&mut graph, &mut node_index, fr.mod_path.clone());
        for imp in fr.imports {
            let tgt_node = get_node(&mut graph, &mut node_index, imp);
            if src_node != tgt_node && !graph.contains_edge(src_node, tgt_node) {
                graph.add_edge(src_node, tgt_node, ());
            }
        }
        for cls in fr.classes {
            classes.insert(cls.name.clone(), cls);
        }
        scanned_files.push(PathBuf::from(&fr.mod_path));
    }

    // Build internal graph: internal nodes + their direct import targets
    // Mirrors Python's _build_internal_graph() — excludes stdlib/third-party
    // nodes that are never imported by anything internal.
    let mut connected: std::collections::HashSet<String> = std::collections::HashSet::new();
    for ni in graph.node_indices() {
        let name = &graph[ni];
        if internal_nodes.contains(name) {
            connected.insert(name.clone());
            for nb in graph.neighbors(ni) {
                connected.insert(graph[nb].clone());
            }
        }
    }
    let mut internal_graph: DiGraph<String, ()> = DiGraph::new();
    let mut int_idx: HashMap<String, NodeIndex> = HashMap::new();
    for name in &connected {
        let ni = internal_graph.add_node(name.clone());
        int_idx.insert(name.clone(), ni);
    }
    for e in graph.edge_indices() {
        let (a, b) = graph.edge_endpoints(e).unwrap();
        let an = &graph[a];
        let bn = &graph[b];
        if let (Some(&ia), Some(&ib)) = (int_idx.get(an), int_idx.get(bn)) {
            if !internal_graph.contains_edge(ia, ib) {
                internal_graph.add_edge(ia, ib, ());
            }
        }
    }

    ScanResult {
        graph,
        internal_graph,
        node_index,
        classes,
        files: scanned_files,
        language: lang,
        internal_nodes,
    }
}
