"""Subscriber handles events and may re-emit, closing the ring."""

from .publisher import emit


def handle(event):
    if getattr(event, "follow_up", None):
        emit(event.follow_up)
