"""
Laraflask WebSocket & Real-time Support
Built on Flask-SocketIO with room, channel, and broadcasting support.
"""

from __future__ import annotations
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger('laraflask.ws')


class Channel:
    """Represents a broadcast channel."""

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name


class PrivateChannel(Channel):
    """Private channel — requires authentication."""

    def __init__(self, name: str):
        super().__init__(f"private-{name}")


class PresenceChannel(Channel):
    """Presence channel — tracks connected users."""

    def __init__(self, name: str):
        super().__init__(f"presence-{name}")


class BroadcastEvent:
    """
    Base class for broadcastable events.
    Implement broadcast_on() and optionally broadcast_with() on your events.
    """

    def broadcast_on(self) -> List[Channel]:
        """Define channels to broadcast on."""
        return []

    def broadcast_as(self) -> str:
        """Define the event name."""
        return type(self).__name__

    def broadcast_with(self) -> Dict:
        """Define the data to broadcast."""
        data = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                data[key] = value
        return data

    def broadcast_when(self) -> bool:
        """Only broadcast if this returns True."""
        return True


class WebSocketManager:
    """
    Manages WebSocket connections and broadcasting.
    Wraps Flask-SocketIO for a Laravel-like Pusher/Echo API.
    """

    def __init__(self):
        self._socketio = None
        self._handlers: Dict[str, List[Callable]] = {}
        self._rooms: Dict[str, set] = {}
        self._connected_users: Dict[str, Any] = {}

    def init_app(self, flask_app, **kwargs):
        """Initialize with Flask app."""
        try:
            from flask_socketio import SocketIO
            self._socketio = SocketIO(
                flask_app,
                cors_allowed_origins='*',
                async_mode=kwargs.get('async_mode', 'eventlet'),
                logger=kwargs.get('logger', False),
                engineio_logger=kwargs.get('engineio_logger', False),
                **{k: v for k, v in kwargs.items()
                   if k not in ('async_mode', 'logger', 'engineio_logger')},
            )
            self._register_core_events()
            logger.info("WebSocket initialized with Flask-SocketIO")
        except ImportError:
            logger.warning(
                "Flask-SocketIO not installed. "
                "Run: pip install flask-socketio eventlet"
            )

    def _register_core_events(self):
        """Register built-in socket events."""
        if not self._socketio:
            return

        @self._socketio.on('connect')
        def on_connect():
            from flask_socketio import request as ws_request
            sid = ws_request.sid
            logger.debug(f"Client connected: {sid}")
            self._connected_users[sid] = None
            if 'connect' in self._handlers:
                for handler in self._handlers['connect']:
                    handler(sid)

        @self._socketio.on('disconnect')
        def on_disconnect():
            from flask_socketio import request as ws_request
            sid = ws_request.sid
            logger.debug(f"Client disconnected: {sid}")
            self._connected_users.pop(sid, None)
            if 'disconnect' in self._handlers:
                for handler in self._handlers['disconnect']:
                    handler(sid)

        @self._socketio.on('subscribe')
        def on_subscribe(data):
            channel = data.get('channel', '')
            from flask_socketio import join_room, request as ws_request
            join_room(channel)
            self._rooms.setdefault(channel, set()).add(ws_request.sid)
            logger.debug(f"Client {ws_request.sid} subscribed to [{channel}]")

        @self._socketio.on('unsubscribe')
        def on_unsubscribe(data):
            channel = data.get('channel', '')
            from flask_socketio import leave_room, request as ws_request
            leave_room(channel)
            if channel in self._rooms:
                self._rooms[channel].discard(ws_request.sid)

    def on(self, event: str) -> Callable:
        """Decorator to register an event handler."""
        def decorator(func: Callable) -> Callable:
            self._handlers.setdefault(event, []).append(func)
            if self._socketio:
                self._socketio.on(event)(func)
            return func
        return decorator

    def emit(self, event: str, data: Any = None,
             room: str = None, namespace: str = '/') -> None:
        """Emit an event to connected clients."""
        if not self._socketio:
            return
        self._socketio.emit(event, data, room=room, namespace=namespace)

    def broadcast(self, event_instance: BroadcastEvent) -> None:
        """Broadcast an event to all its channels."""
        if not event_instance.broadcast_when():
            return

        channels = event_instance.broadcast_on()
        event_name = event_instance.broadcast_as()
        data = event_instance.broadcast_with()

        for channel in channels:
            self.emit(event_name, data, room=channel.name)
            logger.debug(f"Broadcast [{event_name}] → [{channel.name}]")

    def to(self, room: str) -> 'BroadcastTo':
        """Send to a specific room."""
        return BroadcastTo(self, room)

    def join_room(self, room: str, sid: str = None) -> None:
        if self._socketio:
            from flask_socketio import join_room
            join_room(room, sid=sid)

    def leave_room(self, room: str, sid: str = None) -> None:
        if self._socketio:
            from flask_socketio import leave_room
            leave_room(room, sid=sid)

    def run(self, app, host: str = '0.0.0.0', port: int = 8000, **kwargs) -> None:
        if self._socketio:
            self._socketio.run(app, host=host, port=port, **kwargs)

    def clients_in_room(self, room: str) -> set:
        return self._rooms.get(room, set())

    def connected_count(self) -> int:
        return len(self._connected_users)


class BroadcastTo:
    """Fluent interface for targeted broadcasts."""

    def __init__(self, ws: WebSocketManager, room: str):
        self._ws = ws
        self._room = room

    def emit(self, event: str, data: Any = None) -> None:
        self._ws.emit(event, data, room=self._room)


class SSEManager:
    """
    Server-Sent Events (SSE) manager.
    One-way server → client streaming without WebSocket.
    """

    def __init__(self):
        self._subscribers: Dict[str, List] = {}

    def stream(self, channel: str = 'default'):
        """Flask route handler for SSE endpoint."""
        import queue

        def generate():
            q = queue.Queue()
            self._subscribers.setdefault(channel, []).append(q)
            try:
                yield "data: connected\n\n"
                while True:
                    try:
                        data = q.get(timeout=30)
                        if data is None:
                            break
                        yield f"data: {data}\n\n"
                    except queue.Empty:
                        yield ": heartbeat\n\n"
            finally:
                self._subscribers[channel].remove(q)

        from flask import Response, stream_with_context
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            },
        )

    def publish(self, channel: str, data: str, event: str = None) -> int:
        """Publish data to all SSE subscribers on a channel."""
        import json
        payload = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
        message = f"event: {event}\ndata: {payload}" if event else f"data: {payload}"

        count = 0
        for q in self._subscribers.get(channel, []):
            try:
                q.put_nowait(message)
                count += 1
            except Exception:
                pass
        return count

    def subscribers(self, channel: str) -> int:
        return len(self._subscribers.get(channel, []))

    def disconnect_all(self, channel: str) -> None:
        for q in self._subscribers.get(channel, []):
            q.put_nowait(None)
        self._subscribers[channel] = []


# ─── Global instances ─────────────────────────────────────────────────────────

WebSocket = WebSocketManager()
SSE = SSEManager()


# ─── Broadcast Facade ─────────────────────────────────────────────────────────

class Broadcast:
    """
    Facade for broadcasting events.

    Usage:
        Broadcast.event(OrderShipped(order))
        Broadcast.on('orders').emit('new_order', order.to_dict())
    """

    _ws: WebSocketManager = WebSocket

    @classmethod
    def event(cls, event: BroadcastEvent) -> None:
        cls._ws.broadcast(event)

    @classmethod
    def on(cls, room: str) -> BroadcastTo:
        return cls._ws.to(room)

    @classmethod
    def emit(cls, event: str, data: Any = None, room: str = None) -> None:
        cls._ws.emit(event, data, room=room)

    @classmethod
    def to(cls, room: str) -> BroadcastTo:
        return cls._ws.to(room)

    @classmethod
    def init_app(cls, flask_app, **kwargs) -> None:
        cls._ws.init_app(flask_app, **kwargs)
