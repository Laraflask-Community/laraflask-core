"""AuthServiceProvider."""

from laraflask.core.providers.service_provider import ServiceProvider


class AuthServiceProvider(ServiceProvider):
    """Register authentication services."""

    def register(self):
        self.app.singleton('auth', self._make_auth)
        self.app.singleton('gate', self._make_gate)

    def boot(self):
        from laraflask.auth.auth import Auth, Gate
        Auth.configure(
            guards={
                'web': {'driver': 'session', 'provider': 'users'},
                'api': {'driver': 'jwt', 'provider': 'users'},
            },
            default='web',
        )

        # Register Gate abilities
        self._define_abilities(Gate)

    def _make_auth(self, app):
        from laraflask.auth.auth import Auth
        return Auth

    def _make_gate(self, app):
        from laraflask.auth.auth import Gate
        return Gate

    def _define_abilities(self, Gate):
        """Register application abilities. Override in app/Providers/AuthServiceProvider.py"""
        pass
