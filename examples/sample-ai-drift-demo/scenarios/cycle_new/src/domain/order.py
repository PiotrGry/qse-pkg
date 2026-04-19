"""CYCLE_NEW overlay: domain.order now depends on application.order_service,
while order_service already depends on domain.order. This closes a ring that
did not exist in the base graph — a classic AI-generated drift."""

from dataclasses import dataclass

from src.application.order_service import OrderService  # BAD: domain -> application


@dataclass(frozen=True)
class Order:
    id: str
    customer_id: str
    total_cents: int

    def validate(self) -> None:
        if self.total_cents < 0:
            raise ValueError("total_cents must be non-negative")

    @staticmethod
    def service_reference() -> type:
        # "Convenient" backref — the exact pattern that silently introduces cycles.
        return OrderService
