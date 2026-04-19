"""Postgres-backed OrderRepository implementation."""

from src.domain.order import Order
from src.domain.ports import OrderRepository


class PostgresOrderRepository:
    """Implements `OrderRepository` Protocol by duck typing."""

    def __init__(self, dsn: str):
        self._dsn = dsn

    def save(self, order: Order) -> None:
        # Imagine a real `psycopg.execute(...)` here.
        print(f"[db:{self._dsn}] saved order {order.id}")

    def get(self, order_id: str) -> Order:
        return Order(id=order_id, customer_id="c-1", total_cents=0)
