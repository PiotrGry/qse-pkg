"""
Dynamic tracing via sys.settrace.

Instruments a target module's execution to discover runtime type
information and actual call edges not visible in static analysis.
"""

import ast
import importlib
import os
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple

import networkx as nx


@dataclass
class TraceResult:
    """Edges discovered by dynamic tracing."""
    dynamic_edges: List[Tuple[str, str]] = field(default_factory=list)
    runtime_types: Dict[str, Set[str]] = field(default_factory=dict)
    call_count: int = 0


class DynamicTracer:
    """
    Instruments Python execution using sys.settrace to discover:
    1. Actual call edges (caller_module → callee_module)
    2. Runtime types of attribute accesses

    Usage:
        tracer = DynamicTracer(base_dir)
        tracer.start()
        # ... execute target code ...
        tracer.stop()
        result = tracer.get_result()
    """

    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)
        self._edges: Set[Tuple[str, str]] = set()
        self._types: Dict[str, Set[str]] = {}
        self._call_count = 0
        self._lock = threading.Lock()
        self._old_trace = None

    def _module_from_filename(self, filename: str) -> str:
        """Convert absolute filename to dotted module path relative to base_dir."""
        if not filename:
            return ""
        try:
            rel = os.path.relpath(filename, self.base_dir)
        except ValueError:
            return ""
        if rel.startswith(".."):
            return ""
        return rel.replace(os.sep, ".").removesuffix(".py")

    def _trace_func(self, frame, event, arg):
        """Trace callback registered with sys.settrace."""
        filename = frame.f_code.co_filename
        if not filename or not os.path.isabs(filename):
            return self._trace_func

        mod = self._module_from_filename(filename)
        if not mod:
            return self._trace_func

        if event == "call":
            with self._lock:
                self._call_count += 1
                # Record caller → callee edge
                caller_frame = frame.f_back
                if caller_frame:
                    caller_file = caller_frame.f_code.co_filename
                    caller_mod = self._module_from_filename(caller_file)
                    if caller_mod and caller_mod != mod:
                        self._edges.add((caller_mod, mod))

        elif event == "line":
            # Inspect locals for runtime type discovery
            try:
                local_vars = frame.f_locals
                for var_name, var_val in local_vars.items():
                    if var_val is not None and not var_name.startswith("_"):
                        type_name = type(var_val).__name__
                        key = f"{mod}.{var_name}"
                        with self._lock:
                            if key not in self._types:
                                self._types[key] = set()
                            self._types[key].add(type_name)
            except Exception:
                pass

        return self._trace_func

    def start(self):
        """Begin tracing."""
        self._old_trace = sys.gettrace()
        sys.settrace(self._trace_func)

    def stop(self):
        """Stop tracing and restore previous trace function."""
        sys.settrace(self._old_trace)

    def get_result(self) -> TraceResult:
        """Return collected trace data."""
        return TraceResult(
            dynamic_edges=list(self._edges),
            runtime_types={k: set(v) for k, v in self._types.items()},
            call_count=self._call_count,
        )


def trace_repo(base_dir: str) -> TraceResult:
    """
    Perform a dynamic trace of a repository.

    Strategy:
    1. Auto-discover and run test files (test_*.py, *_test.py) under trace.
    2. Fallback: import all .py modules to trigger top-level code.
    """
    import subprocess
    import glob as globmod

    tracer = DynamicTracer(base_dir)
    abs_base = os.path.abspath(base_dir)

    if abs_base not in sys.path:
        sys.path.insert(0, abs_base)

    # Discover test files
    test_files = []
    for pattern in ["**/test_*.py", "**/*_test.py"]:
        test_files.extend(globmod.glob(os.path.join(abs_base, pattern), recursive=True))

    # Snapshot modules before import
    pre_modules = set(sys.modules.keys())

    tracer.start()
    try:
        if test_files:
            # Run tests under trace via import
            for tf in sorted(set(test_files)):
                rel = os.path.relpath(tf, abs_base)
                mod_name = rel.replace(os.sep, ".").removesuffix(".py")
                try:
                    importlib.import_module(mod_name)
                except Exception:
                    pass
        else:
            # Fallback: import all modules to trigger top-level code
            for root, _dirs, files in os.walk(abs_base):
                for fname in sorted(files):
                    if not fname.endswith(".py") or fname == "__init__.py":
                        continue
                    fpath = os.path.join(root, fname)
                    rel = os.path.relpath(fpath, abs_base)
                    mod_name = rel.replace(os.sep, ".").removesuffix(".py")
                    try:
                        importlib.import_module(mod_name)
                    except Exception:
                        pass
    finally:
        tracer.stop()
        # Clean up sys.path
        if abs_base in sys.path:
            sys.path.remove(abs_base)
        # Clean up imported modules
        new_modules = set(sys.modules.keys()) - pre_modules
        for k in new_modules:
            try:
                del sys.modules[k]
            except KeyError:
                pass

    return tracer.get_result()


def trace_synthetic_execution(base_dir: str) -> TraceResult:
    """
    Legacy: trace synthetic repo. Kept for backward compatibility with run_poc.py.
    Delegates to trace_repo.
    """
    return trace_repo(base_dir)
