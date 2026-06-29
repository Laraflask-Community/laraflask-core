"""EventSubscriber - Subscribe to multiple events in one class."""

from __future__ import annotations


class EventSubscriber:
    """
    Allows subscribing to multiple events in one class.
    Override subscribe() to register multiple listeners.
    """

    def subscribe(self, events: 'EventDispatcher') -> None:
        raise NotImplementedError
