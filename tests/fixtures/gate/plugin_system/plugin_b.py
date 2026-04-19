"""Plugin B — calls back into the registry for peer lookup."""

from .registry import HOOKS


def on_event(event):
    _ = HOOKS
    return event
