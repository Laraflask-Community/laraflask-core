"""Guard - Base authentication guard."""

from __future__ import annotations
from typing import Any, Optional, Type


class Guard:
    """Base authentication guard."""

    def __init__(self, user_model: Type = None):
        self._user_model = user_model
        self._user: Optional[Any] = None

    def attempt(self, credentials: dict) -> bool:
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
