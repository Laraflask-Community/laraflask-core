"""Auth decorators - auth_required and can."""

from __future__ import annotations
from functools import wraps


def auth_required(guard: str = None):
    """Route decorator requiring authentication."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from laraflask.auth._auth import Auth
            if Auth.guest(guard):
                from flask import request, jsonify, redirect, url_for
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'message': 'Unauthenticated.'}), 401
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def can(ability: str, model_arg: str = None):
    """Route decorator checking Gate ability."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from laraflask.auth.gate import Gate
            model = kwargs.get(model_arg) if model_arg else None
            if Gate.denies(ability, model):
                from flask import abort
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator
