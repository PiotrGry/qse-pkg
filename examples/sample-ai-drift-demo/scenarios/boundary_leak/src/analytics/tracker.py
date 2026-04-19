"""BOUNDARY_LEAK overlay: `analytics.tracker` reaches into `payments_core`
directly to read raw charge IDs. Per qse-gate.toml, only `payments_api.*`
is authorized — this import leaks protected logic to an un-whitelisted caller."""

from src.infrastructure.payments_core import charge  # BAD: leaks protected module


def track_purchase(customer_id: str, amount_cents: int) -> str:
    # The agent will "helpfully" bypass the API to call the core directly.
    # That's exactly the drift a firewall must catch.
    return charge(customer_id, amount_cents)
