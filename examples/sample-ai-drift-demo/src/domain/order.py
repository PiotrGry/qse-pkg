"""Order value object — pure domain, no infrastructure dependencies."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    id: str
    customer_id: str
    total_cents: int

    def validate(self) -> None:
        if self.total_cents < 0:
            raise ValueError("total_cents must be non-negative")
