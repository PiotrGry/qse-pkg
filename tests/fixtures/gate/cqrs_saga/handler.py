"""Command handler emits events through the event bus."""

from .event_bus import publish


def execute(command):
    kind, payload = command
    publish(f"{kind}d")
