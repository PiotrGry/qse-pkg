"""Event bus — delivers events back to the saga, closing the loop."""

from .saga import on_event


def publish(event):
    on_event(event)
