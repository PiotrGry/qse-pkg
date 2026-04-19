"""Public payments API — the ONLY caller allowed into `payments_core`."""

from src.infrastructure.payments_core import charge


def pay(customer_id: str, amount_cents: int) -> str:
    return charge(customer_id, amount_cents)
