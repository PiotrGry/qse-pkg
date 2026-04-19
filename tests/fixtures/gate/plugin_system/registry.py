"""Plugin registry — iterates plugins to dispatch hooks."""

from .plugin_a import on_event as a_on_event
from .plugin_b import on_event as b_on_event


HOOKS = [a_on_event, b_on_event]


def dispatch(event):
    for hook in HOOKS:
        hook(event)
