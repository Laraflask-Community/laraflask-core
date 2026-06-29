"""CacheServiceProvider."""

from laraflask.core.providers.service_provider import ServiceProvider


class CacheServiceProvider(ServiceProvider):
    """Register cache services."""

    def register(self):
        self.app.singleton('cache', self._make_cache)

    def boot(self):
        from laraflask.cache.cache import Cache
        driver = self.app._config.get('cache.default', 'file') if self.app._config else 'file'
        prefix = self.app._config.get('cache.prefix', '') if self.app._config else ''
        Cache.configure(default=driver, prefix=prefix)

    def _make_cache(self, app):
        from laraflask.cache.cache import Cache
        return Cache
