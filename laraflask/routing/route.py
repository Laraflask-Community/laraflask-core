"""Route - Represents a single registered route."""

from __future__ import annotations
from typing import Any, List, Optional


class Route:
    """Represents a single registered route."""

    def __init__(self, methods: List[str], uri: str, action: Any, name: str = None):
        self.methods = methods
        self.uri = uri
        self.action = action
        self._name = name
        self._middleware: List[str] = []
        self._prefix = ''
        self._domain = None

    def name(self, name: str) -> 'Route':
        """Assign a name to the route."""
        self._name = name
        return self

    def middleware(self, *middleware: str) -> 'Route':
        """Assign middleware to the route."""
        self._middleware.extend(middleware)
        return self

    def prefix(self, prefix: str) -> 'Route':
        self._prefix = prefix
        return self

    def domain(self, domain: str) -> 'Route':
        self._domain = domain
        return self

    def get_name(self) -> Optional[str]:
        return self._name

    def get_middleware(self) -> List[str]:
        return self._middleware
