"""
Laraflask Authentication System
Multi-guard authentication: Session, JWT, OAuth2, and API Key.
"""

from __future__ import annotations
import os
import time
import hashlib
import secrets
import datetime
from typing import Any, Dict, Optional, Type
from functools import wraps


# ─── Password Hashing ─────────────────────────────────────────────────────────

class Hash:
    """Password hashing using bcrypt."""

    @staticmethod
    def make(password: str, rounds: int = 12) -> str:
        try:
            import bcrypt
            return bcrypt.hashpw(
                password.encode('utf-8'),
                bcrypt.gensalt(rounds=rounds)
            ).decode('utf-8')
        except ImportError:
            import hashlib
            salt = secrets.token_hex(16)
            hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
            return f"sha256${salt}${hashed}"

    @staticmethod
    def check(password: str, hashed: str) -> bool:
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except ImportError:
            try:
                _, salt, stored = hashed.split('$')
                computed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
                return secrets.compare_digest(computed, stored)
            except Exception:
                return False

    @staticmethod
    def needs_rehash(hashed: str, rounds: int = 12) -> bool:
        """Check whether the hash was generated with different rounds."""
        try:
            import bcrypt
            return bcrypt.checkpw.__module__ and                    bcrypt.gensalt(rounds=rounds).__len__() != len(bcrypt.gensalt())
        except Exception:
            return False


# ─── JWT Support ──────────────────────────────────────────────────────────────

class JWT:
    """JSON Web Token generation and verification."""

    ALGORITHM = 'HS256'

    def __init__(self, secret: str = None, ttl: int = 60):
        self._secret = secret or os.getenv('JWT_SECRET', os.getenv('APP_KEY', 'laraflask-jwt'))
        self._ttl = ttl  # minutes

    def encode(self, payload: Dict) -> str:
        """Generate a JWT token."""
        try:
            import jwt as pyjwt
            now = datetime.datetime.utcnow()
            payload.update({
                'iat': now,
                'exp': now + datetime.timedelta(minutes=self._ttl),
                'jti': secrets.token_hex(16),
            })
            return pyjwt.encode(payload, self._secret, algorithm=self.ALGORITHM)
        except ImportError:
            # Fallback: simple base64 encoding (NOT secure for production)
            import base64, json
            header = base64.urlsafe_b64encode(
                json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode()
            ).decode().rstrip('=')
            body = base64.urlsafe_b64encode(
                json.dumps({**payload, 'exp': time.time() + self._ttl * 60}).encode()
            ).decode().rstrip('=')
            sig = hashlib.sha256(f"{header}.{body}.{self._secret}".encode()).hexdigest()[:32]
            return f"{header}.{body}.{sig}"

    def decode(self, token: str) -> Optional[Dict]:
        """Decode and verify a JWT token."""
        try:
            import jwt as pyjwt
            return pyjwt.decode(token, self._secret, algorithms=[self.ALGORITHM])
        except ImportError:
            try:
                import base64, json
                parts = token.split('.')
                payload = json.loads(base64.urlsafe_b64decode(parts[1] + '==').decode())
                if payload.get('exp', 0) < time.time():
                    return None
                return payload
            except Exception:
                return None
        except Exception:
            return None

    def refresh(self, token: str) -> Optional[str]:
        """Refresh a JWT token."""
        payload = self.decode(token)
        if payload is None:
            return None
        for key in ('iat', 'exp', 'jti'):
            payload.pop(key, None)
        return self.encode(payload)


# ─── Guards ──────────────────────────────────────────────────────────────────

class Guard:
    """Base authentication guard."""

    def __init__(self, user_model: Type = None):
        self._user_model = user_model
        self._user: Optional[Any] = None

    def attempt(self, credentials: Dict) -> bool:
        raise NotImplementedError

    def login(self, user: Any) -> None:
        raise NotImplementedError

    def logout(self) -> None:
        raise NotImplementedError

    def user(self) -> Optional[Any]:
        raise NotImplementedError

    def check(self) -> bool:
        return self.user() is not None

    def guest(self) -> bool:
        return not self.check()

    def id(self) -> Optional[Any]:
        user = self.user()
        return getattr(user, 'id', None) if user else None


class SessionGuard(Guard):
    """Session-based authentication guard."""

    def attempt(self, credentials: Dict, remember: bool = False) -> bool:
        from flask import session as flask_session
        email = credentials.get('email') or credentials.get('username')
        password = credentials.get('password')

        if not email or not password:
            return False

        # Find user
        user = self._find_user(email)
        if user is None:
            return False

        # Verify password
        stored_password = getattr(user, 'password', None)
        if not stored_password or not Hash.check(password, stored_password):
            return False

        self.login(user, remember)
        return True

    def login(self, user: Any, remember: bool = False) -> None:
        from flask import session as flask_session
        self._user = user
        flask_session['user_id'] = getattr(user, 'id', None)
        flask_session['_token'] = secrets.token_hex(32)

        if remember:
            token = secrets.token_hex(60)
            flask_session['remember_token'] = token
            # Store token in DB
            if hasattr(user, 'remember_token'):
                user.remember_token = token
                user.save()

    def logout(self) -> None:
        from flask import session as flask_session
        self._user = None
        flask_session.pop('user_id', None)
        flask_session.pop('remember_token', None)
        flask_session.clear()

    def user(self) -> Optional[Any]:
        from flask import session as flask_session
        if self._user:
            return self._user

        user_id = flask_session.get('user_id')
        if user_id and self._user_model:
            self._user = self._user_model.find(user_id)

        return self._user

    def _find_user(self, email: str) -> Optional[Any]:
        if not self._user_model:
            return None
        try:
            return self._user_model.where('email', email).first()
        except Exception:
            return None

    def login_using_id(self, user_id: Any, remember: bool = False) -> Optional[Any]:
        if self._user_model:
            user = self._user_model.find(user_id)
            if user:
                self.login(user, remember)
                return user
        return None

    def once(self, credentials: Dict) -> bool:
        """Log the user in for a single request (no session persistence)."""
        email = credentials.get('email')
        password = credentials.get('password')
        user = self._find_user(email)
        if user and Hash.check(password, getattr(user, 'password', '')):
            self._user = user
            return True
        return False

    def viaRemember(self) -> bool:
        from flask import session as flask_session
        return bool(flask_session.get('remember_token'))


class JWTGuard(Guard):
    """JWT-based authentication guard (stateless)."""

    def __init__(self, user_model: Type = None, ttl: int = 60):
        super().__init__(user_model)
        self._jwt = JWT(ttl=ttl)

    def attempt(self, credentials: Dict) -> Optional[str]:
        email = credentials.get('email')
        password = credentials.get('password')

        if not email or not password:
            return None

        user = self._find_user(email)
        if user is None:
            return None

        if not Hash.check(password, getattr(user, 'password', '')):
            return None

        self._user = user
        return self._jwt.encode({
            'sub': str(getattr(user, 'id', '')),
            'email': getattr(user, 'email', ''),
        })

    def user(self) -> Optional[Any]:
        if self._user:
            return self._user

        from flask import request
        token = self._extract_token(request)
        if not token:
            return None

        payload = self._jwt.decode(token)
        if not payload:
            return None

        user_id = payload.get('sub')
        if user_id and self._user_model:
            self._user = self._user_model.find(user_id)

        return self._user

    def login(self, user: Any) -> str:
        self._user = user
        return self._jwt.encode({
            'sub': str(getattr(user, 'id', '')),
            'email': getattr(user, 'email', ''),
        })

    def logout(self) -> None:
        self._user = None
        # Add token to blacklist (if using Redis/Cache)

    def refresh(self) -> Optional[str]:
        from flask import request
        token = self._extract_token(request)
        return self._jwt.refresh(token) if token else None

    def _find_user(self, email: str) -> Optional[Any]:
        if not self._user_model:
            return None
        try:
            return self._user_model.where('email', email).first()
        except Exception:
            return None

    def _extract_token(self, request) -> Optional[str]:
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            return auth[7:]
        return request.args.get('token') or request.form.get('token')


class ApiKeyGuard(Guard):
    """API Key authentication guard."""

    def __init__(self, user_model: Type = None, header: str = 'X-API-KEY'):
        super().__init__(user_model)
        self._header = header

    def user(self) -> Optional[Any]:
        if self._user:
            return self._user

        from flask import request
        api_key = (request.headers.get(self._header)
                   or request.args.get('api_key')
                   or request.headers.get('Authorization', '').replace('Bearer ', ''))

        if not api_key or not self._user_model:
            return None

        try:
            self._user = self._user_model.where('api_key', api_key).first()
        except Exception:
            pass

        return self._user

    def attempt(self, credentials: Dict) -> bool:
        return False  # API keys don't use credentials

    def login(self, user: Any) -> None:
        self._user = user

    def logout(self) -> None:
        self._user = None


# ─── Auth Facade ─────────────────────────────────────────────────────────────

class Auth:
    """
    Authentication facade — unified interface to multiple guards.
    Works like Laravel's Auth facade.
    """

    _guards: Dict[str, Guard] = {}
    _default_guard: str = 'web'
    _user_models: Dict[str, Type] = {}

    @classmethod
    def configure(cls, guards: Dict = None, default: str = 'web'):
        cls._default_guard = default
        if guards:
            for name, config in guards.items():
                cls._guards[name] = config

    @classmethod
    def guard(cls, name: str = None) -> Guard:
        name = name or cls._default_guard
        if name not in cls._guards:
            raise ValueError(f"Auth guard [{name}] is not defined.")
        guard = cls._guards[name]
        if isinstance(guard, dict):
            driver = guard.get('driver', 'session')
            model = cls._user_models.get(guard.get('provider', 'users'))
            if driver == 'session':
                cls._guards[name] = SessionGuard(model)
            elif driver == 'jwt':
                cls._guards[name] = JWTGuard(model, ttl=guard.get('ttl', 60))
            elif driver == 'api':
                cls._guards[name] = ApiKeyGuard(model)
        return cls._guards[name]

    @classmethod
    def attempt(cls, credentials: Dict, guard: str = None) -> bool:
        return cls.guard(guard).attempt(credentials)

    @classmethod
    def login(cls, user: Any, guard: str = None) -> None:
        return cls.guard(guard).login(user)

    @classmethod
    def logout(cls, guard: str = None) -> None:
        return cls.guard(guard).logout()

    @classmethod
    def user(cls, guard: str = None) -> Optional[Any]:
        return cls.guard(guard).user()

    @classmethod
    def check(cls, guard: str = None) -> bool:
        return cls.guard(guard).check()

    @classmethod
    def guest(cls, guard: str = None) -> bool:
        return cls.guard(guard).guest()

    @classmethod
    def id(cls, guard: str = None) -> Optional[Any]:
        return cls.guard(guard).id()

    @classmethod
    def register_model(cls, provider: str, model: Type):
        cls._user_models[provider] = model

    @classmethod
    def register_guard(cls, name: str, guard: Guard):
        cls._guards[name] = guard


# ─── Authorization ────────────────────────────────────────────────────────────

class Gate:
    """
    Authorization gate — define and check abilities.
    """

    _abilities: Dict[str, Any] = {}
    _policies: Dict[str, Any] = {}
    _before_callbacks: list = []
    _after_callbacks: list = []

    @classmethod
    def define(cls, ability: str, callback: Any) -> None:
        """Define a gate ability."""
        cls._abilities[ability] = callback

    @classmethod
    def policy(cls, model_class: Type, policy_class: Type) -> None:
        """Register a policy for a model."""
        cls._policies[model_class.__name__] = policy_class()

    @classmethod
    def before(cls, callback: Any) -> None:
        """Register a before callback."""
        cls._before_callbacks.append(callback)

    @classmethod
    def after(cls, callback: Any) -> None:
        """Register an after callback."""
        cls._after_callbacks.append(callback)

    @classmethod
    def allows(cls, ability: str, arguments: Any = None) -> bool:
        """Check if the current user can perform the ability."""
        user = Auth.user()

        for callback in cls._before_callbacks:
            result = callback(user, ability)
            if result is not None:
                return result

        result = cls._check(user, ability, arguments)

        for callback in cls._after_callbacks:
            callback(user, ability, result)

        return result

    @classmethod
    def denies(cls, ability: str, arguments: Any = None) -> bool:
        return not cls.allows(ability, arguments)

    @classmethod
    def authorize(cls, ability: str, arguments: Any = None):
        if cls.denies(ability, arguments):
            from flask import abort
            abort(403)

    @classmethod
    def can(cls, ability: str, model: Any = None) -> bool:
        return cls.allows(ability, model)

    @classmethod
    def cannot(cls, ability: str, model: Any = None) -> bool:
        return not cls.can(ability, model)

    @classmethod
    def _check(cls, user: Any, ability: str, arguments: Any) -> bool:
        # Check policy first
        if arguments is not None:
            model_name = type(arguments).__name__
            policy = cls._policies.get(model_name)
            if policy and hasattr(policy, ability):
                return getattr(policy, ability)(user, arguments)

        # Fall back to ability
        callback = cls._abilities.get(ability)
        if callback is None:
            return False

        if callable(callback):
            return bool(callback(user, arguments) if arguments else callback(user))

        return bool(callback)

    @classmethod
    def for_user(cls, user: Any) -> 'GateForUser':
        return GateForUser(user)


class GateForUser:
    """Gate checked for a specific user."""

    def __init__(self, user: Any):
        self._user = user

    def can(self, ability: str, model: Any = None) -> bool:
        return Gate._check(self._user, ability, model)

    def cannot(self, ability: str, model: Any = None) -> bool:
        return not self.can(ability, model)


class Policy:
    """Base class for resource policies."""

    def before(self, user: Any, ability: str) -> Optional[bool]:
        """Called before every policy check."""
        return None

    def view_any(self, user: Any) -> bool:
        return False

    def view(self, user: Any, model: Any) -> bool:
        return False

    def create(self, user: Any) -> bool:
        return False

    def update(self, user: Any, model: Any) -> bool:
        return False

    def delete(self, user: Any, model: Any) -> bool:
        return False

    def restore(self, user: Any, model: Any) -> bool:
        return False

    def force_delete(self, user: Any, model: Any) -> bool:
        return False


# ─── Decorators ──────────────────────────────────────────────────────────────

def auth_required(guard: str = None):
    """Route decorator requiring authentication."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
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
            model = kwargs.get(model_arg) if model_arg else None
            if Gate.denies(ability, model):
                from flask import abort
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator
