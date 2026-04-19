"""Command dispatcher."""

from .handler import execute


def send(command):
    execute(command)
