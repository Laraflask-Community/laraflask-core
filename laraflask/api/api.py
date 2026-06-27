"""
Laraflask API Features
REST API resources, versioning, rate limiting, and response helpers.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Type, Union
from flask import jsonify, request, Response


# ─── API Response Helpers ─────────────────────────────────────────────────────

class ApiResponse:
    """Standardized JSON API response builder."""

    @staticmethod
    def success(data: Any = None, message: str = 'Success',
                status: int = 200, meta: Dict = None) -> Response:
        payload = {'success': True, 'message': message}
        if data is not None:
            payload['data'] = data
        if meta:
            payload['meta'] = meta
        return jsonify(payload), status

    @staticmethod
    def created(data: Any = None, message: str = 'Created') -> Response:
        return ApiResponse.success(data, message, 201)

    @staticmethod
    def error(message: str = 'Error', status: int = 400,
              errors: Dict = None, code: str = None) -> Response:
        payload = {'success': False, 'message': message}
        if errors:
            payload['errors'] = errors
        if code:
            payload['code'] = code
        return jsonify(payload), status

    @staticmethod
    def not_found(message: str = 'Resource not found') -> Response:
        return ApiResponse.error(message, 404)

    @staticmethod
    def unauthorized(message: str = 'Unauthenticated.') -> Response:
        return ApiResponse.error(message, 401)

    @staticmethod
    def forbidden(message: str = 'Forbidden.') -> Response:
        return ApiResponse.error(message, 403)

    @staticmethod
    def validation_error(errors: Dict, message: str = 'Validation failed') -> Response:
        return ApiResponse.error(message, 422, errors=errors)

    @staticmethod
    def server_error(message: str = 'Internal Server Error') -> Response:
        return ApiResponse.error(message, 500)

    @staticmethod
    def no_content() -> Response:
        return Response(status=204)

    @staticmethod
    def paginated(paginator: Dict, message: str = 'Success') -> Response:
        data = paginator.get('data', [])
        meta = {
            'total':        paginator.get('total', 0),
            'per_page':     paginator.get('per_page', 15),
            'current_page': paginator.get('current_page', 1),
            'last_page':    paginator.get('last_page', 1),
            'from':         paginator.get('from', 0),
            'to':           paginator.get('to', 0),
        }
        return ApiResponse.success(data, message, meta=meta)


# ─── API Resources ────────────────────────────────────────────────────────────

class ApiResource:
    """
    Transform a single model instance to JSON.
    Laravel-style API resource transformers.
    """

    def __init__(self, resource: Any):
        self._resource = resource
        self._additional: Dict = {}
        self._with_data: Dict = {}

    def to_array(self) -> Dict:
        """Override to define the resource's array representation."""
        if hasattr(self._resource, 'to_dict'):
            return self._resource.to_dict()
        return dict(self._resource) if hasattr(self._resource, '__iter__') else {}

    def with_(self, **kwargs) -> 'ApiResource':
        self._with_data.update(kwargs)
        return self

    def additional(self, **kwargs) -> 'ApiResource':
        self._additional.update(kwargs)
        return self

    def to_response(self) -> Response:
        data = self.to_array()
        payload = {'data': data}
        if self._with_data:
            payload.update(self._with_data)
        if self._additional:
            payload.update(self._additional)
        return jsonify(payload)

    def resolve(self) -> Dict:
        return self.to_array()

    @classmethod
    def make(cls, resource: Any) -> 'ApiResource':
        return cls(resource)

    @classmethod
    def collection(cls, resources: List) -> 'ApiResourceCollection':
        return ApiResourceCollection(resources, cls)

    def __call__(self) -> Response:
        return self.to_response()


class ApiResourceCollection:
    """Transform a collection of models."""

    def __init__(self, collection: List, resource_class: Type[ApiResource] = None):
        self._collection = collection
        self._resource_class = resource_class or ApiResource
        self._additional: Dict = {}
        self._pagination: Optional[Dict] = None

    def paginate(self, pagination_data: Dict) -> 'ApiResourceCollection':
        self._pagination = pagination_data
        self._collection = pagination_data.get('data', self._collection)
        return self

    def additional(self, **kwargs) -> 'ApiResourceCollection':
        self._additional.update(kwargs)
        return self

    def to_array(self) -> List[Dict]:
        return [self._resource_class(item).to_array() for item in self._collection]

    def to_response(self) -> Response:
        data = self.to_array()
        payload = {'data': data}

        if self._pagination:
            payload['meta'] = {
                'total':        self._pagination.get('total', len(data)),
                'per_page':     self._pagination.get('per_page', len(data)),
                'current_page': self._pagination.get('current_page', 1),
                'last_page':    self._pagination.get('last_page', 1),
            }
            payload['links'] = {
                'first': f"?page=1",
                'last':  f"?page={payload['meta']['last_page']}",
                'prev':  None,
                'next':  None,
            }

        if self._additional:
            payload.update(self._additional)

        return jsonify(payload)

    def __call__(self) -> Response:
        return self.to_response()


# ─── Base API Controller ──────────────────────────────────────────────────────

class ApiController:
    """
    Base controller for API endpoints.
    Provides helpers for common API patterns.
    """

    def respond(self, data: Any = None, message: str = 'Success',
                status: int = 200) -> Response:
        return ApiResponse.success(data, message, status)

    def created(self, data: Any = None, message: str = 'Created') -> Response:
        return ApiResponse.created(data, message)

    def no_content(self) -> Response:
        return ApiResponse.no_content()

    def error(self, message: str, status: int = 400,
              errors: Dict = None) -> Response:
        return ApiResponse.error(message, status, errors)

    def not_found(self, message: str = 'Resource not found') -> Response:
        return ApiResponse.not_found(message)

    def unauthorized(self) -> Response:
        return ApiResponse.unauthorized()

    def forbidden(self) -> Response:
        return ApiResponse.forbidden()

    def validation_error(self, errors: Dict) -> Response:
        return ApiResponse.validation_error(errors)

    def paginate(self, query_builder, per_page: int = 15) -> Response:
        page = request.args.get('page', 1, type=int)
        paginator = query_builder.paginate(per_page=per_page, page=page)
        return ApiResponse.paginated(paginator)

    def resource(self, resource: Any,
                 resource_class: Type[ApiResource] = None) -> Response:
        if resource_class:
            return resource_class(resource).to_response()
        return ApiResponse.success(
            resource.to_dict() if hasattr(resource, 'to_dict') else resource
        )

    def collection(self, items: List,
                   resource_class: Type[ApiResource] = None) -> Response:
        if resource_class:
            return ApiResourceCollection(items, resource_class).to_response()
        return ApiResponse.success([
            item.to_dict() if hasattr(item, 'to_dict') else item
            for item in items
        ])


# ─── API Versioning ───────────────────────────────────────────────────────────

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


# ─── OpenAPI / Swagger ────────────────────────────────────────────────────────

class OpenApiGenerator:
    """
    Generate OpenAPI 3.0 specification from routes.
    Visit /api/docs for Swagger UI.
    """

    def __init__(self, title: str = 'Laraflask API',
                 version: str = '1.0.0',
                 description: str = ''):
        self._spec = {
            'openapi': '3.0.0',
            'info': {
                'title': title,
                'version': version,
                'description': description,
            },
            'paths': {},
            'components': {
                'schemas': {},
                'securitySchemes': {
                    'bearerAuth': {
                        'type': 'http',
                        'scheme': 'bearer',
                        'bearerFormat': 'JWT',
                    },
                    'apiKeyAuth': {
                        'type': 'apiKey',
                        'in': 'header',
                        'name': 'X-API-KEY',
                    },
                },
            },
        }

    def add_path(self, path: str, method: str,
                 summary: str = '', description: str = '',
                 tags: List[str] = None, responses: Dict = None,
                 security: List = None) -> 'OpenApiGenerator':
        if path not in self._spec['paths']:
            self._spec['paths'][path] = {}

        self._spec['paths'][path][method.lower()] = {
            'summary': summary,
            'description': description,
            'tags': tags or [],
            'responses': responses or {'200': {'description': 'Success'}},
            'security': security or [],
        }
        return self

    def add_schema(self, name: str, schema: Dict) -> 'OpenApiGenerator':
        self._spec['components']['schemas'][name] = schema
        return self

    def server(self, url: str, description: str = '') -> 'OpenApiGenerator':
        self._spec.setdefault('servers', []).append({
            'url': url, 'description': description
        })
        return self

    def to_dict(self) -> Dict:
        return self._spec

    def to_json(self) -> str:
        import json
        return json.dumps(self._spec, indent=2)

    def register_routes(self, router: Any, prefix: str = '/api') -> None:
        """Register Swagger UI and spec endpoint."""
        spec = self._spec

        def spec_endpoint():
            return jsonify(spec)

        def swagger_ui():
            spec_url = f"{prefix}/openapi.json"
            return f"""<!DOCTYPE html>
<html>
<head>
    <title>API Documentation</title>
    <link rel="stylesheet" type="text/css"
          href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({{
            url: "{spec_url}",
            dom_id: '#swagger-ui',
            presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
            layout: "BaseLayout"
        }})
    </script>
</body>
</html>"""

        router.get(f'{prefix}/openapi.json', spec_endpoint)
        router.get(f'{prefix}/docs', swagger_ui)


# ─── Rate Limiting ────────────────────────────────────────────────────────────

class RateLimiter:
    """
    Configurable rate limiter.
    Use in middleware or directly in controllers.
    """

    _limiters: Dict[str, callable] = {}
    _store: Dict[str, Dict] = {}

    @classmethod
    def for_(cls, name: str, callback: callable) -> None:
        """Define a named rate limiter."""
        cls._limiters[name] = callback

    @classmethod
    def attempt(cls, key: str, max_attempts: int,
                decay_seconds: int = 60) -> bool:
        """Attempt to hit the rate limiter."""
        import time
        now = time.time()
        bucket = cls._store.get(key, {'count': 0, 'reset_at': now + decay_seconds})

        if now > bucket['reset_at']:
            bucket = {'count': 0, 'reset_at': now + decay_seconds}

        if bucket['count'] >= max_attempts:
            cls._store[key] = bucket
            return False

        bucket['count'] += 1
        cls._store[key] = bucket
        return True

    @classmethod
    def too_many_attempts(cls, key: str, max_attempts: int) -> bool:
        bucket = cls._store.get(key, {'count': 0})
        return bucket['count'] >= max_attempts

    @classmethod
    def available_in(cls, key: str) -> int:
        """Seconds until the limiter resets."""
        import time
        bucket = cls._store.get(key)
        if bucket:
            return max(0, int(bucket['reset_at'] - time.time()))
        return 0

    @classmethod
    def clear(cls, key: str) -> None:
        cls._store.pop(key, None)

    @classmethod
    def remaining_attempts(cls, key: str, max_attempts: int) -> int:
        bucket = cls._store.get(key, {'count': 0})
        return max(0, max_attempts - bucket['count'])
