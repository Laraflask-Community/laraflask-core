"""EventServiceProvider."""

from laraflask.core.providers.service_provider import ServiceProvider


class EventServiceProvider(ServiceProvider):
    """Register event and listener services."""

    def register(self):
        self.app.singleton('events', self._make_dispatcher)

    def boot(self):
        from laraflask.events.dispatcher import Events
        self._register_listeners(Events)

    def _make_dispatcher(self, app):
        from laraflask.events.dispatcher import Events
        return Events

    def _register_listeners(self, Events):
        """Register event listeners. Override in app/Providers/EventServiceProvider.py"""
        pass
