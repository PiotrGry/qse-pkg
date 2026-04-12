# Acyclicity

Acyclicity means the project avoids circular dependencies.

A circular dependency happens when part A depends on part B, and part B eventually depends back on part A.

Those loops can make a system harder to change and reason about.

QSE detects such loops using [[Tarjan SCC]].
