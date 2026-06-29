"""Auth - Authentication facade."""

from __future__ import annotations
from typing import Any, Dict, Optional, Type

from laraflask.auth.guard import Guard
from laraflask.auth.session_guard import SessionGuard
from laraflask.auth.jwt_guard import JWTGuard
from laraflask.auth.api_key_guard import ApiKeyGuard


class Auth:
    """
    Authentication facade - unified interface to multiple guards.
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
