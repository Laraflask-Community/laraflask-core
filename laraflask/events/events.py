"""Events - Facade for the global event dispatcher."""

from __future__ import annotations
from typing import Any, List, Optional

from laraflask.events.event_dispatcher import EventDispatcher


class Events:
    """Facade for the global event dispatcher."""

    _dispatcher: Optional[EventDispatcher] = None

    @classmethod
    def get_dispatcher(cls) -> EventDispatcher:
        if cls._dispatcher is None:
            cls._dispatcher = EventDispatcher()
        return cls._dispatcher

    @classmethod
    def listen(cls, event: Any, listener: Any) -> None:
        cls.get_dispatcher().listen(event, listener)

    @classmethod
    def dispatch(cls, event: Any, payload: Any = None) -> List:
        return cls.get_dispatcher().dispatch(event, payload)

    @classmethod
    def fire(cls, event: Any, payload: Any = None) -> List:
        return cls.dispatch(event, payload)

    @classmethod
    def subscribe(cls, subscriber: Any) -> None:
        cls.get_dispatcher().subscribe(subscriber)

    @classmethod
    def forget(cls, event: Any) -> None:
        cls.get_dispatcher().forget(event)

    @classmethod
    def has_listeners(cls, event: Any) -> bool:
        return cls.get_dispatcher().has_listeners(event)
