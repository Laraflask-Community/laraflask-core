"""ContextualBindingBuilder for the IoC Container."""

from __future__ import annotations
from typing import Any, Optional

from laraflask.core.container.binding_resolution_exception import BindingResolutionException


class ContextualBindingBuilder:
    """
    [ID] Fluent builder untuk contextual binding, dipakai lewat `Container.when()`.
    Memungkinkan sintaks: `container.when(Concrete).needs(Abstract).give(Implementation)`.

    [EN] Fluent builder for contextual bindings, used via `Container.when()`.
    Enables the syntax: `container.when(Concrete).needs(Abstract).give(Implementation)`.
    """

    def __init__(self, container: 'Container', concrete_key: str):
        self._container = container
        self._concrete_key = concrete_key
        self._abstract: Optional[Any] = None

    def needs(self, abstract: Any) -> 'ContextualBindingBuilder':
        """Specify which abstract/interface this contextual binding applies to."""
        self._abstract = abstract
        return self

    def give(self, implementation: Any) -> 'Container':
        """Provide the concrete implementation/value and register the binding. Returns the Container."""
        if self._abstract is None:
            raise BindingResolutionException(
                "ContextualBindingBuilder.give() called before .needs(); "
                "use container.when(X).needs(Y).give(Z)."
            )
        return self._container.add_contextual_binding(self._concrete_key, self._abstract, implementation)
