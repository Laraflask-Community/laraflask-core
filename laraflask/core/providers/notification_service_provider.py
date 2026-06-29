"""NotificationServiceProvider."""

from laraflask.core.providers.service_provider import ServiceProvider


class NotificationServiceProvider(ServiceProvider):
    """Register notification services."""

    def register(self):
        self.app.singleton('notification', self._make_notification)

    def _make_notification(self, app):
        from laraflask.notifications.notification import NotificationSender
        return NotificationSender()
