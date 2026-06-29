"""StorageServiceProvider."""

from laraflask.core.providers.service_provider import ServiceProvider


class StorageServiceProvider(ServiceProvider):
    """Register storage services."""

    def register(self):
        self.app.singleton('storage', self._make_storage)

    def boot(self):
        import os
        from laraflask.storage.storage import Storage
        Storage.configure(default=os.getenv('FILESYSTEM_DISK', 'local'))

        # Register public storage symlink route
        flask_app = self.app._flask
        storage_path = self.app.storage_path('app', 'public')
        public_path = self.app.public_path('storage')

        if not os.path.exists(public_path) and os.path.exists(storage_path):
            try:
                os.symlink(storage_path, public_path)
            except Exception:
                pass

    def _make_storage(self, app):
        from laraflask.storage.storage import Storage
        return Storage
