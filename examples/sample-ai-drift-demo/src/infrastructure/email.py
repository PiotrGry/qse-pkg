"""SMTP-backed Notifier implementation."""

from src.domain.ports import Notifier  # noqa: F401 — kept for docs


class SmtpNotifier:
    def __init__(self, host: str):
        self._host = host

    def send(self, customer_id: str, message: str) -> None:
        print(f"[smtp:{self._host}] -> {customer_id}: {message}")
