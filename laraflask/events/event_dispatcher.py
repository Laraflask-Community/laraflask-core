"""EventDispatcher - The Laraflask Event Dispatcher."""

from __future__ import annotations
import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union

from laraflask.events.event import Event
from laraflask.events.listener import Listener

logger = logging.getLogger('laraflask.events')


class EventDispatcher:
    """
    The Laraflask Event Dispatcher.
    Fires events and notifies listeners synchronously or queued.
    """

    def __init__(self):
        self._listeners: Dict[str, List] = {}
        self._wildcards: Dict[str, List] = {}
        self._queued: List = []
        self._firing: List[str] = []

    # --- Registration ---

    def listen(self, event: Union[str, Type], listener: Any) -> 'EventDispatcher':
        """Register a listener for an event."""
        event_name = self._get_event_name(event)

        if '*' in event_name:
            self._wildcards.setdefault(event_name, []).append(listener)
        else:
            self._listeners.setdefault(event_name, []).append(listener)

        return self

    def subscribe(self, subscriber: Any) -> 'EventDispatcher':
        """Register an event subscriber."""
        if isinstance(subscriber, type):
            subscriber = subscriber()
        subscriber.subscribe(self)
        return self

    def has_listeners(self, event: Union[str, Type]) -> bool:
        event_name = self._get_event_name(event)
        return event_name in self._listeners and bool(self._listeners[event_name])

    def forget(self, event: Union[str, Type]) -> 'EventDispatcher':
        event_name = self._get_event_name(event)
        self._listeners.pop(event_name, None)
        return self

    def forget_all(self) -> 'EventDispatcher':
        self._listeners.clear()
        self._wildcards.clear()
        return self

    # --- Dispatching ---

    def dispatch(self, event: Union[Event, str, Type],
                 payload: Any = None, halt: bool = False) -> List:
        """Fire an event and notify all listeners."""
        if isinstance(event, str):
            event_name = event
            event_instance = None
        elif isinstance(event, type):
            event_instance = event() if payload is None else event(**payload if isinstance(payload, dict) else {})
            event_name = event_instance.name
        else:
            event_instance = event
            event_name = event.name

        if event_name in self._firing:
            logger.debug(f"Event [{event_name}] is already firing, skipping re-dispatch")

        self._firing.append(event_name)
        responses = []

        try:
            listeners = self._get_listeners(event_name)
            for listener in listeners:
                response = self._call_listener(listener, event_instance or payload)

                if halt and response is False:
                    return responses

                if response is not None:
                    responses.append(response)
        finally:
            self._firing.remove(event_name)

        return responses

    def fire(self, event: Any, payload: Any = None, halt: bool = False) -> List:
        """Alias for dispatch()."""
        return self.dispatch(event, payload, halt)

    def dispatch_now(self, event: Any, payload: Any = None) -> List:
        """Dispatch event immediately (same as dispatch but explicit)."""
        return self.dispatch(event, payload)

    def until(self, event: Any, payload: Any = None) -> Optional[Any]:
        """Fire event until a listener returns a non-null value."""
        results = self.dispatch(event, payload, halt=True)
        return results[0] if results else None

    async def dispatch_async(self, event: Any, payload: Any = None) -> List:
        """Dispatch event asynchronously."""
        responses = []
        event_name = self._get_event_name(event)
        listeners = self._get_listeners(event_name)

        tasks = []
        for listener in listeners:
            if asyncio.iscoroutinefunction(self._resolve_listener(listener)):
                tasks.append(self._call_listener_async(listener, event))
            else:
                responses.append(self._call_listener(listener, event))

        if tasks:
            async_responses = await asyncio.gather(*tasks, return_exceptions=True)
            responses.extend(async_responses)

        return responses

    # --- Helpers ---

    def _get_listeners(self, event_name: str) -> List:
        """Get all listeners for an event, including wildcards."""
        listeners = list(self._listeners.get(event_name, []))

        for pattern, wild_listeners in self._wildcards.items():
            import fnmatch
            if fnmatch.fnmatch(event_name, pattern):
                listeners.extend(wild_listeners)

        return listeners

    def _call_listener(self, listener: Any, event: Any) -> Any:
        """Invoke a single listener."""
        resolved = self._resolve_listener(listener)

        if isinstance(resolved, Listener):
            if resolved.should_queue():
                self._queue_listener(resolved, event)
                return None
            return resolved.handle(event)
        elif callable(resolved):
            sig = inspect.signature(resolved)
            if len(sig.parameters) == 0:
                return resolved()
            return resolved(event)
        return None

    async def _call_listener_async(self, listener: Any, event: Any) -> Any:
        resolved = self._resolve_listener(listener)
        if asyncio.iscoroutinefunction(resolved):
            return await resolved(event)
        return self._call_listener(listener, event)

    def _resolve_listener(self, listener: Any) -> Any:
        """Resolve a listener to its callable form."""
        if isinstance(listener, type):
            try:
                from laraflask.core.application import Application
                return listener()
            except Exception:
                return listener()
        return listener

    def _queue_listener(self, listener: Listener, event: Any) -> None:
        """Queue a listener for async execution."""
        try:
            from laraflask.queue.queue import Queue
            Queue.push({
                'type': 'event_listener',
                'listener': f"{listener.__class__.__module__}.{listener.__class__.__name__}",
                'event': event,
            }, queue=listener.queue())
        except Exception as e:
            logger.error(f"Failed to queue listener: {e}")

    def _get_event_name(self, event: Any) -> str:
        if isinstance(event, str):
            return event
        if isinstance(event, type):
            return event.__name__
        return type(event).__name__

    def make_listener(self, listener: Any) -> Callable:
        """Create a closure that wraps a listener."""
        def wrapper(event):
            return self._call_listener(listener, event)
        return wrapper
