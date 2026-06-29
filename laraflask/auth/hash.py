"""Hash - Password hashing using bcrypt."""

from __future__ import annotations
import hashlib
import secrets


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
        try:
            import bcrypt
            return bcrypt.checkpw.__module__ and \
                   bcrypt.gensalt(rounds=rounds).__len__() != len(bcrypt.gensalt())
        except Exception:
            return False
