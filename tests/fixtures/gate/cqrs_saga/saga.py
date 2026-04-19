"""Saga orchestrator."""

from .command_bus import send


def start(order_id):
    send(("reserve", order_id))


def on_event(event):
    if event == "reserved":
        send(("charge", event))
