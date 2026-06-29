"""Tests for laraflask.events - EventDispatcher, Event, Listener, EventSubscriber."""

import pytest

from laraflask.events.event import Event
from laraflask.events.listener import Listener
from laraflask.events.event_subscriber import EventSubscriber
from laraflask.events.event_dispatcher import EventDispatcher


class TestEvent:
    """Test the base Event class."""

    def test_event_name_is_class_name(self):
        event = Event()
        assert event.name == "Event"

    def test_custom_event_name(self):
        class UserCreated(Event):
            pass

        e = UserCreated()
        assert e.name == "UserCreated"

    def test_event_stores_data(self):
        e = Event(user_id=42, action="login")
        assert e.user_id == 42
        assert e.action == "login"

    def test_broadcast_on_default(self):
        e = Event()
        assert e.broadcast_on() == []

    def test_broadcast_as_default(self):
        e = Event()
        assert e.broadcast_as() == "Event"


class TestListener:
    """Test the base Listener class."""

    def test_handle_raises_not_implemented(self):
        listener = Listener()
        with pytest.raises(NotImplementedError):
            listener.handle(Event())

    def test_should_queue_default_false(self):
        assert Listener().should_queue() is False

    def test_queue_default(self):
        assert Listener().queue() == "default"


class TestEventDispatcher:
    """Test EventDispatcher listen/dispatch/forget lifecycle."""

    def setup_method(self):
        self.dispatcher = EventDispatcher()

    def test_listen_and_dispatch_with_string_event(self):
        results = []
        self.dispatcher.listen("user.created", lambda e: results.append("handled"))
        self.dispatcher.dispatch("user.created")
        assert results == ["handled"]

    def test_listen_and_dispatch_with_event_class(self):
        class OrderPlaced(Event):
            pass

        results = []
        self.dispatcher.listen("OrderPlaced", lambda e: results.append("order"))
        self.dispatcher.dispatch(OrderPlaced())
        assert results == ["order"]

    def test_multiple_listeners(self):
        results = []
        self.dispatcher.listen("event", lambda e: results.append("A"))
        self.dispatcher.listen("event", lambda e: results.append("B"))
        self.dispatcher.dispatch("event")
        assert results == ["A", "B"]

    def test_dispatch_returns_responses(self):
        self.dispatcher.listen("calc", lambda e: 42)
        responses = self.dispatcher.dispatch("calc")
        assert 42 in responses

    def test_has_listeners(self):
        assert self.dispatcher.has_listeners("event") is False
        self.dispatcher.listen("event", lambda e: None)
        assert self.dispatcher.has_listeners("event") is True

    def test_forget_removes_listeners(self):
        self.dispatcher.listen("event", lambda e: None)
        self.dispatcher.forget("event")
        assert self.dispatcher.has_listeners("event") is False

    def test_forget_all(self):
        self.dispatcher.listen("a", lambda e: None)
        self.dispatcher.listen("b", lambda e: None)
        self.dispatcher.forget_all()
        assert self.dispatcher.has_listeners("a") is False
        assert self.dispatcher.has_listeners("b") is False

    def test_dispatch_event_instance(self):
        class PaymentReceived(Event):
            pass

        results = []
        self.dispatcher.listen("PaymentReceived", lambda e: results.append(e.name))
        self.dispatcher.dispatch(PaymentReceived())
        assert results == ["PaymentReceived"]

    def test_fire_is_alias_for_dispatch(self):
        results = []
        self.dispatcher.listen("test", lambda e: results.append("fired"))
        self.dispatcher.fire("test")
        assert results == ["fired"]


class TestEventDispatcherWildcard:
    """Test wildcard listener patterns."""

    def setup_method(self):
        self.dispatcher = EventDispatcher()

    def test_wildcard_listener(self):
        results = []
        self.dispatcher.listen("user.*", lambda e: results.append("wildcard"))
        self.dispatcher.dispatch("user.created")
        assert results == ["wildcard"]

    def test_wildcard_matches_multiple(self):
        results = []
        self.dispatcher.listen("order.*", lambda e: results.append("order"))
        self.dispatcher.dispatch("order.placed")
        self.dispatcher.dispatch("order.shipped")
        assert results == ["order", "order"]

    def test_wildcard_does_not_match_unrelated(self):
        results = []
        self.dispatcher.listen("user.*", lambda e: results.append("user"))
        self.dispatcher.dispatch("order.placed")
        assert results == []


class TestEventSubscriber:
    """Test EventSubscriber registration."""

    def test_subscribe_raises_not_implemented(self):
        subscriber = EventSubscriber()
        with pytest.raises(NotImplementedError):
            subscriber.subscribe(EventDispatcher())

    def test_custom_subscriber(self):
        class MySubscriber(EventSubscriber):
            def subscribe(self, events):
                events.listen("my.event", lambda e: "subscribed")

        dispatcher = EventDispatcher()
        dispatcher.subscribe(MySubscriber)
        assert dispatcher.has_listeners("my.event") is True


class TestEventDispatcherHalt:
    """Test dispatch with halt=True."""

    def test_halt_stops_on_false(self):
        dispatcher = EventDispatcher()
        results = []
        dispatcher.listen("event", lambda e: False)
        dispatcher.listen("event", lambda e: results.append("second"))
        dispatcher.dispatch("event", halt=True)
        # Second listener should not execute when halt=True and first returns False
        assert results == []

    def test_until_returns_first_response(self):
        dispatcher = EventDispatcher()
        dispatcher.listen("event", lambda e: "first")
        dispatcher.listen("event", lambda e: "second")
        result = dispatcher.until("event")
        assert result == "first"


class TestEventDispatcherWithListenerClass:
    """Test dispatching with Listener class instances."""

    def test_listener_class_handle(self):
        class MyListener(Listener):
            def handle(self, event):
                return "handled"

        dispatcher = EventDispatcher()
        dispatcher.listen("test", MyListener())
        responses = dispatcher.dispatch("test")
        assert "handled" in responses
