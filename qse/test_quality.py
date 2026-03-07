"""
QSE_test — metryka jakości testów.

Mierzy 5 wymiarów jakości zestawu testów:
1. assertion_density   — średnia liczba asercji per test
2. test_to_code_ratio  — stosunek LOC testów do LOC kodu produkcyjnego
3. naming_quality      — % testów z opisową nazwą (test_should_*, test_when_*, itp.)
4. isolation_score     — % testów bez zewnętrznych zależności (mock/patch/fixture)
5. coverage_potential  — proxy: % klas domenowych które mają co najmniej 1 test

QSE_test = mean(powyższych 5 metryk) ∈ [0, 1]

Walidacja: 6 testów jednostkowych, zaimplementowane i przechodzące.
"""

import ast
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set


# Descriptive test name patterns (beyond just "test_something")
_DESCRIPTIVE_PATTERNS = re.compile(
    r"test_(should|when|given|if|that|returns|raises|handles|with|without|"
    r"can|cannot|does|does_not|will|wont|is|is_not|has|has_no)_",
    re.IGNORECASE,
)

# Isolation markers: if a test uses these, it's isolated (no real external deps)
_ISOLATION_MARKERS = {
    "mock", "patch", "fixture", "mocker", "monkeypatch",
    "Mock", "MagicMock", "AsyncMock", "patch",
}

# Assertion calls commonly used in pytest / unittest
_ASSERTION_NAMES = {
    "assert",          # bare assert statement
    "assertEqual", "assertNotEqual", "assertTrue", "assertFalse",
    "assertIn", "assertNotIn", "assertIsNone", "assertIsNotNone",
    "assertRaises", "assertAlmostEqual",
    "assert_called", "assert_called_once", "assert_called_with",
    "assert_called_once_with", "assert_any_call", "assert_not_called",
}


@dataclass
class TestFileInfo:
    """Metadata about a single test file."""
    file_path: str
    test_functions: List[str] = field(default_factory=list)
    assertion_counts: List[int] = field(default_factory=list)   # per test function
    uses_isolation: List[bool] = field(default_factory=list)     # per test function
    tested_classes: Set[str] = field(default_factory=set)        # domain class names referenced


def _count_assertions(func_node: ast.FunctionDef) -> int:
    """Count assertion statements/calls in a test function."""
    count = 0
    for node in ast.walk(func_node):
        if isinstance(node, ast.Assert):
            count += 1
        elif isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in _ASSERTION_NAMES:
                count += 1
    return count


def _uses_isolation(func_node: ast.FunctionDef) -> bool:
    """Check if test uses mocking/patching (isolation markers)."""
    # Check decorators
    for dec in func_node.decorator_list:
        if isinstance(dec, ast.Call):
            func = dec.func
            name = getattr(func, "id", "") or getattr(func, "attr", "")
        elif isinstance(dec, ast.Name):
            name = dec.id
        elif isinstance(dec, ast.Attribute):
            name = dec.attr
        else:
            name = ""
        if name in _ISOLATION_MARKERS:
            return True

    # Check function arguments (fixtures)
    for arg in func_node.args.args:
        if arg.arg in {m.lower() for m in _ISOLATION_MARKERS}:
            return True

    # Check body for patch() calls
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "id", "") or getattr(func, "attr", "")
            if name in _ISOLATION_MARKERS:
                return True
    return False


def _referenced_classes(tree: ast.AST, domain_classes: Set[str]) -> Set[str]:
    """Find which domain classes are referenced in this file."""
    refs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in domain_classes:
            refs.add(node.id)
        elif isinstance(node, ast.Attribute) and node.attr in domain_classes:
            refs.add(node.attr)
    return refs


def _count_lines(file_path: str) -> int:
    """Count non-empty, non-comment lines."""
    try:
        with open(file_path) as f:
            return sum(
                1 for line in f
                if line.strip() and not line.strip().startswith("#")
            )
    except OSError:
        return 0


def _scan_test_file(file_path: str,
                    domain_classes: Set[str]) -> TestFileInfo:
    """Parse a test file and extract quality metadata."""
    info = TestFileInfo(file_path=file_path)
    try:
        with open(file_path) as f:
            source = f.read()
        tree = ast.parse(source, filename=file_path)
    except (SyntaxError, OSError):
        return info

    info.tested_classes = _referenced_classes(tree, domain_classes)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        info.test_functions.append(node.name)
        info.assertion_counts.append(_count_assertions(node))
        info.uses_isolation.append(_uses_isolation(node))

    return info


def _collect_domain_classes(base_dir: str,
                           target_dirs: List[str] = None) -> Set[str]:
    """Collect all class names defined in target directories.

    target_dirs: list of directory names to scan (default: ["domain"]).
    """
    if target_dirs is None:
        target_dirs = ["domain"]
    classes = set()
    for dirname in target_dirs:
        target_dir = os.path.join(base_dir, dirname)
        if not os.path.isdir(target_dir):
            continue
        for root, _dirs, files in os.walk(target_dir):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath) as f:
                        tree = ast.parse(f.read(), filename=fpath)
                except (SyntaxError, OSError):
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        classes.add(node.name)
    return classes


def _collect_test_files(base_dir: str) -> List[str]:
    """Find all test_*.py files under base_dir."""
    result = []
    for root, _dirs, files in os.walk(base_dir):
        for fname in files:
            if fname.startswith("test_") and fname.endswith(".py"):
                result.append(os.path.join(root, fname))
    return result


def _collect_production_files(base_dir: str) -> List[str]:
    """Find all non-test .py files."""
    result = []
    for root, _dirs, files in os.walk(base_dir):
        for fname in files:
            if fname.endswith(".py") and not fname.startswith("test_"):
                result.append(os.path.join(root, fname))
    return result


def compute_test_quality(base_dir: str,
                         target_dirs: List[str] = None) -> Dict[str, float]:
    """
    Compute QSE_test metrics for a repository.

    target_dirs: list of directory names containing entity classes
                 (default: ["domain"]).

    Returns dict with keys:
        assertion_density, test_to_code_ratio, naming_quality,
        isolation_score, coverage_potential, qse_test
    """
    domain_classes = _collect_domain_classes(base_dir, target_dirs=target_dirs)
    test_files = _collect_test_files(base_dir)
    prod_files = _collect_production_files(base_dir)

    if not test_files:
        return {
            "assertion_density": 0.0,
            "test_to_code_ratio": 0.0,
            "naming_quality": 0.0,
            "isolation_score": 0.0,
            "coverage_potential": 0.0,
            "qse_test": 0.0,
            "n_test_files": 0,
            "n_test_functions": 0,
        }

    infos = [_scan_test_file(fp, domain_classes) for fp in test_files]

    all_tests = [name for info in infos for name in info.test_functions]
    all_assertions = [c for info in infos for c in info.assertion_counts]
    all_isolation = [v for info in infos for v in info.uses_isolation]
    tested_classes = set().union(*[info.tested_classes for info in infos])

    n_tests = len(all_tests)

    # 1. Assertion density: avg assertions per test, capped at 1.0 for ≥3
    if n_tests > 0:
        avg_assertions = sum(all_assertions) / n_tests
        assertion_density = min(avg_assertions / 3.0, 1.0)
    else:
        assertion_density = 0.0

    # 2. Test-to-code ratio: LOC(tests) / LOC(production), capped at 1.0
    test_loc = sum(_count_lines(fp) for fp in test_files)
    prod_loc = sum(_count_lines(fp) for fp in prod_files)
    test_to_code_ratio = min(test_loc / max(prod_loc, 1), 1.0)

    # 3. Naming quality: % tests with descriptive names
    if n_tests > 0:
        descriptive = sum(1 for name in all_tests if _DESCRIPTIVE_PATTERNS.search(name))
        naming_quality = descriptive / n_tests
    else:
        naming_quality = 0.0

    # 4. Isolation score: % tests using mocks/fixtures
    if n_tests > 0:
        isolation_score = sum(all_isolation) / n_tests
    else:
        isolation_score = 0.0

    # 5. Coverage potential: % domain classes with at least 1 test referencing them
    if domain_classes:
        coverage_potential = len(tested_classes & domain_classes) / len(domain_classes)
    else:
        coverage_potential = 1.0  # no domain classes = no uncovered classes

    qse_test = (
        assertion_density
        + test_to_code_ratio
        + naming_quality
        + isolation_score
        + coverage_potential
    ) / 5.0

    return {
        "assertion_density": round(assertion_density, 4),
        "test_to_code_ratio": round(test_to_code_ratio, 4),
        "naming_quality": round(naming_quality, 4),
        "isolation_score": round(isolation_score, 4),
        "coverage_potential": round(coverage_potential, 4),
        "qse_test": round(qse_test, 4),
        "n_test_files": len(test_files),
        "n_test_functions": n_tests,
    }
