//! Language-aware source scanner used by the Rust AGQ implementation.
//!
//! The scanners share a result schema, but not a dependency model:
//! Python and Java use file/module nodes, while Go uses package nodes.

use petgraph::graph::{DiGraph, NodeIndex};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeSet, HashMap, HashSet};
use std::fmt;
use std::path::{Path, PathBuf};
use tree_sitter::{Language as TSLanguage, Node, Parser};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Language {
    Python,
    Java,
    Go,
}

impl Language {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Python => "Python",
            Self::Java => "Java",
            Self::Go => "Go",
        }
    }
}

impl fmt::Display for Language {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClassInfo {
    pub name: String,
    /// Module/package-qualified identity. This is also the key in ScanResult::classes.
    pub qualified_name: String,
    pub file_path: String,
    pub is_abstract: bool,
    /// (method_name, {field-or-method markers}) for LCOM4.
    pub method_attrs: Vec<(String, HashSet<String>)>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ScanDiagnostics {
    pub discovered_files: usize,
    pub parsed_files: usize,
    pub skipped_files: usize,
    pub external_imports: usize,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ScanError {
    InvalidPath(String),
    NoSupportedSources,
    AmbiguousLanguage {
        python: usize,
        java: usize,
        go: usize,
    },
    NoParsedFiles {
        language: Language,
        discovered: usize,
    },
}

impl fmt::Display for ScanError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidPath(path) => write!(f, "repository path is not a readable directory: {path}"),
            Self::NoSupportedSources => {
                f.write_str("no supported Python, Java, or Go source files were found")
            }
            Self::AmbiguousLanguage { python, java, go } => write!(
                f,
                "repository is multi-language or ambiguous (Python={python}, Java={java}, Go={go}); scan a language-specific subdirectory"
            ),
            Self::NoParsedFiles {
                language,
                discovered,
            } => write!(
                f,
                "found {discovered} {language} source files, but none could be parsed"
            ),
        }
    }
}

impl std::error::Error for ScanError {}

#[derive(Debug)]
pub struct ScanResult {
    /// Full graph, including unresolved external import targets.
    pub graph: DiGraph<String, ()>,
    /// True induced graph of scanned internal nodes only.
    pub internal_graph: DiGraph<String, ()>,
    /// Indices in `graph`, keyed by canonical node identity.
    pub node_index: HashMap<String, NodeIndex>,
    /// Source files contributing to each canonical node. Go packages may have many files.
    pub node_files: HashMap<String, Vec<PathBuf>>,
    /// Class metadata keyed by qualified identity.
    pub classes: HashMap<String, ClassInfo>,
    /// Actual successfully parsed source paths.
    pub files: Vec<PathBuf>,
    pub language: Language,
    pub internal_nodes: HashSet<String>,
    pub diagnostics: ScanDiagnostics,
}

#[derive(Debug, Default, Clone, Copy)]
struct LanguageCounts {
    python: usize,
    java: usize,
    go: usize,
}

impl LanguageCounts {
    fn total(self) -> usize {
        self.python + self.java + self.go
    }

    fn for_language(self, language: Language) -> usize {
        match language {
            Language::Python => self.python,
            Language::Java => self.java,
            Language::Go => self.go,
        }
    }
}

fn ignored_dir(name: &str) -> bool {
    name.starts_with('.')
        || matches!(
            name,
            "target"
                | "__pycache__"
                | "node_modules"
                | "dist"
                | "build"
                | "out"
                | "bin"
                | "gen"
                | "generated"
                | "vendor"
                | "test"
                | "tests"
                | "androidTest"
                | "testFixtures"
                | "integrationTest"
        )
}

fn count_languages(base: &Path) -> LanguageCounts {
    let mut counts = LanguageCounts::default();
    let mut stack = vec![base.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(entries) = std::fs::read_dir(dir) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
                if !ignored_dir(name) {
                    stack.push(path);
                }
                continue;
            }
            match path.extension().and_then(|e| e.to_str()) {
                Some("py") => counts.python += 1,
                Some("java") => counts.java += 1,
                Some("go") if !path.to_string_lossy().ends_with("_test.go") => counts.go += 1,
                _ => {}
            }
        }
    }
    counts
}

fn root_marker(base: &Path, language: Language) -> bool {
    match language {
        Language::Python => ["pyproject.toml", "setup.py", "setup.cfg"]
            .iter()
            .any(|name| base.join(name).is_file()),
        Language::Java => [
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "settings.gradle",
        ]
        .iter()
        .any(|name| base.join(name).is_file()),
        Language::Go => base.join("go.mod").is_file(),
    }
}

fn detect_language(base: &Path) -> Result<Language, ScanError> {
    let counts = count_languages(base);
    if counts.total() == 0 {
        return Err(ScanError::NoSupportedSources);
    }

    let present: Vec<Language> = [Language::Python, Language::Java, Language::Go]
        .into_iter()
        .filter(|&language| counts.for_language(language) > 0)
        .collect();
    if present.len() == 1 {
        return Ok(present[0]);
    }

    let marked: Vec<Language> = present
        .iter()
        .copied()
        .filter(|&language| root_marker(base, language))
        .collect();
    if marked.len() == 1 {
        let marked_language = marked[0];
        let largest_other = [Language::Python, Language::Java, Language::Go]
            .into_iter()
            .filter(|&language| language != marked_language)
            .map(|language| counts.for_language(language))
            .max()
            .unwrap_or(0);
        // setup.py/pyproject.toml also appear as tooling in non-Python projects;
        // do not let a tiny Python helper override a much larger codebase.
        if marked_language != Language::Python
            || counts.for_language(marked_language) >= largest_other
        {
            return Ok(marked_language);
        }
    }

    let mut ranked = present;
    ranked.sort_by_key(|&language| std::cmp::Reverse(counts.for_language(language)));
    let first = counts.for_language(ranked[0]);
    let second = counts.for_language(ranked[1]);
    if first >= second.saturating_mul(4) {
        return Ok(ranked[0]);
    }

    Err(ScanError::AmbiguousLanguage {
        python: counts.python,
        java: counts.java,
        go: counts.go,
    })
}

fn ts_language(language: Language) -> TSLanguage {
    match language {
        Language::Python => tree_sitter_python::LANGUAGE.into(),
        Language::Java => tree_sitter_java::LANGUAGE.into(),
        Language::Go => tree_sitter_go::LANGUAGE.into(),
    }
}

fn file_extension(language: Language) -> &'static str {
    match language {
        Language::Python => "py",
        Language::Java => "java",
        Language::Go => "go",
    }
}

fn contains_extension(base: &Path, extension: &str) -> bool {
    let mut stack = vec![base.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(entries) = std::fs::read_dir(dir) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
                if !ignored_dir(name) {
                    stack.push(path);
                }
            } else if path.extension().and_then(|e| e.to_str()) == Some(extension) {
                return true;
            }
        }
    }
    false
}

fn find_source_root(base: &Path, language: Language) -> PathBuf {
    match language {
        Language::Java => {
            let standard = base.join("src").join("main").join("java");
            if contains_extension(&standard, "java") {
                standard
            } else {
                base.to_path_buf()
            }
        }
        Language::Python => {
            let src = base.join("src");
            if contains_extension(&src, "py") {
                // Keep the top-level package in canonical module names.
                src
            } else {
                base.to_path_buf()
            }
        }
        Language::Go => base.to_path_buf(),
    }
}

fn collect_files(base: &Path, language: Language) -> Vec<PathBuf> {
    let extension = file_extension(language);
    let mut files = Vec::new();
    let mut stack = vec![base.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let Ok(entries) = std::fs::read_dir(dir) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
                if !ignored_dir(name) {
                    stack.push(path);
                }
            } else if path.extension().and_then(|e| e.to_str()) == Some(extension) {
                if language == Language::Go && path.to_string_lossy().ends_with("_test.go") {
                    continue;
                }
                files.push(path);
            }
        }
    }
    files.sort();
    files
}

fn relative_components(file: &Path, base: &Path) -> Vec<String> {
    file.strip_prefix(base)
        .unwrap_or(file)
        .components()
        .map(|component| component.as_os_str().to_string_lossy().into_owned())
        .collect()
}

fn java_package(source: &str) -> Option<String> {
    for line in source.lines().take(100) {
        let trimmed = line.trim();
        if let Some(rest) = trimmed.strip_prefix("package ") {
            let package = rest.split(';').next().unwrap_or(rest).trim();
            if !package.is_empty() {
                return Some(package.to_string());
            }
        }
    }
    None
}

fn module_path(file: &Path, base: &Path, language: Language, source: &str) -> String {
    match language {
        Language::Python => {
            let mut parts = relative_components(file, base);
            if let Some(last) = parts.last_mut() {
                *last = last.trim_end_matches(".py").to_string();
            }
            if parts.last().is_some_and(|last| last == "__init__") {
                parts.pop();
            }
            if parts.is_empty() {
                "__root__".to_string()
            } else {
                parts.join(".")
            }
        }
        Language::Java => {
            let stem = file
                .file_stem()
                .and_then(|s| s.to_str())
                .unwrap_or("Unknown");
            java_package(source)
                .map(|package| format!("{package}.{stem}"))
                .unwrap_or_else(|| {
                    let mut parts = relative_components(file, base);
                    if let Some(last) = parts.last_mut() {
                        *last = last.trim_end_matches(".java").to_string();
                    }
                    parts.join(".")
                })
        }
        Language::Go => {
            let relative = file.strip_prefix(base).unwrap_or(file);
            let parent = relative.parent().unwrap_or_else(|| Path::new(""));
            let parts: Vec<String> = parent
                .components()
                .map(|component| component.as_os_str().to_string_lossy().into_owned())
                .collect();
            if parts.is_empty() {
                ".".to_string()
            } else {
                parts.join("/")
            }
        }
    }
}

fn read_go_module(base: &Path) -> Option<String> {
    let source = std::fs::read_to_string(base.join("go.mod")).ok()?;
    source.lines().find_map(|line| {
        let trimmed = line.trim();
        trimmed
            .strip_prefix("module ")
            .map(str::trim)
            .filter(|module| !module.is_empty())
            .map(str::to_string)
    })
}

#[derive(Debug, Clone)]
enum ImportRef {
    Exact(String),
    From { base: String, members: Vec<String> },
    Wildcard(String),
}

#[derive(Debug)]
struct FileResult {
    file_path: PathBuf,
    mod_path: String,
    imports: Vec<ImportRef>,
    classes: Vec<ClassInfo>,
    referenced_types: BTreeSet<String>,
}

fn node_text<'a>(node: Node, source: &'a str) -> &'a str {
    source.get(node.start_byte()..node.end_byte()).unwrap_or("")
}

fn python_package(module: &str, file: &Path) -> String {
    if file.file_name().and_then(|n| n.to_str()) == Some("__init__.py") {
        return module.to_string();
    }
    module
        .rsplit_once('.')
        .map(|(package, _)| package)
        .unwrap_or("")
        .to_string()
}

fn resolve_python_base(raw: &str, current_package: &str) -> String {
    let level = raw.chars().take_while(|&c| c == '.').count();
    if level == 0 {
        return raw.to_string();
    }
    let suffix = raw.trim_start_matches('.');
    let mut parts: Vec<&str> = current_package
        .split('.')
        .filter(|part| !part.is_empty())
        .collect();
    for _ in 0..level.saturating_sub(1) {
        parts.pop();
    }
    if !suffix.is_empty() {
        parts.extend(suffix.split('.'));
    }
    parts.join(".")
}

fn parse_python_import(text: &str) -> Vec<ImportRef> {
    text.trim()
        .strip_prefix("import ")
        .into_iter()
        .flat_map(|rest| rest.split(','))
        .filter_map(|item| item.split_whitespace().next())
        .filter(|item| !item.is_empty())
        .map(|item| ImportRef::Exact(item.to_string()))
        .collect()
}

fn parse_python_from(text: &str, current_package: &str) -> Option<ImportRef> {
    let normalized = text.split_whitespace().collect::<Vec<_>>().join(" ");
    let rest = normalized.strip_prefix("from ")?;
    let (raw_base, raw_members) = rest.split_once(" import ")?;
    let base = resolve_python_base(raw_base.trim(), current_package);
    if base.is_empty() {
        return None;
    }
    let members = raw_members
        .trim_matches(|c| c == '(' || c == ')')
        .split(',')
        .filter_map(|member| member.split_whitespace().next())
        .filter(|member| !member.is_empty() && *member != "*")
        .map(str::to_string)
        .collect();
    Some(ImportRef::From { base, members })
}

fn collect_python_method_links(
    node: Node,
    source: &str,
    method_names: &HashSet<String>,
    attrs: &mut HashSet<String>,
) {
    if node.kind() == "attribute" {
        let mut cursor = node.walk();
        let children: Vec<Node> = node.children(&mut cursor).collect();
        if children.len() >= 3 && node_text(children[0], source) == "self" {
            let name = node_text(children[2], source);
            let prefix = if method_names.contains(name) {
                "method"
            } else {
                "field"
            };
            attrs.insert(format!("{prefix}:{name}"));
            return;
        }
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_python_method_links(child, source, method_names, attrs);
    }
}

fn extract_python_methods(
    block: Node,
    source: &str,
    is_abstract: &mut bool,
) -> Vec<(String, HashSet<String>)> {
    let mut method_nodes = Vec::new();
    let mut cursor = block.walk();
    for child in block.children(&mut cursor) {
        let actual = if child.kind() == "decorated_definition" {
            let mut nested = child.walk();
            let mut function = None;
            for node in child.children(&mut nested) {
                if node.kind() == "decorator" && node_text(node, source).contains("abstractmethod")
                {
                    *is_abstract = true;
                }
                if node.kind() == "function_definition" {
                    function = Some(node);
                }
            }
            function
        } else if child.kind() == "function_definition" {
            Some(child)
        } else {
            None
        };
        if let Some(function) = actual {
            let name = function
                .child_by_field_name("name")
                .map(|node| node_text(node, source).to_string())
                .unwrap_or_default();
            if !name.is_empty() {
                method_nodes.push((name, function));
            }
        }
    }

    let method_names: HashSet<String> = method_nodes.iter().map(|(name, _)| name.clone()).collect();
    method_nodes
        .into_iter()
        .map(|(name, function)| {
            let mut attrs = HashSet::from([format!("method:{name}")]);
            if let Some(body) = function.child_by_field_name("body") {
                collect_python_method_links(body, source, &method_names, &mut attrs);
            }
            (name, attrs)
        })
        .collect()
}

fn extract_python_node(
    node: Node,
    source: &str,
    module: &str,
    file: &Path,
    imports: &mut Vec<ImportRef>,
    classes: &mut Vec<ClassInfo>,
) {
    match node.kind() {
        "import_statement" => imports.extend(parse_python_import(node_text(node, source))),
        "import_from_statement" => {
            let package = python_package(module, file);
            if let Some(import) = parse_python_from(node_text(node, source), &package) {
                imports.push(import);
            }
        }
        "class_definition" => {
            let name = node
                .child_by_field_name("name")
                .map(|child| node_text(child, source).to_string())
                .unwrap_or_default();
            let mut is_abstract = node
                .child_by_field_name("superclasses")
                .map(|child| {
                    let bases = node_text(child, source);
                    bases.contains("ABC") || bases.contains("Protocol")
                })
                .unwrap_or(false);
            let method_attrs = node
                .child_by_field_name("body")
                .map(|body| extract_python_methods(body, source, &mut is_abstract))
                .unwrap_or_default();
            if !name.is_empty() {
                let qualified_name = format!("{module}.{name}");
                classes.push(ClassInfo {
                    name,
                    qualified_name,
                    file_path: file.to_string_lossy().into_owned(),
                    is_abstract,
                    method_attrs,
                });
            }
        }
        _ => {
            let mut cursor = node.walk();
            for child in node.children(&mut cursor) {
                extract_python_node(child, source, module, file, imports, classes);
            }
        }
    }
}

fn extract_python(
    source: &str,
    tree: &tree_sitter::Tree,
    module: &str,
    file: &Path,
) -> (Vec<ImportRef>, Vec<ClassInfo>, BTreeSet<String>) {
    let mut imports = Vec::new();
    let mut classes = Vec::new();
    extract_python_node(
        tree.root_node(),
        source,
        module,
        file,
        &mut imports,
        &mut classes,
    );
    (imports, classes, BTreeSet::new())
}

fn collect_java_fields(node: Node, source: &str, fields: &mut HashSet<String>) {
    if node.kind() == "variable_declarator" {
        if let Some(name) = node.child_by_field_name("name") {
            fields.insert(node_text(name, source).to_string());
        }
        return;
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_java_fields(child, source, fields);
    }
}

fn collect_java_method_links(
    node: Node,
    source: &str,
    fields: &HashSet<String>,
    methods: &HashSet<String>,
    attrs: &mut HashSet<String>,
) {
    if node.kind() == "identifier" {
        let name = node_text(node, source);
        if fields.contains(name) {
            attrs.insert(format!("field:{name}"));
        }
        if methods.contains(name) {
            attrs.insert(format!("method:{name}"));
        }
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_java_method_links(child, source, fields, methods, attrs);
    }
}

fn extract_java_methods(body: Node, source: &str) -> Vec<(String, HashSet<String>)> {
    let mut fields = HashSet::new();
    let mut cursor = body.walk();
    for child in body.children(&mut cursor) {
        if child.kind() == "field_declaration" {
            collect_java_fields(child, source, &mut fields);
        }
    }

    let mut method_nodes = Vec::new();
    let mut cursor = body.walk();
    for child in body.children(&mut cursor) {
        if matches!(
            child.kind(),
            "method_declaration" | "constructor_declaration"
        ) {
            let name = child
                .child_by_field_name("name")
                .map(|node| node_text(node, source).to_string())
                .unwrap_or_default();
            if !name.is_empty() {
                method_nodes.push((name, child));
            }
        }
    }
    let methods: HashSet<String> = method_nodes.iter().map(|(name, _)| name.clone()).collect();
    method_nodes
        .into_iter()
        .map(|(name, method)| {
            let mut attrs = HashSet::from([format!("method:{name}")]);
            if let Some(body) = method.child_by_field_name("body") {
                collect_java_method_links(body, source, &fields, &methods, &mut attrs);
            }
            (name, attrs)
        })
        .collect()
}

fn extract_java_class(node: Node, source: &str, file: &Path, package: &str) -> Option<ClassInfo> {
    let name = node
        .child_by_field_name("name")
        .map(|child| node_text(child, source).to_string())?;
    let mut cursor = node.walk();
    let is_abstract = node.kind() == "interface_declaration"
        || node.children(&mut cursor).any(|child| {
            child.kind() == "modifiers" && node_text(child, source).contains("abstract")
        });
    let method_attrs = node
        .child_by_field_name("body")
        .map(|body| extract_java_methods(body, source))
        .unwrap_or_default();
    let qualified_name = if package.is_empty() {
        name.clone()
    } else {
        format!("{package}.{name}")
    };
    Some(ClassInfo {
        name,
        qualified_name,
        file_path: file.to_string_lossy().into_owned(),
        is_abstract,
        method_attrs,
    })
}

fn collect_java_type_references(node: Node, source: &str, out: &mut BTreeSet<String>) {
    if node.kind() == "type_identifier" {
        out.insert(node_text(node, source).to_string());
        return;
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_java_type_references(child, source, out);
    }
}

fn extract_java(
    source: &str,
    tree: &tree_sitter::Tree,
    file: &Path,
) -> (Vec<ImportRef>, Vec<ClassInfo>, BTreeSet<String>) {
    let root = tree.root_node();
    let package = java_package(source).unwrap_or_default();
    let mut imports = Vec::new();
    let mut classes = Vec::new();
    let mut cursor = root.walk();
    for child in root.children(&mut cursor) {
        match child.kind() {
            "import_declaration" => {
                let raw = node_text(child, source)
                    .trim_start_matches("import ")
                    .trim_start_matches("static ")
                    .trim_end_matches(';')
                    .trim();
                if let Some(package) = raw.strip_suffix(".*") {
                    imports.push(ImportRef::Wildcard(package.to_string()));
                } else if !raw.is_empty() {
                    imports.push(ImportRef::Exact(raw.to_string()));
                }
            }
            "class_declaration"
            | "interface_declaration"
            | "enum_declaration"
            | "record_declaration" => {
                if let Some(class) = extract_java_class(child, source, file, &package) {
                    classes.push(class);
                }
            }
            _ => {}
        }
    }
    let mut referenced_types = BTreeSet::new();
    collect_java_type_references(root, source, &mut referenced_types);
    (imports, classes, referenced_types)
}

fn collect_go_imports(node: Node, source: &str, imports: &mut Vec<ImportRef>) {
    if node.kind() == "interpreted_string_literal" {
        let import = node_text(node, source).trim_matches('"');
        if !import.is_empty() {
            imports.push(ImportRef::Exact(import.to_string()));
        }
        return;
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_go_imports(child, source, imports);
    }
}

fn collect_go_structs(
    node: Node,
    source: &str,
    module: &str,
    file: &Path,
    classes: &mut Vec<ClassInfo>,
) {
    if node.kind() == "type_spec" {
        let mut cursor = node.walk();
        let is_struct = node
            .children(&mut cursor)
            .any(|child| child.kind() == "struct_type");
        if is_struct {
            if let Some(name_node) = node.child_by_field_name("name") {
                let name = node_text(name_node, source).to_string();
                classes.push(ClassInfo {
                    qualified_name: format!("{module}.{name}"),
                    name,
                    file_path: file.to_string_lossy().into_owned(),
                    is_abstract: false,
                    method_attrs: Vec::new(),
                });
            }
        }
        return;
    }
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_go_structs(child, source, module, file, classes);
    }
}

fn extract_go(
    source: &str,
    tree: &tree_sitter::Tree,
    module: &str,
    file: &Path,
) -> (Vec<ImportRef>, Vec<ClassInfo>, BTreeSet<String>) {
    let root = tree.root_node();
    let mut imports = Vec::new();
    let mut classes = Vec::new();
    let mut cursor = root.walk();
    for child in root.children(&mut cursor) {
        if child.kind() == "import_declaration" {
            collect_go_imports(child, source, &mut imports);
        } else if child.kind() == "type_declaration" {
            collect_go_structs(child, source, module, file, &mut classes);
        }
    }
    (imports, classes, BTreeSet::new())
}

fn resolve_alias(
    raw: &str,
    aliases: &HashMap<String, String>,
    language: Language,
) -> Option<String> {
    if let Some(target) = aliases.get(raw) {
        return Some(target.clone());
    }
    if language == Language::Java {
        let mut candidate = raw;
        while let Some((prefix, _)) = candidate.rsplit_once('.') {
            if let Some(target) = aliases.get(prefix) {
                return Some(target.clone());
            }
            candidate = prefix;
        }
    }
    None
}

fn resolve_import(
    import: &ImportRef,
    aliases: &HashMap<String, String>,
    internal_nodes: &HashSet<String>,
    language: Language,
) -> Vec<(String, bool)> {
    match import {
        ImportRef::Exact(raw) => resolve_alias(raw, aliases, language)
            .map(|target| vec![(target, true)])
            .unwrap_or_else(|| vec![(raw.clone(), false)]),
        ImportRef::From { base, members } => {
            let mut targets = BTreeSet::new();
            for member in members {
                let candidate = format!("{base}.{member}");
                if let Some(target) = resolve_alias(&candidate, aliases, language) {
                    targets.insert(target);
                }
            }
            if let Some(target) = resolve_alias(base, aliases, language) {
                targets.insert(target);
            }
            if targets.is_empty() {
                vec![(base.clone(), false)]
            } else {
                targets.into_iter().map(|target| (target, true)).collect()
            }
        }
        ImportRef::Wildcard(package) => {
            let targets: Vec<(String, bool)> = internal_nodes
                .iter()
                .filter(|node| {
                    node.rsplit_once('.')
                        .map(|(parent, _)| parent == package)
                        .unwrap_or(false)
                })
                .cloned()
                .collect::<BTreeSet<_>>()
                .into_iter()
                .map(|target| (target, true))
                .collect();
            if targets.is_empty() {
                vec![(package.clone(), false)]
            } else {
                targets
            }
        }
    }
}

fn add_node(
    graph: &mut DiGraph<String, ()>,
    indices: &mut HashMap<String, NodeIndex>,
    name: String,
) -> NodeIndex {
    if let Some(&index) = indices.get(&name) {
        return index;
    }
    let index = graph.add_node(name.clone());
    indices.insert(name, index);
    index
}

pub fn scan_repo(base_dir: &str) -> Result<ScanResult, ScanError> {
    let repository = Path::new(base_dir);
    if !repository.is_dir() {
        return Err(ScanError::InvalidPath(base_dir.to_string()));
    }

    let language = detect_language(repository)?;
    let source_root = find_source_root(repository, language);
    let go_module = (language == Language::Go)
        .then(|| read_go_module(repository))
        .flatten();
    let files = collect_files(&source_root, language);
    let discovered_files = files.len();
    if discovered_files == 0 {
        return Err(ScanError::NoSupportedSources);
    }

    let ts_language = ts_language(language);
    let parsed: Vec<Result<FileResult, String>> = files
        .par_iter()
        .map(|file| {
            let bytes =
                std::fs::read(file).map_err(|error| format!("{}: {error}", file.display()))?;
            if bytes.len() > 1_048_576 {
                return Err(format!("{}: file exceeds 1 MiB", file.display()));
            }
            let source = std::str::from_utf8(&bytes)
                .map_err(|_| format!("{}: source is not UTF-8", file.display()))?;
            let mut parser = Parser::new();
            parser
                .set_language(&ts_language)
                .map_err(|error| format!("tree-sitter setup failed: {error}"))?;
            let tree = parser
                .parse(&bytes, None)
                .ok_or_else(|| format!("{}: tree-sitter returned no tree", file.display()))?;
            if tree.root_node().has_error() {
                return Err(format!("{}: syntax errors in parse tree", file.display()));
            }
            let mod_path = module_path(file, &source_root, language, source);
            let (imports, classes, referenced_types) = match language {
                Language::Python => extract_python(source, &tree, &mod_path, file),
                Language::Java => extract_java(source, &tree, file),
                Language::Go => extract_go(source, &tree, &mod_path, file),
            };
            Ok(FileResult {
                file_path: file.clone(),
                mod_path,
                imports,
                classes,
                referenced_types,
            })
        })
        .collect();

    let mut warnings = Vec::new();
    let mut file_results = Vec::new();
    for result in parsed {
        match result {
            Ok(file) => file_results.push(file),
            Err(warning) => {
                if warnings.len() < 20 {
                    warnings.push(warning);
                }
            }
        }
    }
    if file_results.is_empty() {
        return Err(ScanError::NoParsedFiles {
            language,
            discovered: discovered_files,
        });
    }

    let mut internal_nodes = HashSet::new();
    let mut node_files: HashMap<String, Vec<PathBuf>> = HashMap::new();
    let mut classes = HashMap::new();
    let mut class_modules = HashMap::new();
    for result in &file_results {
        internal_nodes.insert(result.mod_path.clone());
        node_files
            .entry(result.mod_path.clone())
            .or_default()
            .push(result.file_path.clone());
        for class in &result.classes {
            class_modules.insert(class.qualified_name.clone(), result.mod_path.clone());
            classes.insert(class.qualified_name.clone(), class.clone());
        }
    }

    let mut aliases: HashMap<String, String> = internal_nodes
        .iter()
        .cloned()
        .map(|node| (node.clone(), node))
        .collect();
    if language == Language::Java {
        aliases.extend(class_modules);
    }
    if let Some(module) = &go_module {
        for node in &internal_nodes {
            let import_path = if node == "." {
                module.clone()
            } else {
                format!("{module}/{node}")
            };
            aliases.insert(import_path, node.clone());
        }
    }

    let mut graph = DiGraph::new();
    let mut node_index = HashMap::new();
    let mut sorted_internal: Vec<String> = internal_nodes.iter().cloned().collect();
    sorted_internal.sort();
    for node in &sorted_internal {
        add_node(&mut graph, &mut node_index, node.clone());
    }

    let mut external_targets = BTreeSet::new();
    for result in &file_results {
        let source_index = node_index[&result.mod_path];
        let mut imports = result.imports.clone();
        if language == Language::Java {
            let package = result
                .mod_path
                .rsplit_once('.')
                .map(|(package, _)| package)
                .unwrap_or("");
            for type_name in &result.referenced_types {
                if !package.is_empty() {
                    imports.push(ImportRef::Exact(format!("{package}.{type_name}")));
                }
            }
        }
        for import in &imports {
            for (target, internal) in resolve_import(import, &aliases, &internal_nodes, language) {
                if target == result.mod_path {
                    continue;
                }
                if !internal {
                    external_targets.insert(target.clone());
                }
                let target_index = add_node(&mut graph, &mut node_index, target);
                if !graph.contains_edge(source_index, target_index) {
                    graph.add_edge(source_index, target_index, ());
                }
            }
        }
    }

    let mut internal_graph = DiGraph::new();
    let mut internal_index = HashMap::new();
    for node in &sorted_internal {
        let index = internal_graph.add_node(node.clone());
        internal_index.insert(node.clone(), index);
    }
    for edge in graph.edge_indices() {
        let Some((source, target)) = graph.edge_endpoints(edge) else {
            continue;
        };
        let source_name = &graph[source];
        let target_name = &graph[target];
        if let (Some(&internal_source), Some(&internal_target)) = (
            internal_index.get(source_name),
            internal_index.get(target_name),
        ) {
            if !internal_graph.contains_edge(internal_source, internal_target) {
                internal_graph.add_edge(internal_source, internal_target, ());
            }
        }
    }

    let parsed_files = file_results.len();
    if internal_graph.node_count() < 50 {
        warnings.push(format!(
            "only {} internal nodes were measured; cross-repository AGQ discrimination is weak below 50",
            internal_graph.node_count()
        ));
    }
    if language == Language::Go {
        warnings.push(
            "Go cohesion is unavailable; AGQ weights are renormalized over measurable components"
                .to_string(),
        );
        if go_module.is_none() {
            warnings
                .push("go.mod was not found; local package imports may not resolve".to_string());
        }
    }

    Ok(ScanResult {
        graph,
        internal_graph,
        node_index,
        node_files,
        classes,
        files: file_results
            .into_iter()
            .map(|result| result.file_path)
            .collect(),
        language,
        internal_nodes,
        diagnostics: ScanDiagnostics {
            discovered_files,
            parsed_files,
            skipped_files: discovered_files.saturating_sub(parsed_files),
            external_imports: external_targets.len(),
            warnings,
        },
    })
}
