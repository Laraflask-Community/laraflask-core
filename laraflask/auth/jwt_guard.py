"""JWTGuard - JWT-based authentication guard (stateless)."""

from __future__ import annotations
from typing import Any, Dict, Optional, Type

from laraflask.auth.guard import Guard
from laraflask.auth.hash import Hash
from laraflask.auth.jwt import JWT


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
