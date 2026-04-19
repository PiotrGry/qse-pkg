"""Event bus core. Decouples producers from consumers."""

from .subscriber import handle


def publish(event):
    handle(event)
