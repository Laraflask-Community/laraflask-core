"""SessionGuard - Session-based authentication guard."""

from __future__ import annotations
import secrets
from typing import Any, Dict, Optional, Type

from laraflask.auth.guard import Guard
from laraflask.auth.hash import Hash


class SessionGuard(Guard):
    """Session-based authentication guard."""

    def attempt(self, credentials: Dict, remember: bool = False) -> bool:
        from flask import session as flask_session
        email = credentials.get('email') or credentials.get('username')
        password = credentials.get('password')

        if not email or not password:
            return False

        user = self._find_user(email)
        if user is None:
            return False

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
