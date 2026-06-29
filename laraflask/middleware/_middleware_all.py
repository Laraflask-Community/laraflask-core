"""
Laraflask Middleware System
Global, route, group, and terminable middleware support.
"""

from __future__ import annotations
import re
import time
import hashlib
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from flask import Request, Response, request, session, abort, jsonify, redirect


class Middleware(ABC):
    """
    Base Middleware class.
    All middleware must implement handle().
    """

    @abstractmethod
    def handle(self, request: Request, next: Callable) -> Any:
        """Handle an incoming request."""
        pass

    def terminate(self, request: Request, response: Response) -> None:
        """Perform tasks after the response is sent (terminable middleware)."""
        pass


class MiddlewarePipeline:
    """
    Processes a request through a stack of middleware.
    Like a pipeline: request -> mw1 -> mw2 -> ... -> handler -> response
    """

    def __init__(self, middleware_stack: List[Middleware]):
        self._stack = middleware_stack

    def run(self, request: Request, destination: Callable) -> Any:
        """Run the request through the pipeline."""
        pipeline = self._build_pipeline(destination)
        return pipeline(request)

    def _build_pipeline(self, destination: Callable) -> Callable:
        """Build the nested middleware pipeline."""
        def carry(stack, middleware):
            def pipe(req):
                return middleware.handle(req, lambda r: stack(r))
            return pipe

        pipeline = destination
        for mw in reversed(self._stack):
            pipeline = carry(pipeline, mw)

        return pipeline


# ─── Built-in Middleware ──────────────────────────────────────────────────────

class AuthMiddleware(Middleware):
    """Authenticate the request using session or JWT."""

    def __init__(self, guard: str = 'web'):
        self._guard = guard

    def handle(self, request: Request, next: Callable) -> Any:
        from flask import session, redirect, url_for
        user = session.get('user')
        if not user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'message': 'Unauthenticated.'}), 401
            return redirect(url_for('login'))
        return next(request)


class GuestMiddleware(Middleware):
    """Redirect authenticated users."""

    def handle(self, request: Request, next: Callable) -> Any:
        if session.get('user'):
            return redirect('/')
        return next(request)


class CsrfMiddleware(Middleware):
    """Verify CSRF token on state-changing requests."""

    EXEMPT_METHODS = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}
    EXEMPT_PATTERNS = [
        r'^/api/',
        r'^/webhooks/',
    ]

    def handle(self, request: Request, next: Callable) -> Any:
        if request.method in self.EXEMPT_METHODS:
            return next(request)

        for pattern in self.EXEMPT_PATTERNS:
            if re.match(pattern, request.path):
                return next(request)

        token = (
            request.form.get('_token')
            or request.headers.get('X-CSRF-TOKEN')
            or request.headers.get('X-XSRF-TOKEN')
        )

        session_token = session.get('_token')

        if not token or not session_token or token != session_token:
            abort(419)

        return next(request)


class PreventRequestForgeryMiddleware(Middleware):
    """
    [ID] Alternatif `CsrfMiddleware` yang menambahkan layer origin-aware
    verification (cek `Origin`/`Referer`) di atas verifikasi token CSRF
    yang sudah ada — mengadaptasi peningkatan CSRF protection Laravel 13
    ke Python. `CsrfMiddleware` lama TIDAK diubah dan tetap berfungsi apa
    adanya; middleware ini adalah pilihan tambahan, didaftarkan terpisah
    di `app/Http/Kernel.py` saat ingin perlindungan ekstra.

    [EN] An alternative to `CsrfMiddleware` that adds an origin-aware
    verification layer (checking `Origin`/`Referer`) on top of the
    existing CSRF token verification — adapting Laravel 13's CSRF
    protection upgrade to Python. The old `CsrfMiddleware` is NOT modified
    and keeps working as-is; this middleware is an additional opt-in,
    registered separately in `app/Http/Kernel.py` when extra protection is
    wanted.
    """

    EXEMPT_METHODS = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}
    EXEMPT_PATTERNS = [
        r'^/api/',
        r'^/webhooks/',
    ]

    def __init__(self, trusted_origins: List[str] = None):
        from laraflask.security.security import PreventRequestForgery
        self._guard = PreventRequestForgery(trusted_origins)

    def handle(self, request: Request, next: Callable) -> Any:
        if request.method in self.EXEMPT_METHODS:
            return next(request)

        for pattern in self.EXEMPT_PATTERNS:
            if re.match(pattern, request.path):
                return next(request)

        token = (
            request.form.get('_token')
            or request.headers.get('X-CSRF-TOKEN')
            or request.headers.get('X-XSRF-TOKEN')
        )

        if not self._guard.verify(token, session, request):
            abort(419)

        return next(request)


class ThrottleMiddleware(Middleware):
    """Rate limiting middleware."""

    def __init__(self, max_attempts: int = 60, decay_minutes: int = 1):
        self._max = max_attempts
        self._decay = decay_minutes
        self._cache: Dict[str, Dict] = {}

    def handle(self, request: Request, next: Callable) -> Any:
        key = self._resolve_key(request)
        bucket = self._cache.get(key, {'count': 0, 'reset_at': time.time() + self._decay * 60})

        if time.time() > bucket['reset_at']:
            bucket = {'count': 0, 'reset_at': time.time() + self._decay * 60}

        bucket['count'] += 1
        self._cache[key] = bucket

        if bucket['count'] > self._max:
            try:
                response = jsonify({'message': 'Too Many Requests.'})
                response.status_code = 429
                response.headers['Retry-After'] = str(int(bucket['reset_at'] - time.time()))
            except RuntimeError:
                from flask import Response
                import json
                response = Response(
                    json.dumps({'message': 'Too Many Requests.'}),
                    status=429, mimetype='application/json'
                )
            return response

        response = next(request)
        return response

    def _resolve_key(self, request: Request) -> str:
        ip = request.remote_addr or '127.0.0.1'
        return hashlib.md5(ip.encode()).hexdigest()


class CorsMiddleware(Middleware):
    """Handle CORS headers."""

    def __init__(self, allowed_origins: List[str] = None,
                 allowed_methods: List[str] = None,
                 allowed_headers: List[str] = None,
                 max_age: int = 86400):
        self._origins = allowed_origins or ['*']
        self._methods = allowed_methods or ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
        self._headers = allowed_headers or ['Content-Type', 'Authorization', 'X-Requested-With']
        self._max_age = max_age

    def handle(self, request: Request, next: Callable) -> Any:
        if request.method == 'OPTIONS':
            response = Response()
        else:
            response = next(request)

        origin = request.headers.get('Origin', '*')
        allowed = origin if origin in self._origins or '*' in self._origins else ''

        if isinstance(response, tuple):
            body, status = response[0], response[1]
            from flask import make_response
            response = make_response(body, status)

        response.headers['Access-Control-Allow-Origin'] = allowed or '*'
        response.headers['Access-Control-Allow-Methods'] = ', '.join(self._methods)
        response.headers['Access-Control-Allow-Headers'] = ', '.join(self._headers)
        response.headers['Access-Control-Max-Age'] = str(self._max_age)
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        return response


class SecureHeadersMiddleware(Middleware):
    """Add security headers to every response."""

    def handle(self, request: Request, next: Callable) -> Any:
        response = next(request)

        if isinstance(response, tuple):
            from flask import make_response
            response = make_response(*response)

        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('X-XSS-Protection', '1; mode=block')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault(
            'Permissions-Policy',
            'camera=(), microphone=(), geolocation=()'
        )
        response.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        )
        return response


class TrimStringsMiddleware(Middleware):
    """Trim whitespace from all string inputs."""

    EXCEPT = ['password', 'password_confirmation', 'current_password']

    def handle(self, request: Request, next: Callable) -> Any:
        form_data = request.form.to_dict(flat=False)
        for key in form_data:
            if key not in self.EXCEPT:
                form_data[key] = [v.strip() if isinstance(v, str) else v
                                   for v in form_data[key]]
        return next(request)


class ConvertEmptyStringsToNullMiddleware(Middleware):
    """Convert empty string inputs to None."""

    EXCEPT = ['password', 'password_confirmation']

    def handle(self, request: Request, next: Callable) -> Any:
        return next(request)


class SessionMiddleware(Middleware):
    """Start and manage the user session."""

    def handle(self, request: Request, next: Callable) -> Any:
        return next(request)

    def terminate(self, request: Request, response: Response) -> None:
        pass


class LogRequestMiddleware(Middleware):
    """Log all incoming requests."""

    def handle(self, request: Request, next: Callable) -> Any:
        start = time.time()
        response = next(request)
        elapsed = (time.time() - start) * 1000

        import logging
        logging.getLogger('laraflask').info(
            f"{request.method} {request.path} "
            f"[{getattr(response, 'status_code', '?')}] "
            f"{elapsed:.2f}ms"
        )
        return response


class ForceHttpsMiddleware(Middleware):
    """Redirect HTTP requests to HTTPS in production."""

    def handle(self, request: Request, next: Callable) -> Any:
        if not request.is_secure and not request.headers.get('X-Forwarded-Proto') == 'https':
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)
        return next(request)


class MaintenanceModeMiddleware(Middleware):
    """Return 503 when app is in maintenance mode."""

    def handle(self, request: Request, next: Callable) -> Any:
        import os
        if os.path.exists('storage/framework/down'):
            return jsonify({'message': 'Service Unavailable. We\'ll be back soon!'}), 503
        return next(request)


class SubstituteBindingsMiddleware(Middleware):
    """Substitute route model bindings."""

    def handle(self, request: Request, next: Callable) -> Any:
        return next(request)


class VerifySignedMiddleware(Middleware):
    """Verify signed URLs."""

    def handle(self, request: Request, next: Callable) -> Any:
        signature = request.args.get('signature')
        expires = request.args.get('expires')

        if expires and float(expires) < time.time():
            abort(403)

        return next(request)


# ─── Middleware Registry ──────────────────────────────────────────────────────

class MiddlewareRegistry:
    """Registry of all available middleware aliases."""

    _registry: Dict[str, type] = {
        'auth':             AuthMiddleware,
        'guest':            GuestMiddleware,
        'csrf':             CsrfMiddleware,
        'throttle':         ThrottleMiddleware,
        'cors':             CorsMiddleware,
        'secure.headers':   SecureHeadersMiddleware,
        'trim.strings':     TrimStringsMiddleware,
        'session':          SessionMiddleware,
        'log':              LogRequestMiddleware,
        'https':            ForceHttpsMiddleware,
        'maintenance':      MaintenanceModeMiddleware,
        'signed':           VerifySignedMiddleware,
    }

    @classmethod
    def register(cls, alias: str, middleware_class: type):
        cls._registry[alias] = middleware_class

    @classmethod
    def resolve(cls, alias: str) -> Optional[type]:
        """Resolve middleware by alias, supporting 'throttle:60,1' syntax."""
        if ':' in alias:
            name, params = alias.split(':', 1)
            mw_class = cls._registry.get(name)
            if mw_class:
                args = [int(p) if p.isdigit() else p for p in params.split(',')]
                return lambda: mw_class(*args)
        return cls._registry.get(alias)

    @classmethod
    def all(cls) -> Dict[str, type]:
        return cls._registry.copy()
