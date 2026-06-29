"""Gate and GateForUser - Authorization gate."""

from __future__ import annotations
from typing import Any, Dict, Optional, Type


class Gate:
    """Authorization gate - define and check abilities."""

    _abilities: Dict[str, Any] = {}
    _policies: Dict[str, Any] = {}
    _before_callbacks: list = []
    _after_callbacks: list = []

    @classmethod
    def define(cls, ability: str, callback: Any) -> None:
        cls._abilities[ability] = callback

    @classmethod
    def policy(cls, model_class: Type, policy_class: Type) -> None:
        cls._policies[model_class.__name__] = policy_class()

    @classmethod
    def before(cls, callback: Any) -> None:
        cls._before_callbacks.append(callback)

    @classmethod
    def after(cls, callback: Any) -> None:
        cls._after_callbacks.append(callback)

    @classmethod
    def allows(cls, ability: str, arguments: Any = None) -> bool:
        from laraflask.auth._auth import Auth
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
        if arguments is not None:
            model_name = type(arguments).__name__
            policy = cls._policies.get(model_name)
            if policy and hasattr(policy, ability):
                return getattr(policy, ability)(user, arguments)

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
