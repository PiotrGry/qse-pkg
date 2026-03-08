/// Universal tree-sitter based scanner for Python, Java, Go, TypeScript.
///
/// Produces a dependency graph + class metadata from source files,
/// regardless of language. Same output format for all languages —
/// AGQ metrics are computed identically.
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use petgraph::graph::DiGraph;
use petgraph::graph::NodeIndex;
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
    /// Import dependency graph: nodes = module paths, edges = imports
    pub graph: DiGraph<String, ()>,
    /// Node indices keyed by module path
    pub node_index: HashMap<String, NodeIndex>,
    /// Class metadata keyed by class name
    pub classes: HashMap<String, ClassInfo>,
    /// All scanned file paths
    pub files: Vec<PathBuf>,
    /// Language detected
    pub language: Language,
}

// ---------------------------------------------------------------------------
// Language detection
// ---------------------------------------------------------------------------

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

    if py == 0 && java == 0 && go == 0 {
        return None;
    }
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
    let rel = file.strip_prefix(base).unwrap_or(file);
    let s = rel.to_string_lossy().replace(std::path::MAIN_SEPARATOR, ".");
    // Strip extension
    let s = match lang {
        Language::Python => s.trim_end_matches(".py").to_string(),
        Language::Java   => s.trim_end_matches(".java").to_string(),
        Language::Go     => s.trim_end_matches(".go").to_string(),
    };
    // Strip __init__ suffix for Python
    if s.ends_with(".__init__") {
        s[..s.len() - 9].to_string()
    } else {
        s
    }
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
            // Skip hidden dirs and common non-source dirs
            let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
            if name.starts_with('.') || matches!(name, "node_modules" | "target" | "__pycache__" | ".git") {
                continue;
            }
            collect_recursive(&path, ext, out);
        } else if path.extension().and_then(|e| e.to_str()) == Some(ext) {
            // Skip __init__.py for Python (mostly re-exports, inflate graph)
            if ext == "py" && path.file_name().and_then(|n| n.to_str()) == Some("__init__.py") {
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
    &source[node.start_byte()..node.end_byte()]
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

pub fn scan_repo(base_dir: &str) -> ScanResult {
    let base = Path::new(base_dir);
    let lang = detect_language(base).unwrap_or(Language::Python);
    let ext = file_extension(&lang);
    let ts_lang = ts_language(&lang);

    let files = collect_files(base, ext);

    let mut graph: DiGraph<String, ()> = DiGraph::new();
    let mut node_index: HashMap<String, NodeIndex> = HashMap::new();
    let mut classes: HashMap<String, ClassInfo> = HashMap::new();

    // Helper: get or create node
    let get_node = |g: &mut DiGraph<String, ()>,
                        idx: &mut HashMap<String, NodeIndex>,
                        name: String| -> NodeIndex {
        if let Some(&ni) = idx.get(&name) {
            ni
        } else {
            let ni = g.add_node(name.clone());
            idx.insert(name, ni);
            ni
        }
    };

    let mut parser = Parser::new();
    parser.set_language(&ts_lang).expect("Failed to set language");

    let mut scanned_files = Vec::new();

    for file_path in &files {
        let Ok(source) = std::fs::read(file_path) else { continue };

        let Some(tree) = parser.parse(&source, None) else { continue };

        let mod_path = module_path(file_path, base, &lang);
        let src_node = get_node(&mut graph, &mut node_index, mod_path.clone());

        let (imports, file_classes) = match lang {
            Language::Python => extract_python(&source, &tree, file_path, base),
            Language::Java   => extract_java(&source, &tree, file_path, base),
            Language::Go     => extract_go(&source, &tree, file_path, base),
        };

        for imp in imports {
            let tgt_node = get_node(&mut graph, &mut node_index, imp);
            if src_node != tgt_node && !graph.contains_edge(src_node, tgt_node) {
                graph.add_edge(src_node, tgt_node, ());
            }
        }

        for cls in file_classes {
            classes.insert(cls.name.clone(), cls);
        }

        scanned_files.push(file_path.clone());
    }

    ScanResult {
        graph,
        node_index,
        classes,
        files: scanned_files,
        language: lang,
    }
}
