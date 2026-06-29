"""Listener - Base class for event listeners."""

from __future__ import annotations
from laraflask.events.event import Event


class Listener:
    """Base class for event listeners."""

    def handle(self, event: Event) -> None:
        raise NotImplementedError

    def should_queue(self) -> bool:
        return False

    def queue(self) -> str:
        return 'default'
