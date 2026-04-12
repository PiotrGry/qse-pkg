---
type: explainer
audience: beginner
---

# How QSE Works Simply

QSE scans a software project and builds a map of its internal structure. That map is called a [[Dependency Graph]].

Then it measures a few important qualities:

- [[Modularity]]: are parts nicely separated?
- [[Acyclicity]]: do parts avoid circular dependencies?
- [[Stability]]: do important parts stay dependable?
- [[Cohesion]]: do things inside one package belong together?
- [[CD]]: is the graph too densely connected?
- [[flatscore]]: in Python, is the project too flat and spaghetti-like?

These signals are combined into one final score using an [[AGQ Formula]].
