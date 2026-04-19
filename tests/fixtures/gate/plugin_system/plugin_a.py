"""Plugin A — calls back into the registry to query peers."""

from .registry import HOOKS


def on_event(event):
    if event == "ping":
        for h in HOOKS:
            if h is not on_event:
                h("pong")
