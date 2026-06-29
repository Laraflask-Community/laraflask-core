"""Event - Base class for all Laraflask events."""

from __future__ import annotations
from typing import List


class Event:
    """Base class for all Laraflask events."""

    def __init__(self, **data):
        for key, value in data.items():
            setattr(self, key, value)

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def broadcast_on(self) -> List:
        """Define channels to broadcast on (for realtime events)."""
        return []

    def broadcast_as(self) -> str:
        """Define the broadcast event name."""
        return self.name
