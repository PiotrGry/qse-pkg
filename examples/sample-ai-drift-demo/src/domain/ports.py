"""Ports — abstract interfaces the application depends on."""

from typing import Protocol

from .order import Order


class OrderRepository(Protocol):
    def save(self, order: Order) -> None: ...
    def get(self, order_id: str) -> Order: ...


class Notifier(Protocol):
    def send(self, customer_id: str, message: str) -> None: ...
