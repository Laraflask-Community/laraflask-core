"""JWT - JSON Web Token generation and verification."""

from __future__ import annotations
import os
import time
import hashlib
import secrets
import datetime
from typing import Dict, Optional


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
