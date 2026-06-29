"""
Laraflask IoC Container
Powerful dependency injection with singleton, scoped, and transient lifetimes.
"""

from __future__ import annotations
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from laraflask.core.container.binding_resolution_exception import BindingResolutionException
from laraflask.core.container.contextual_binding_builder import ContextualBindingBuilder

T = TypeVar('T')


class Container:
    """
    The Laraflask Inversion of Control Container.

    Manages class dependencies and performs dependency injection.
    Supports singleton, scoped, and transient bindings.
    """

    def __init__(self):
        self._bindings: Dict[str, Dict] = {}
        self._instances: Dict[str, Any] = {}
        self._aliases: Dict[str, str] = {}
        self._resolved: Dict[str, bool] = {}
        self._scoped_instances: Dict[str, Any] = {}
        self._contextual: Dict[str, Dict[str, Any]] = {}
        self._tags: Dict[str, List[str]] = {}
        self._build_stack: List[str] = []

    # --- Binding ---

    def bind(self, abstract: Any, concrete: Any = None, shared: bool = False) -> 'Container':
        """Register a binding in the container."""
        key = self._get_key(abstract)
        if concrete is None:
            concrete = abstract

        self._bindings[key] = {
            'concrete': concrete,
            'shared': shared,
        }
        # Clear cached instance if re-binding
        self._instances.pop(key, None)
        return self

    def singleton(self, abstract: Any, concrete: Any = None) -> 'Container':
        """Register a shared binding (singleton) in the container."""
        return self.bind(abstract, concrete, shared=True)

    def scoped(self, abstract: Any, concrete: Any = None) -> 'Container':
        """Register a scoped binding (per-request singleton)."""
        key = self._get_key(abstract)
        self._bindings[key] = {
            'concrete': concrete or abstract,
            'shared': False,
            'scoped': True,
        }
        return self

    def transient(self, abstract: Any, concrete: Any = None) -> 'Container':
        """Register a transient binding (new instance every time)."""
        return self.bind(abstract, concrete, shared=False)

    def instance(self, abstract: Any, instance: Any) -> Any:
        """Register an existing instance as a singleton."""
        key = self._get_key(abstract)
        self._instances[key] = instance
        return instance

    def alias(self, abstract: Any, alias: str) -> 'Container':
        """Alias a type to a different name."""
        self._aliases[alias] = self._get_key(abstract)
        return self

    # --- Contextual Binding ---

    def when(self, concrete: Any) -> 'ContextualBindingBuilder':
        """
        Begin a contextual binding definition.
        Example: `container.when(ReportController).needs(Logger).give(FileLogger)`.
        """
        return ContextualBindingBuilder(self, self._get_key(concrete))

    def add_contextual_binding(self, concrete_key: str, abstract: Any, implementation: Any) -> 'Container':
        """Register a resolved contextual binding (used internally by ContextualBindingBuilder)."""
        abstract_key = self._get_key(abstract)
        self._contextual.setdefault(concrete_key, {})[abstract_key] = implementation
        return self

    def get_contextual_concrete(self, building_key: str, abstract_key: str) -> Optional[Any]:
        """Look up a contextual override for `abstract_key` while building `building_key`."""
        return self._contextual.get(building_key, {}).get(abstract_key)

    # --- Tagging ---

    def tag(self, abstracts: Any, *tags: str) -> 'Container':
        """Tag one or more bindings at once so they can be resolved together via `tagged()`."""
        if not isinstance(abstracts, (list, tuple)):
            abstracts = [abstracts]

        for tag in tags:
            keys = self._tags.setdefault(tag, [])
            for abstract in abstracts:
                key = self._get_key(abstract)
                if key not in keys:
                    keys.append(key)

        return self

    def tagged(self, tag: str) -> List[Any]:
        """Resolve and return every instance registered under the given tag."""
        return [self.make(key) for key in self._tags.get(tag, [])]

    # --- Resolution ---

    def make(self, abstract: Any, parameters: Dict = None) -> Any:
        """Resolve the given type from the container."""
        key = self._get_key(abstract)

        # Check aliases
        if key in self._aliases:
            key = self._aliases[key]

        # Check cached singletons
        if key in self._instances:
            return self._instances[key]

        # Check scoped instances
        if key in self._scoped_instances:
            return self._scoped_instances[key]

        concrete = self._get_concrete(key)
        instance = self._build(concrete, parameters or {})

        # Cache if singleton
        if self._is_shared(key):
            self._instances[key] = instance
        elif self._is_scoped(key):
            self._scoped_instances[key] = instance

        self._resolved[key] = True
        return instance

    def _get_concrete(self, key: str) -> Any:
        """Get the concrete type for a given abstract."""
        if key in self._bindings:
            return self._bindings[key]['concrete']

        # Try to import the class directly
        try:
            parts = key.rsplit('.', 1)
            if len(parts) == 2:
                module = __import__(parts[0], fromlist=[parts[1]])
                return getattr(module, parts[1])
        except (ImportError, AttributeError):
            pass

        raise BindingResolutionException(
            f"Target [{key}] is not instantiable. Are you sure you bound it?"
        )

    def _build(self, concrete: Any, parameters: Dict = {}) -> Any:
        """Build an instance of the given type."""
        if callable(concrete) and not inspect.isclass(concrete):
            return concrete(self)

        if not inspect.isclass(concrete):
            return concrete

        self._build_stack.append(self._get_key(concrete))
        try:
            constructor = concrete.__init__
            deps = self._resolve_dependencies(constructor, parameters)
            return concrete(*deps)
        except TypeError as e:
            raise BindingResolutionException(
                f"Unable to build [{concrete.__name__}]: {e}"
            )
        finally:
            self._build_stack.pop()

    def _resolve_dependencies(self, func: Callable, overrides: Dict = {}) -> list:
        """Resolve dependencies from a function's type hints."""
        sig = inspect.signature(func)
        deps = []
        building_key = self._build_stack[-1] if self._build_stack else None

        for name, param in sig.parameters.items():
            if name == 'self':
                continue

            if name in overrides:
                deps.append(overrides[name])
                continue

            annotation = param.annotation
            if annotation == inspect.Parameter.empty:
                if param.default != inspect.Parameter.empty:
                    deps.append(param.default)
                continue

            # Contextual binding takes priority over the regular binding table.
            if building_key is not None:
                contextual = self.get_contextual_concrete(building_key, self._get_key(annotation))
                if contextual is not None:
                    deps.append(self._build(contextual, {}) if inspect.isclass(contextual) else contextual)
                    continue

            try:
                deps.append(self.make(annotation))
            except BindingResolutionException:
                if param.default != inspect.Parameter.empty:
                    deps.append(param.default)

        return deps

    def _is_shared(self, key: str) -> bool:
        return self._bindings.get(key, {}).get('shared', False)

    def _is_scoped(self, key: str) -> bool:
        return self._bindings.get(key, {}).get('scoped', False)

    def _get_key(self, abstract: Any) -> str:
        """Get a string key for the abstract."""
        if isinstance(abstract, str):
            return abstract
        if inspect.isclass(abstract):
            return f"{abstract.__module__}.{abstract.__qualname__}"
        return str(abstract)

    def bound(self, abstract: Any) -> bool:
        """Determine if the given abstract type has been bound."""
        key = self._get_key(abstract)
        return key in self._bindings or key in self._instances

    def resolved(self, abstract: Any) -> bool:
        """Determine if the given abstract type has been resolved."""
        return self._get_key(abstract) in self._resolved

    def flush(self) -> None:
        """Flush all bindings and resolved instances."""
        self._bindings.clear()
        self._instances.clear()
        self._resolved.clear()

    def flush_scoped(self) -> None:
        """Flush scoped instances (call at end of each request)."""
        self._scoped_instances.clear()

    def call(self, callback: Callable, parameters: Dict = None) -> Any:
        """Call the given Closure/class@method and inject its dependencies."""
        parameters = parameters or {}

        if isinstance(callback, str) and '@' in callback:
            class_name, method = callback.split('@')
            instance = self.make(class_name)
            callback = getattr(instance, method)

        deps = self._resolve_dependencies(callback, parameters)
        return callback(*deps)

    def __getitem__(self, abstract: Any) -> Any:
        return self.make(abstract)

    def __setitem__(self, abstract: Any, concrete: Any) -> None:
        self.bind(abstract, concrete)

    def __contains__(self, abstract: Any) -> bool:
        return self.bound(abstract)
