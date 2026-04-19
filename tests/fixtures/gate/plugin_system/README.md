# Counterexample: Plugin System

A registry and its plugins mutually reference each other: the registry exposes
hooks that plugins call, while the registry iterates plugins to dispatch. This
is the "host ↔ extension" shape found in VSCode, pytest, setuptools, etc.

Gate expectation: `mode="delta"` with base==head → 0 new cycles.
