# Counterexample: Event Bus

Legitimate cycle: `publisher` → `bus` → `subscriber` → `publisher`.

The subscriber loops back to publisher through typed events. In any pub/sub
system this ring exists by design and must NOT be flagged as drift when the
cycle was already present in the base graph.

Gate expectation (Sprint 0 Δ mode):
- `mode="any"`   → flagged (documents the pattern)
- `mode="delta"` with base==head → 0 new cycles (ring is not new)
