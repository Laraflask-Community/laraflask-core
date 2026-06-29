"""SchedulerServiceProvider."""

from laraflask.core.providers.service_provider import ServiceProvider


class SchedulerServiceProvider(ServiceProvider):
    """Register the task scheduler."""

    def register(self):
        self.app.singleton('schedule', self._make_schedule)

    def _make_schedule(self, app):
        from laraflask.scheduler.schedule import Schedule
        return Schedule
