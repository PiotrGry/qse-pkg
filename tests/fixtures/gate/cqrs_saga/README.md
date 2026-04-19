# Counterexample: CQRS Saga

Saga orchestrates command → handler → event → saga (reply loop). The ring
`saga` → `command_bus` → `handler` → `event_bus` → `saga` is intentional.

Gate expectation: `mode="delta"` with base==head → 0 new cycles.
