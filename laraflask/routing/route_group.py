"""RouteGroup - Represents a group of routes sharing common attributes."""

from __future__ import annotations
from typing import Dict


class RouteGroup:
    """Represents a group of routes sharing common attributes."""

    def __init__(self, router: 'Router', attributes: Dict):
        self._router = router
        self._attributes = attributes
        self._previous_group = None

    def __enter__(self):
        self._previous_group = self._router._current_group.copy()
        self._router._current_group.update(self._attributes)
        return self

    def __exit__(self, *args):
        self._router._current_group = self._previous_group
