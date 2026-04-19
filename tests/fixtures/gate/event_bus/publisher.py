"""Publisher emits events through the bus."""

from .bus import publish


def emit(event):
    publish(event)
