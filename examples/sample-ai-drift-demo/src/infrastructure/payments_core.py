"""Protected payments core. Only `src.payments_api.*` is allowed to import this.

Enforced by BOUNDARY_LEAK in qse-gate.toml.
"""


def charge(customer_id: str, amount_cents: int) -> str:
    return f"charge-{customer_id}-{amount_cents}"
