"""Tests for laraflask.core.container.Container and related classes."""

import pytest

from laraflask.core.container.container import Container
from laraflask.core.container.binding_resolution_exception import BindingResolutionException
from laraflask.core.container.contextual_binding_builder import ContextualBindingBuilder


class TestContainerBinding:
    """Test basic binding operations: bind, singleton, transient, instance."""

    def test_bind_and_resolve_class(self):
        container = Container()

        class Greeter:
            def greet(self):
                return "hello"

        container.bind("greeter", Greeter)
        result = container.make("greeter")
        assert result.greet() == "hello"

    def test_bind_callable_factory(self):
        container = Container()
        container.bind("value", lambda c: 42)
        assert container.make("value") == 42

    def test_singleton_returns_same_instance(self):
        container = Container()

        class Service:
            pass

        container.singleton("svc", Service)
        a = container.make("svc")
        b = container.make("svc")
        assert a is b

    def test_transient_returns_different_instances(self):
        container = Container()

        class Service:
            pass

        container.transient("svc", Service)
        a = container.make("svc")
        b = container.make("svc")
        assert a is not b

    def test_instance_registration(self):
        container = Container()
        obj = {"key": "value"}
        container.instance("config", obj)
        assert container.make("config") is obj

    def test_bound_check(self):
        container = Container()
        container.bind("foo", lambda c: "bar")
        assert container.bound("foo") is True
        assert container.bound("missing") is False

    def test_resolved_check(self):
        container = Container()
        container.bind("svc", lambda c: "instance")
        assert container.resolved("svc") is False
        container.make("svc")
        assert container.resolved("svc") is True

    def test_flush_clears_all(self):
        container = Container()
        container.singleton("x", lambda c: 1)
        container.make("x")
        container.flush()
        assert container.bound("x") is False


class TestContainerAlias:
    """Test alias resolution."""

    def test_alias_resolves(self):
        container = Container()
        container.bind("original", lambda c: "hello")
        container.alias("original", "shortcut")
        assert container.make("shortcut") == "hello"


class TestContainerContextualBinding:
    """Test contextual binding (when/needs/give)."""

    def test_contextual_binding(self):
        container = Container()

        class Logger:
            def __init__(self):
                self.name = "default"

        class FileLogger:
            def __init__(self):
                self.name = "file"

        class ReportController:
            def __init__(self, logger: Logger):
                self.logger = logger

        container.bind(Logger, Logger)
        container.bind(ReportController, ReportController)
        container.when(ReportController).needs(Logger).give(FileLogger)

        result = container.make(ReportController)
        assert result.logger.name == "file"

    def test_contextual_binding_builder_give_without_needs_raises(self):
        container = Container()
        builder = ContextualBindingBuilder(container, "some_key")
        with pytest.raises(BindingResolutionException):
            builder.give("something")


class TestContainerTagging:
    """Test tagging and tagged resolution."""

    def test_tag_and_resolve_tagged(self):
        container = Container()
        container.bind("report_a", lambda c: "A")
        container.bind("report_b", lambda c: "B")
        container.tag(["report_a", "report_b"], "reports")

        resolved = container.tagged("reports")
        assert resolved == ["A", "B"]

    def test_tagged_empty(self):
        container = Container()
        assert container.tagged("nonexistent") == []

    def test_tag_single_abstract(self):
        container = Container()
        container.bind("x", lambda c: "X")
        container.tag("x", "single")
        assert container.tagged("single") == ["X"]


class TestContainerScoped:
    """Test scoped bindings."""

    def test_scoped_returns_same_within_scope(self):
        container = Container()

        class Request:
            pass

        container.scoped("req", Request)
        a = container.make("req")
        b = container.make("req")
        assert a is b

    def test_scoped_flush_resets(self):
        container = Container()

        class Request:
            pass

        container.scoped("req", Request)
        a = container.make("req")
        container.flush_scoped()
        b = container.make("req")
        assert a is not b


class TestContainerCall:
    """Test the call() method for dependency injection into callables."""

    def test_call_closure(self):
        container = Container()

        def add(a=1, b=2):
            return a + b

        result = container.call(add, {"a": 10, "b": 20})
        assert result == 30

    def test_call_with_defaults(self):
        container = Container()

        def greet(name="world"):
            return f"hello {name}"

        result = container.call(greet)
        assert result == "hello world"


class TestContainerDunderMethods:
    """Test __getitem__, __setitem__, __contains__."""

    def test_getitem(self):
        container = Container()
        container.bind("key", lambda c: "value")
        assert container["key"] == "value"

    def test_setitem(self):
        container = Container()
        container["key"] = lambda c: "value"
        assert container.make("key") == "value"

    def test_contains(self):
        container = Container()
        container.bind("key", lambda c: "value")
        assert "key" in container
        assert "missing" not in container


class TestBindingResolutionException:
    """Test BindingResolutionException behavior."""

    def test_raises_for_unbound_abstract(self):
        container = Container()
        with pytest.raises(BindingResolutionException):
            container.make("nonexistent.module.Class")

    def test_exception_message(self):
        container = Container()
        with pytest.raises(BindingResolutionException, match="not instantiable"):
            container.make("totally.fake.Thing")
