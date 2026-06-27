"""
Laraflask Router
Elegant, expressive routing with groups, names, resources, and middleware.
"""

from __future__ import annotations
import re
from typing import Any, Callable, Dict, List, Optional, Type, Union
from flask import Flask, request, jsonify, redirect, url_for
from functools import wraps


class RouteGroup:
    """Represents a group of routes sharing common attributes."""

    def __init__(self, router: 'Router', attributes: Dict):
        self._router = router
        self._attributes = attributes
        self._previous_group = None

    def __enter__(self):
        self._previous_group = self._router._current_group.copy()
        self._router._current_group.update(self._attributes)
        return self

    def __exit__(self, *args):
        self._router._current_group = self._previous_group


class Route:
    """Represents a single registered route."""

    def __init__(self, methods: List[str], uri: str, action: Any, name: str = None):
        self.methods = methods
        self.uri = uri
        self.action = action
        self._name = name
        self._middleware: List[str] = []
        self._prefix = ''
        self._domain = None

    def name(self, name: str) -> 'Route':
        """Assign a name to the route."""
        self._name = name
        return self

    def middleware(self, *middleware: str) -> 'Route':
        """Assign middleware to the route."""
        self._middleware.extend(middleware)
        return self

    def prefix(self, prefix: str) -> 'Route':
        self._prefix = prefix
        return self

    def domain(self, domain: str) -> 'Route':
        self._domain = domain
        return self

    def get_name(self) -> Optional[str]:
        return self._name

    def get_middleware(self) -> List[str]:
        return self._middleware


class Router:
    """
    The Laraflask Router.

    Provides an expressive, fluent interface for defining routes.
    """

    RESOURCE_METHODS = {
        'index':   ('GET',    ''),
        'create':  ('GET',    '/create'),
        'store':   ('POST',   ''),
        'show':    ('GET',    '/<int:id>'),
        'edit':    ('GET',    '/<int:id>/edit'),
        'update':  ('PUT',    '/<int:id>'),
        'destroy': ('DELETE', '/<int:id>'),
    }

    def __init__(self, flask_app: Flask, container: Any):
        self._flask = flask_app
        self._container = container
        self._routes: List[Route] = []
        self._named_routes: Dict[str, str] = {}
        self._middleware_groups: Dict[str, List] = {
            'web': ['session', 'csrf'],
            'api': ['throttle:60,1'],
        }
        self._route_middleware: Dict[str, Any] = {}
        self._current_group: Dict = {}
        self._global_middleware: List = []

    # ─── HTTP Verbs ───────────────────────────────────────────────────────────

    def get(self, uri: str, action: Any) -> Route:
        return self._add_route(['GET', 'HEAD'], uri, action)

    def post(self, uri: str, action: Any) -> Route:
        return self._add_route(['POST'], uri, action)

    def put(self, uri: str, action: Any) -> Route:
        return self._add_route(['PUT'], uri, action)

    def patch(self, uri: str, action: Any) -> Route:
        return self._add_route(['PATCH'], uri, action)

    def delete(self, uri: str, action: Any) -> Route:
        return self._add_route(['DELETE'], uri, action)

    def options(self, uri: str, action: Any) -> Route:
        return self._add_route(['OPTIONS'], uri, action)

    def any(self, uri: str, action: Any) -> Route:
        return self._add_route(['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'], uri, action)

    def match(self, methods: List[str], uri: str, action: Any) -> Route:
        return self._add_route([m.upper() for m in methods], uri, action)

    # ─── Route Groups ─────────────────────────────────────────────────────────

    def group(self, attributes: Dict, callback: Callable = None):
        """Create a route group with shared attributes."""
        if callback:
            with RouteGroup(self, attributes):
                callback()
        else:
            return RouteGroup(self, attributes)

    def prefix(self, prefix: str):
        """Create a route group with a URI prefix."""
        return RouteGroup(self, {'prefix': prefix})

    def middleware(self, *middleware: str):
        """Create a route group with middleware."""
        return RouteGroup(self, {'middleware': list(middleware)})

    def namespace(self, namespace: str):
        """Create a route group with a namespace."""
        return RouteGroup(self, {'namespace': namespace})

    # ─── Resource Routes ──────────────────────────────────────────────────────

    def resource(self, name: str, controller: Any,
                 only: List[str] = None, except_: List[str] = None) -> 'Router':
        """Register a resourceful route to a controller."""
        methods = list(self.RESOURCE_METHODS.keys())

        if only:
            methods = [m for m in methods if m in only]
        if except_:
            methods = [m for m in methods if m not in except_]

        for action in methods:
            http_method, suffix = self.RESOURCE_METHODS[action]
            uri = f"/{name}{suffix}"
            self._add_route(
                [http_method],
                uri,
                f"{controller}@{action}" if isinstance(controller, str) else (controller, action)
            ).name(f"{name}.{action}")

        return self

    def api_resource(self, name: str, controller: Any) -> 'Router':
        """Register an API resource (without create/edit routes)."""
        return self.resource(name, controller,
                             only=['index', 'store', 'show', 'update', 'destroy'])

    # ─── Middleware Registry ───────────────────────────────────────────────────

    def alias_middleware(self, name: str, middleware: Any) -> 'Router':
        """Register a short-hand name for a middleware."""
        self._route_middleware[name] = middleware
        return self

    def middleware_group(self, name: str, middleware: List) -> 'Router':
        """Register a group of middleware with a short-hand name."""
        self._middleware_groups[name] = middleware
        return self

    # ─── Internal ─────────────────────────────────────────────────────────────

    def _add_route(self, methods: List[str], uri: str, action: Any) -> Route:
        """Add a route to the router and Flask."""
        # Apply group attributes
        prefix = self._current_group.get('prefix', '')
        group_middleware = self._current_group.get('middleware', [])

        full_uri = f"{prefix}{uri}".replace('//', '/')

        route = Route(methods, full_uri, action)
        route._middleware.extend(group_middleware)
        self._routes.append(route)

        # Convert Flask-style URI
        flask_uri = self._convert_uri(full_uri)
        view_func = self._build_view_func(action, route)

        endpoint = self._make_endpoint(full_uri, methods)

        self._flask.add_url_rule(
            flask_uri,
            endpoint=endpoint,
            view_func=view_func,
            methods=methods,
        )

        return route

    def _convert_uri(self, uri: str) -> str:
        """Convert Laraflask URI params to Flask format."""
        # {id} -> <id>, {id?} -> optional
        uri = re.sub(r'\{(\w+)\}', r'<\1>', uri)
        uri = re.sub(r'\{(\w+)\?\}', r'<\1>', uri)
        return uri

    def _make_endpoint(self, uri: str, methods: List[str]) -> str:
        """Generate a unique endpoint name."""
        safe = uri.replace('/', '_').replace('<', '').replace('>', '').strip('_')
        method_str = '_'.join(methods[:1])
        return f"{method_str}_{safe}" or 'root'

    def _build_view_func(self, action: Any, route: Route) -> Callable:
        """Build a Flask view function from a Laraflask action."""

        @wraps(action if callable(action) else lambda: None)
        def view_func(**kwargs):
            # Apply middleware
            for mw_name in route.get_middleware():
                mw = self._resolve_middleware(mw_name)
                if mw:
                    result = mw.handle(request, lambda r: None)
                    if result is not None:
                        return result

            # Resolve and call controller action
            return self._call_action(action, kwargs)

        view_func.__name__ = self._make_endpoint(route.uri, route.methods)
        return view_func

    def _call_action(self, action: Any, params: Dict) -> Any:
        """Resolve and call the route action."""
        if callable(action):
            return self._container.call(action, params)

        if isinstance(action, str) and '@' in action:
            class_path, method = action.split('@')
            controller = self._container.make(class_path)
            return self._container.call(getattr(controller, method), params)

        if isinstance(action, (list, tuple)) and len(action) == 2:
            controller_class, method = action
            if isinstance(controller_class, str):
                controller = self._container.make(controller_class)
            else:
                controller = self._container.make(controller_class)
            return self._container.call(getattr(controller, method), params)

        raise ValueError(f"Invalid route action: {action}")

    def _resolve_middleware(self, name: str) -> Optional[Any]:
        """Resolve a middleware by name."""
        if name in self._route_middleware:
            mw_class = self._route_middleware[name]
            return self._container.make(mw_class)
        return None

    def get_routes(self) -> List[Route]:
        return self._routes

    def get_named_routes(self) -> Dict[str, str]:
        return self._named_routes

    def url_for(self, name: str, **values) -> str:
        """Generate a URL for a named route."""
        if name in self._named_routes:
            return url_for(self._named_routes[name], **values)
        return url_for(name, **values)

    # ─── Redirect Helpers ─────────────────────────────────────────────────────

    def redirect(self, from_uri: str, to_uri: str, status: int = 302) -> Route:
        """Register a redirect route."""
        return self.get(from_uri, lambda: redirect(to_uri, status))

    def permanent_redirect(self, from_uri: str, to_uri: str) -> Route:
        return self.redirect(from_uri, to_uri, 301)

    def view(self, uri: str, template: str, data: Dict = None) -> Route:
        """Register a route that returns a view."""
        from flask import render_template
        return self.get(uri, lambda: render_template(template, **(data or {})))
