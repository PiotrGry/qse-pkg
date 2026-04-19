"""Order service — orchestrates domain + ports. No infra imports."""

from src.domain.order import Order
from src.domain.ports import Notifier, OrderRepository


class OrderService:
    def __init__(self, repo: OrderRepository, notifier: Notifier):
        self._repo = repo
        self._notifier = notifier

    def place(self, order: Order) -> None:
        order.validate()
        self._repo.save(order)
        self._notifier.send(order.customer_id, f"Order {order.id} placed.")
