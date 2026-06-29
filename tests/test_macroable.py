"""Tests for laraflask.core.macroable.Macroable mixin."""

import pytest

from laraflask.core.macroable import Macroable


class TestMacroRegistration:
    """Test macro registration and invocation."""

    def setup_method(self):
        """Clean up macros between tests to prevent cross-contamination."""

        class Fresh(Macroable):
            pass

        self.FreshClass = Fresh

    def test_register_and_call_macro(self):
        cls = self.FreshClass

        cls.macro("greet", lambda self: "hello")
        instance = cls()
        assert instance.greet() == "hello"

    def test_macro_receives_self(self):
        cls = self.FreshClass
        cls.value = 42
        cls.macro("get_value", lambda self: self.value)
        instance = cls()
        instance.value = 99
        assert instance.get_value() == 99

    def test_macro_with_arguments(self):
        cls = self.FreshClass
        cls.macro("add", lambda self, a, b: a + b)
        instance = cls()
        assert instance.add(3, 4) == 7

    def test_has_macro(self):
        cls = self.FreshClass
        assert cls.has_macro("nonexistent") is False
        cls.macro("exists", lambda self: True)
        assert cls.has_macro("exists") is True

    def test_flush_macros(self):
        cls = self.FreshClass
        cls.macro("temporary", lambda self: "temp")
        assert cls.has_macro("temporary") is True
        cls.flush_macros()
        assert cls.has_macro("temporary") is False


class TestMacroIsolation:
    """Test that macros are isolated between subclasses."""

    def test_macros_do_not_leak_between_classes(self):
        class ClassA(Macroable):
            pass

        class ClassB(Macroable):
            pass

        ClassA.macro("only_a", lambda self: "A")

        assert ClassA.has_macro("only_a") is True
        assert ClassB.has_macro("only_a") is False

    def test_subclass_has_own_registry(self):
        class Parent(Macroable):
            pass

        class Child(Parent):
            pass

        Parent.macro("parent_method", lambda self: "parent")
        Child.macro("child_method", lambda self: "child")

        assert Parent.has_macro("parent_method") is True
        assert Parent.has_macro("child_method") is False
        assert Child.has_macro("child_method") is True

    def test_flush_on_one_does_not_affect_other(self):
        class A(Macroable):
            pass

        class B(Macroable):
            pass

        A.macro("x", lambda self: 1)
        B.macro("y", lambda self: 2)
        A.flush_macros()

        assert A.has_macro("x") is False
        assert B.has_macro("y") is True
        B.flush_macros()


class TestMixin:
    """Test the mixin() method for bulk macro registration."""

    def test_mixin_registers_all_public_methods(self):
        class Extension:
            def double(self, val):
                return val * 2

            def triple(self, val):
                return val * 3

        class Target(Macroable):
            pass

        Target.mixin(Extension)

        instance = Target()
        assert instance.double(5) == 10
        assert instance.triple(5) == 15
        Target.flush_macros()

    def test_mixin_skips_private_methods(self):
        class Extension:
            def _private(self):
                return "hidden"

            def public(self):
                return "visible"

        class Target(Macroable):
            pass

        Target.mixin(Extension)
        assert Target.has_macro("public") is True
        assert Target.has_macro("_private") is False
        Target.flush_macros()

    def test_mixin_replace_false_does_not_overwrite(self):
        class Extension:
            def method(self):
                return "new"

        class Target(Macroable):
            pass

        Target.macro("method", lambda self: "original")
        Target.mixin(Extension, replace=False)

        instance = Target()
        assert instance.method() == "original"
        Target.flush_macros()
