"""ApiVersionRouter - Route API requests to versioned controllers."""

from __future__ import annotations
from typing import Any, Dict


class ApiVersionRouter:
    """
    Route API requests to versioned controllers.
    Registers /api/v1, /api/v2 route prefixes.
    """

    def __init__(self, router: Any):
        self._router = router
        self._versions: Dict[str, callable] = {}

    def version(self, version: str, callback: callable) -> 'ApiVersionRouter':
        self._versions[version] = callback
        with self._router.group({'prefix': f'/api/{version}', 'middleware': ['api']}):
            callback()
        return self

    def v1(self, callback: callable) -> 'ApiVersionRouter':
        return self.version('v1', callback)

    def v2(self, callback: callable) -> 'ApiVersionRouter':
        return self.version('v2', callback)

    def deprecate(self, version: str, sunset_date: str) -> 'ApiVersionRouter':
        """Mark an API version as deprecated."""
        original_callback = self._versions.get(version)
        if original_callback:
            def add_deprecation_header(*args, **kwargs):
                response = original_callback(*args, **kwargs)
                if hasattr(response, 'headers'):
                    response.headers['Deprecation'] = 'true'
                    response.headers['Sunset'] = sunset_date
                return response
            self._versions[version] = add_deprecation_header
        return self
