"""Base ServiceProvider class."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from laraflask.core.application import Application


class ServiceProvider:
    """Base class for all service providers."""

    def __init__(self, app: 'Application'):
        self.app = app

    def register(self) -> None:
        """Register bindings into the container."""
        pass

    def boot(self) -> None:
        """Bootstrap any application services."""
        pass

    def provides(self) -> list:
        """Get the services provided by the provider."""
        return []

    def when(self) -> list:
        """Get the events that trigger deferred loading."""
        return []
