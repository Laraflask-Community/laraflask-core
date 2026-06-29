"""OpenApiGenerator - Generate OpenAPI 3.0 specification from routes."""

from __future__ import annotations
from typing import Any, Dict, List
from flask import jsonify


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
