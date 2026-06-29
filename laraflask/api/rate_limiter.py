"""RateLimiter - Configurable rate limiter."""

from __future__ import annotations
from typing import Dict


class RateLimiter:
    """
    Configurable rate limiter.
    Use in middleware or directly in controllers.
    """

    _limiters: Dict[str, callable] = {}
    _store: Dict[str, Dict] = {}

    @classmethod
    def for_(cls, name: str, callback: callable) -> None:
        """Define a named rate limiter."""
        cls._limiters[name] = callback

    @classmethod
    def attempt(cls, key: str, max_attempts: int,
                decay_seconds: int = 60) -> bool:
        """Attempt to hit the rate limiter."""
        import time
        now = time.time()
        bucket = cls._store.get(key, {'count': 0, 'reset_at': now + decay_seconds})

        if now > bucket['reset_at']:
            bucket = {'count': 0, 'reset_at': now + decay_seconds}

        if bucket['count'] >= max_attempts:
            cls._store[key] = bucket
            return False

        bucket['count'] += 1
        cls._store[key] = bucket
        return True

    @classmethod
    def too_many_attempts(cls, key: str, max_attempts: int) -> bool:
        bucket = cls._store.get(key, {'count': 0})
        return bucket['count'] >= max_attempts

    @classmethod
    def available_in(cls, key: str) -> int:
        """Seconds until the limiter resets."""
        import time
        bucket = cls._store.get(key)
        if bucket:
            return max(0, int(bucket['reset_at'] - time.time()))
        return 0

    @classmethod
    def clear(cls, key: str) -> None:
        cls._store.pop(key, None)

    @classmethod
    def remaining_attempts(cls, key: str, max_attempts: int) -> int:
        bucket = cls._store.get(key, {'count': 0})
        return max(0, max_attempts - bucket['count'])
