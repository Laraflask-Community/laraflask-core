"""
Laraflask Cache System
Multi-driver cache: File, Redis, Database, Memcached, and In-Memory.
"""

from __future__ import annotations
import os
import json
import time
import pickle
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger('laraflask.cache')


class CacheDriver(ABC):
    """Abstract cache driver."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]: pass

    @abstractmethod
    def put(self, key: str, value: Any, seconds: int = None) -> bool: pass

    @abstractmethod
    def has(self, key: str) -> bool: pass

    @abstractmethod
    def forget(self, key: str) -> bool: pass

    @abstractmethod
    def flush(self) -> bool: pass

    @abstractmethod
    def increment(self, key: str, value: int = 1) -> int: pass

    @abstractmethod
    def decrement(self, key: str, value: int = 1) -> int: pass

    def touch(self, key: str, seconds: int) -> bool:
        """
        [ID] Perpanjang TTL sebuah key tanpa mengambil-ulang (fetch) nilainya
        — idealnya satu round-trip ke backend, bukan get() lalu put().
        Implementasi default ini tetap melakukan get+put sebagai fallback
        untuk driver yang tidak override method ini secara native.

        [EN] Extend a key's TTL without re-fetching its value — ideally a
        single round-trip to the backend instead of get() then put(). This
        default implementation falls back to a get+put cycle for drivers
        that don't natively override it.
        """
        value = self.get(key)
        if value is None:
            return False
        return self.put(key, value, seconds)


class FileDriver(CacheDriver):
    """File-based cache driver."""

    def __init__(self, path: str = None):
        self._path = path or os.path.join(os.getcwd(), 'storage', 'cache', 'data')
        os.makedirs(self._path, exist_ok=True)

    def _key_path(self, key: str) -> str:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        return os.path.join(self._path, hashed[:2], hashed + '.cache')

    def _read(self, key: str) -> Optional[Dict]:
        path = self._key_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            if data.get('expires_at') and time.time() > data['expires_at']:
                os.remove(path)
                return None
            return data
        except Exception:
            return None

    def get(self, key: str) -> Optional[Any]:
        data = self._read(key)
        return data['value'] if data else None

    def put(self, key: str, value: Any, seconds: int = None) -> bool:
        path = self._key_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            'value': value,
            'expires_at': (time.time() + seconds) if seconds else None,
        }
        try:
            with open(path, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            logger.error(f"Cache put error: {e}")
            return False

    def has(self, key: str) -> bool:
        return self._read(key) is not None

    def forget(self, key: str) -> bool:
        path = self._key_path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def flush(self) -> bool:
        import shutil
        try:
            shutil.rmtree(self._path)
            os.makedirs(self._path, exist_ok=True)
            return True
        except Exception:
            return False

    def increment(self, key: str, value: int = 1) -> int:
        current = self.get(key) or 0
        new_val = int(current) + value
        self.put(key, new_val)
        return new_val

    def decrement(self, key: str, value: int = 1) -> int:
        return self.increment(key, -value)

    def touch(self, key: str, seconds: int) -> bool:
        """
        [ID] Perpanjang TTL dengan membaca-ulang metadata file lalu menulis
        kembali field `expires_at` saja — value yang sudah ter-unpickle tidak
        di-deserialize ulang lewat get(), cukup dipindahkan apa adanya.
        [EN] Extend TTL by re-reading the file's metadata and rewriting only
        the `expires_at` field — the already-unpickled value is carried over
        as-is rather than being re-deserialized through get().
        """
        data = self._read(key)
        if data is None:
            return False
        data['expires_at'] = time.time() + seconds
        path = self._key_path(key)
        try:
            with open(path, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            logger.error(f"Cache touch error: {e}")
            return False


class RedisDriver(CacheDriver):
    """Redis-backed cache driver."""

    def __init__(self, host: str = None, port: int = None,
                 password: str = None, db: int = 1, prefix: str = ''):
        import redis
        self._redis = redis.Redis(
            host=host or os.getenv('REDIS_HOST', '127.0.0.1'),
            port=int(port or os.getenv('REDIS_PORT', 6379)),
            password=password or os.getenv('REDIS_PASSWORD') or None,
            db=db,
            decode_responses=False,
        )
        self._prefix = prefix or os.getenv('CACHE_PREFIX', 'laraflask_cache:')

    def _k(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        data = self._redis.get(self._k(key))
        if data is None:
            return None
        try:
            return pickle.loads(data)
        except Exception:
            return data.decode() if isinstance(data, bytes) else data

    def put(self, key: str, value: Any, seconds: int = None) -> bool:
        serialized = pickle.dumps(value)
        if seconds:
            return bool(self._redis.setex(self._k(key), seconds, serialized))
        return bool(self._redis.set(self._k(key), serialized))

    def has(self, key: str) -> bool:
        return bool(self._redis.exists(self._k(key)))

    def forget(self, key: str) -> bool:
        return bool(self._redis.delete(self._k(key)))

    def flush(self) -> bool:
        keys = self._redis.keys(f"{self._prefix}*")
        if keys:
            self._redis.delete(*keys)
        return True

    def increment(self, key: str, value: int = 1) -> int:
        return int(self._redis.incrby(self._k(key), value))

    def decrement(self, key: str, value: int = 1) -> int:
        return int(self._redis.decrby(self._k(key), value))

    def expire(self, key: str, seconds: int) -> bool:
        return bool(self._redis.expire(self._k(key), seconds))

    def touch(self, key: str, seconds: int) -> bool:
        """Native single round-trip TTL extension via Redis' EXPIRE command."""
        return self.expire(key, seconds)

    def ttl(self, key: str) -> int:
        return self._redis.ttl(self._k(key))


class ArrayDriver(CacheDriver):
    """In-memory array cache (not persistent between requests)."""

    def __init__(self):
        self._store: Dict[str, Dict] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.get('expires_at') and time.time() > entry['expires_at']:
            del self._store[key]
            return None
        return entry['value']

    def put(self, key: str, value: Any, seconds: int = None) -> bool:
        self._store[key] = {
            'value': value,
            'expires_at': (time.time() + seconds) if seconds else None,
        }
        return True

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def forget(self, key: str) -> bool:
        return bool(self._store.pop(key, None))

    def flush(self) -> bool:
        self._store.clear()
        return True

    def increment(self, key: str, value: int = 1) -> int:
        current = self.get(key) or 0
        new_val = int(current) + value
        self.put(key, new_val)
        return new_val

    def decrement(self, key: str, value: int = 1) -> int:
        return self.increment(key, -value)

    def touch(self, key: str, seconds: int) -> bool:
        """Extend TTL in-place by mutating the stored entry's `expires_at` only."""
        entry = self._store.get(key)
        if entry is None:
            return False
        entry['expires_at'] = time.time() + seconds
        return True


class DatabaseDriver(CacheDriver):
    """Database-backed cache driver."""

    TABLE = 'cache'

    def get(self, key: str) -> Optional[Any]:
        from laraflask.orm.db import DB
        rows = DB.select(
            f"SELECT value, expires_at FROM {self.TABLE} WHERE key = :key",
            {'key': key}
        )
        if not rows:
            return None
        row = rows[0]
        if row['expires_at'] and time.time() > float(row['expires_at']):
            self.forget(key)
            return None
        try:
            return pickle.loads(row['value'])
        except Exception:
            return row['value']

    def put(self, key: str, value: Any, seconds: int = None) -> bool:
        from laraflask.orm.db import DB
        expires_at = (time.time() + seconds) if seconds else None
        serialized = pickle.dumps(value)

        DB.delete(f"DELETE FROM {self.TABLE} WHERE key = :key", {'key': key})
        DB.insert(
            f"INSERT INTO {self.TABLE} (key, value, expires_at) VALUES (:key, :value, :exp)",
            {'key': key, 'value': serialized, 'exp': expires_at}
        )
        return True

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def forget(self, key: str) -> bool:
        from laraflask.orm.db import DB
        return bool(DB.delete(f"DELETE FROM {self.TABLE} WHERE key = :key", {'key': key}))

    def flush(self) -> bool:
        from laraflask.orm.db import DB
        DB.delete(f"DELETE FROM {self.TABLE}")
        return True

    def increment(self, key: str, value: int = 1) -> int:
        current = self.get(key) or 0
        new_val = int(current) + value
        self.put(key, new_val)
        return new_val

    def decrement(self, key: str, value: int = 1) -> int:
        return self.increment(key, -value)

    def touch(self, key: str, seconds: int) -> bool:
        """
        [ID] Perpanjang TTL lewat satu statement `UPDATE` pada kolom
        `expires_at` saja — tidak ada SELECT untuk mengambil value, dan
        tidak ada unpickle/serialize ulang.
        [EN] Extend TTL via a single `UPDATE` statement touching only the
        `expires_at` column — no SELECT to fetch the value, and no
        unpickle/re-serialize round trip.
        """
        from laraflask.orm.db import DB
        new_expires_at = time.time() + seconds
        affected = DB.update(
            f"UPDATE {self.TABLE} SET expires_at = :exp WHERE key = :key",
            {'exp': new_expires_at, 'key': key}
        )
        return bool(affected)


# ─── Cache Manager ────────────────────────────────────────────────────────────

class Cache:
    """
    Cache facade — unified interface to multiple cache drivers.
    Works like Laravel's Cache facade.
    """

    _stores: Dict[str, CacheDriver] = {}
    _default: str = 'file'
    _prefix: str = ''

    @classmethod
    def configure(cls, default: str = 'file', prefix: str = ''):
        cls._default = default
        cls._prefix = prefix

    @classmethod
    def store(cls, name: str = None) -> CacheDriver:
        name = name or cls._default
        if name not in cls._stores:
            cls._stores[name] = cls._make_driver(name)
        return cls._stores[name]

    @classmethod
    def _make_driver(cls, name: str) -> CacheDriver:
        if name == 'file':
            return FileDriver()
        elif name == 'redis':
            return RedisDriver()
        elif name == 'array' or name == 'memory':
            return ArrayDriver()
        elif name == 'database':
            return DatabaseDriver()
        raise ValueError(f"Unknown cache driver [{name}]")

    @classmethod
    def _key(cls, key: str) -> str:
        return f"{cls._prefix}{key}" if cls._prefix else key

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        value = cls.store().get(cls._key(key))
        if value is None:
            return default() if callable(default) else default
        return value

    @classmethod
    def put(cls, key: str, value: Any, seconds: int = None) -> bool:
        return cls.store().put(cls._key(key), value, seconds)

    @classmethod
    def set(cls, key: str, value: Any, seconds: int = None) -> bool:
        return cls.put(key, value, seconds)

    @classmethod
    def add(cls, key: str, value: Any, seconds: int = None) -> bool:
        """Store if not already present."""
        if cls.has(key):
            return False
        return cls.put(key, value, seconds)

    @classmethod
    def forever(cls, key: str, value: Any) -> bool:
        return cls.put(key, value, None)

    @classmethod
    def remember(cls, key: str, seconds: int, callback: Callable) -> Any:
        """Get cached value, or store the result of callback."""
        value = cls.get(key)
        if value is None:
            value = callback()
            cls.put(key, value, seconds)
        return value

    @classmethod
    def remember_forever(cls, key: str, callback: Callable) -> Any:
        value = cls.get(key)
        if value is None:
            value = callback()
            cls.forever(key, value)
        return value

    @classmethod
    def pull(cls, key: str, default: Any = None) -> Any:
        """Get and delete a cached value."""
        value = cls.get(key, default)
        cls.forget(key)
        return value

    @classmethod
    def has(cls, key: str) -> bool:
        return cls.store().has(cls._key(key))

    @classmethod
    def missing(cls, key: str) -> bool:
        return not cls.has(key)

    @classmethod
    def forget(cls, key: str) -> bool:
        return cls.store().forget(cls._key(key))

    @classmethod
    def touch(cls, key: str, seconds: int) -> bool:
        """
        [ID] Perpanjang TTL sebuah key tanpa mengambil-ulang valuenya — hanya
        satu round-trip ke storage backend (bukan get() lalu put()).
        Mirip `Cache::touch()` di Laravel 13.

        [EN] Extend a key's TTL without re-fetching its value — a single
        round-trip to the storage backend (not get() then put()). Mirrors
        Laravel 13's `Cache::touch()`.
        """
        return cls.store().touch(cls._key(key), seconds)

    @classmethod
    def flush(cls) -> bool:
        return cls.store().flush()

    @classmethod
    def clear(cls) -> bool:
        return cls.flush()

    @classmethod
    def increment(cls, key: str, value: int = 1) -> int:
        return cls.store().increment(cls._key(key), value)

    @classmethod
    def decrement(cls, key: str, value: int = 1) -> int:
        return cls.store().decrement(cls._key(key), value)

    @classmethod
    def many(cls, keys: List[str]) -> Dict[str, Any]:
        return {key: cls.get(key) for key in keys}

    @classmethod
    def put_many(cls, values: Dict[str, Any], seconds: int = None) -> bool:
        return all(cls.put(key, val, seconds) for key, val in values.items())

    @classmethod
    def tags(cls, *tags: str) -> 'TaggedCache':
        return TaggedCache(cls.store(), list(tags))


class TaggedCache:
    """Cache with tag-based invalidation."""

    def __init__(self, driver: CacheDriver, tags: List[str]):
        self._driver = driver
        self._tags = tags

    def _tag_prefix(self) -> str:
        return ':'.join(sorted(self._tags)) + ':'

    def get(self, key: str, default: Any = None) -> Any:
        return self._driver.get(self._tag_prefix() + key) or default

    def put(self, key: str, value: Any, seconds: int = None) -> bool:
        return self._driver.put(self._tag_prefix() + key, value, seconds)

    def forget(self, key: str) -> bool:
        return self._driver.forget(self._tag_prefix() + key)

    def flush(self) -> bool:
        """Flush all keys with the tag prefix."""
        # Note: Redis driver supports pattern deletion
        if hasattr(self._driver, '_redis'):
            prefix = self._driver._prefix + self._tag_prefix()
            keys = self._driver._redis.keys(f"{prefix}*")
            if keys:
                self._driver._redis.delete(*keys)
        return True

    def remember(self, key: str, seconds: int, callback: Callable) -> Any:
        value = self.get(key)
        if value is None:
            value = callback()
            self.put(key, value, seconds)
        return value
