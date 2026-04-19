"""LAYER_VIOLATION overlay: domain.order directly imports from infrastructure.
This is the most common AI-generated drift — the agent sees 'we already have
a DB helper' and calls it from the domain to 'save a line'."""

from dataclasses import dataclass

from src.infrastructure.db import PostgresOrderRepository  # BAD: domain -> infrastructure


@dataclass(frozen=True)
class Order:
    id: str
    customer_id: str
    total_cents: int

    def validate(self) -> None:
        if self.total_cents < 0:
            raise ValueError("total_cents must be non-negative")

    def save_directly(self, dsn: str) -> None:
        # "Helpful" convenience method that drags infra into the domain layer.
        PostgresOrderRepository(dsn).save(self)
