"""ApiKeyGuard - API Key authentication guard."""

from __future__ import annotations
from typing import Any, Dict, Optional, Type

from laraflask.auth.guard import Guard


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
        return False

    def login(self, user: Any) -> None:
        self._user = user

    def logout(self) -> None:
        self._user = None
