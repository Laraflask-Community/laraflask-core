"""ValidationServiceProvider."""

from laraflask.core.providers.service_provider import ServiceProvider


class ValidationServiceProvider(ServiceProvider):
    """Register validation services."""

    def register(self):
        self.app.singleton('validator', self._make_validator)

    def _make_validator(self, app):
        from laraflask.validation.validator import Validator
        return Validator
