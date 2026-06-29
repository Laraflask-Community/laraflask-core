"""QueueServiceProvider."""

from laraflask.core.providers.service_provider import ServiceProvider


class QueueServiceProvider(ServiceProvider):
    """Register queue services."""

    def register(self):
        self.app.singleton('queue', self._make_queue)

    def boot(self):
        import os
        from laraflask.queue.queue import Queue
        Queue.configure(default=os.getenv('QUEUE_CONNECTION', 'sync'))

    def _make_queue(self, app):
        from laraflask.queue.queue import Queue
        return Queue
