"""
Laraflask Queue System
Multi-driver queue with Redis, RabbitMQ, and Database backends.
"""

from __future__ import annotations
import os
import json
import time
import uuid
import datetime
import logging
import traceback
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger('laraflask.queue')


class Job:
    """
    Base class for all queue jobs.
    Override handle() to define job logic.
    """

    queue: str = 'default'
    tries: int = 3
    timeout: int = 60
    retry_after: int = 90
    delay: int = 0
    max_exceptions: int = 3
    backoff: int = 0

    def handle(self) -> None:
        raise NotImplementedError

    def failed(self, exception: Exception) -> None:
        """Called when all retries are exhausted."""
        logger.error(f"Job [{self.__class__.__name__}] failed: {exception}")

    def middleware(self) -> List:
        return []

    def retry_until(self) -> Optional[datetime.datetime]:
        return None

    def unique_id(self) -> Optional[str]:
        return None

    def tags(self) -> List[str]:
        return []

    def serialize(self) -> Dict:
        return {
            'job': f"{self.__class__.__module__}.{self.__class__.__name__}",
            'data': self.__dict__,
            'queue': self.queue,
            'tries': self.tries,
            'timeout': self.timeout,
        }

    @classmethod
    def deserialize(cls, data: Dict) -> 'Job':
        import importlib
        module_path, class_name = data['job'].rsplit('.', 1)
        module = importlib.import_module(module_path)
        job_class = getattr(module, class_name)
        job = job_class.__new__(job_class)
        for key, value in data.get('data', {}).items():
            setattr(job, key, value)
        return job


class Interruptible:
    """
    [ID] Mixin untuk Job yang ingin diberi kesempatan menyimpan state atau
    melepas lock sebelum worker benar-benar exit akibat sinyal penghentian
    (mis. SIGTERM dari supervisor/orchestrator). Worker akan memanggil
    `interrupted(signal)` pada job yang sedang berjalan begitu sinyal
    diterima, sebelum proses keluar.

    Contoh:
        class ProcessVideoJob(Job, Interruptible):
            def handle(self):
                self.lock = acquire_lock(...)
                ...

            def interrupted(self, signal):
                release_lock(self.lock)
                save_partial_progress(self)

    [EN] Mixin for Jobs that want a chance to save state or release a lock
    before the worker actually exits due to a termination signal (e.g.
    SIGTERM from a supervisor/orchestrator). The worker calls
    `interrupted(signal)` on the currently-running job as soon as the
    signal is received, before the process exits.
    """

    def interrupted(self, signal: int) -> None:
        """
        [ID] Dipanggil worker tepat sebelum exit karena sinyal penghentian.
        Override method ini untuk menyimpan progress, melepas lock, atau
        melakukan cleanup lain. Default tidak melakukan apa pun.

        [EN] Called by the worker right before exiting due to a termination
        signal. Override this to save progress, release a lock, or perform
        other cleanup. Defaults to a no-op.
        """
        pass


class QueueMessage:
    """Represents a message in the queue."""

    def __init__(self, id: str, body: Dict, queue: str = 'default',
                 attempts: int = 0, available_at: float = None):
        self.id = id
        self.body = body
        self.queue = queue
        self.attempts = attempts
        self.available_at = available_at or time.time()

    def is_available(self) -> bool:
        return time.time() >= self.available_at

    def increment_attempts(self):
        self.attempts += 1

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'body': self.body,
            'queue': self.queue,
            'attempts': self.attempts,
            'available_at': self.available_at,
        }


class QueueDriver(ABC):
    """Abstract queue driver interface."""

    @abstractmethod
    def push(self, job: Any, queue: str = 'default', delay: int = 0) -> str:
        pass

    @abstractmethod
    def later(self, delay: int, job: Any, queue: str = 'default') -> str:
        pass

    @abstractmethod
    def pop(self, queue: str = 'default') -> Optional[QueueMessage]:
        pass

    @abstractmethod
    def delete(self, message: QueueMessage) -> None:
        pass

    @abstractmethod
    def release(self, message: QueueMessage, delay: int = 0) -> None:
        pass

    @abstractmethod
    def size(self, queue: str = 'default') -> int:
        pass

    @abstractmethod
    def clear(self, queue: str = 'default') -> int:
        pass


class SyncDriver(QueueDriver):
    """Synchronous driver — runs jobs immediately (great for testing/development)."""

    def push(self, job: Any, queue: str = 'default', delay: int = 0) -> str:
        job_id = str(uuid.uuid4())
        if isinstance(job, Job):
            try:
                job.handle()
            except Exception as e:
                job.failed(e)
        return job_id

    def later(self, delay: int, job: Any, queue: str = 'default') -> str:
        return self.push(job, queue)

    def pop(self, queue: str = 'default') -> Optional[QueueMessage]:
        return None

    def delete(self, message: QueueMessage) -> None:
        pass

    def release(self, message: QueueMessage, delay: int = 0) -> None:
        pass

    def size(self, queue: str = 'default') -> int:
        return 0

    def clear(self, queue: str = 'default') -> int:
        return 0


class DatabaseDriver(QueueDriver):
    """Database-backed queue driver."""

    TABLE = 'jobs'
    FAILED_TABLE = 'failed_jobs'

    def push(self, job: Any, queue: str = 'default', delay: int = 0) -> str:
        from laraflask.orm.db import DB
        job_id = str(uuid.uuid4())
        available_at = time.time() + delay

        payload = json.dumps(job.serialize() if isinstance(job, Job) else job)

        DB.insert(
            f"INSERT INTO {self.TABLE} (id, queue, payload, attempts, available_at, created_at) "
            f"VALUES (:id, :queue, :payload, 0, :available_at, :created_at)",
            {
                'id': job_id,
                'queue': queue,
                'payload': payload,
                'available_at': available_at,
                'created_at': time.time(),
            }
        )
        return job_id

    def later(self, delay: int, job: Any, queue: str = 'default') -> str:
        return self.push(job, queue, delay)

    def pop(self, queue: str = 'default') -> Optional[QueueMessage]:
        from laraflask.orm.db import DB
        now = time.time()

        rows = DB.select(
            f"SELECT * FROM {self.TABLE} WHERE queue = :queue AND available_at <= :now "
            f"AND reserved_at IS NULL ORDER BY id LIMIT 1",
            {'queue': queue, 'now': now}
        )

        if not rows:
            return None

        row = rows[0]
        DB.update(
            f"UPDATE {self.TABLE} SET reserved_at = :now, attempts = attempts + 1 WHERE id = :id",
            {'now': now, 'id': row['id']}
        )

        return QueueMessage(
            id=row['id'],
            body=json.loads(row['payload']),
            queue=queue,
            attempts=row['attempts'] + 1,
            available_at=row['available_at'],
        )

    def delete(self, message: QueueMessage) -> None:
        from laraflask.orm.db import DB
        DB.delete(f"DELETE FROM {self.TABLE} WHERE id = :id", {'id': message.id})

    def release(self, message: QueueMessage, delay: int = 0) -> None:
        from laraflask.orm.db import DB
        DB.update(
            f"UPDATE {self.TABLE} SET reserved_at = NULL, available_at = :at WHERE id = :id",
            {'at': time.time() + delay, 'id': message.id}
        )

    def size(self, queue: str = 'default') -> int:
        from laraflask.orm.db import DB
        result = DB.select(
            f"SELECT COUNT(*) as cnt FROM {self.TABLE} WHERE queue = :q",
            {'q': queue}
        )
        return result[0]['cnt'] if result else 0

    def clear(self, queue: str = 'default') -> int:
        from laraflask.orm.db import DB
        return DB.delete(f"DELETE FROM {self.TABLE} WHERE queue = :q", {'q': queue})

    def fail(self, message: QueueMessage, exception: Exception) -> None:
        from laraflask.orm.db import DB
        DB.insert(
            f"INSERT INTO {self.FAILED_TABLE} (id, queue, payload, exception, failed_at) "
            f"VALUES (:id, :queue, :payload, :exc, :at)",
            {
                'id': str(uuid.uuid4()),
                'queue': message.queue,
                'payload': json.dumps(message.body),
                'exc': traceback.format_exc(),
                'at': time.time(),
            }
        )
        self.delete(message)


class RedisDriver(QueueDriver):
    """Redis-backed queue driver."""

    def __init__(self, host: str = None, port: int = None,
                 password: str = None, db: int = 0):
        import redis
        self._redis = redis.Redis(
            host=host or os.getenv('REDIS_HOST', '127.0.0.1'),
            port=int(port or os.getenv('REDIS_PORT', 6379)),
            password=password or os.getenv('REDIS_PASSWORD'),
            db=db,
            decode_responses=True,
        )
        self._prefix = os.getenv('REDIS_PREFIX', 'laraflask:queue:')

    def _queue_key(self, queue: str) -> str:
        return f"{self._prefix}{queue}"

    def _delayed_key(self, queue: str) -> str:
        return f"{self._prefix}{queue}:delayed"

    def push(self, job: Any, queue: str = 'default', delay: int = 0) -> str:
        job_id = str(uuid.uuid4())
        payload = json.dumps({
            'id': job_id,
            'body': job.serialize() if isinstance(job, Job) else job,
            'attempts': 0,
        })

        if delay > 0:
            score = time.time() + delay
            self._redis.zadd(self._delayed_key(queue), {payload: score})
        else:
            self._redis.rpush(self._queue_key(queue), payload)

        return job_id

    def later(self, delay: int, job: Any, queue: str = 'default') -> str:
        return self.push(job, queue, delay)

    def pop(self, queue: str = 'default') -> Optional[QueueMessage]:
        # Move ready delayed jobs first
        self._migrate_delayed(queue)

        data = self._redis.lpop(self._queue_key(queue))
        if not data:
            return None

        payload = json.loads(data)
        return QueueMessage(
            id=payload['id'],
            body=payload['body'],
            queue=queue,
            attempts=payload.get('attempts', 0),
        )

    def _migrate_delayed(self, queue: str):
        """Move delayed jobs that are ready into the main queue."""
        now = time.time()
        items = self._redis.zrangebyscore(self._delayed_key(queue), '-inf', now)
        for item in items:
            self._redis.zrem(self._delayed_key(queue), item)
            self._redis.rpush(self._queue_key(queue), item)

    def delete(self, message: QueueMessage) -> None:
        pass  # Redis LPOP already removes it

    def release(self, message: QueueMessage, delay: int = 0) -> None:
        self.push(message.body, message.queue, delay)

    def size(self, queue: str = 'default') -> int:
        return int(self._redis.llen(self._queue_key(queue)))

    def clear(self, queue: str = 'default') -> int:
        size = self.size(queue)
        self._redis.delete(self._queue_key(queue))
        return size


# ─── Queue Manager ────────────────────────────────────────────────────────────

class Queue:
    """
    Queue facade — push jobs to drivers with a simple interface.
    """

    _driver: Optional[QueueDriver] = None
    _connections: Dict[str, QueueDriver] = {}
    _default: str = 'sync'
    _routes: Dict[str, Dict[str, str]] = {}

    @classmethod
    def configure(cls, default: str = 'sync', connections: Dict = None):
        cls._default = default

    @classmethod
    def route(cls, job_class: Type['Job'], connection: str = None, queue: str = None) -> None:
        """
        [ID] Daftarkan secara terpusat connection/queue default untuk sebuah
        Job class, supaya tiap pemanggilan `dispatch()` tidak perlu mengatur
        `connection`/`queue` berulang-ulang. Biasanya dipanggil sekali di
        `QueueServiceProvider.boot()`. Contoh:
        `Queue.route(SendInvoiceJob, connection='redis', queue='high')`.

        [EN] Centrally register the default connection/queue for a Job
        class, so each `dispatch()` call doesn't need to repeat
        `connection`/`queue`. Typically called once in
        `QueueServiceProvider.boot()`. Example:
        `Queue.route(SendInvoiceJob, connection='redis', queue='high')`.
        """
        key = cls._job_key(job_class)
        route = cls._routes.setdefault(key, {})
        if connection is not None:
            route['connection'] = connection
        if queue is not None:
            route['queue'] = queue

    @classmethod
    def route_for(cls, job_class: Type['Job']) -> Dict[str, str]:
        """Get the registered route (connection/queue) for a Job class, if any."""
        return cls._routes.get(cls._job_key(job_class), {})

    @classmethod
    def _job_key(cls, job_class: Any) -> str:
        if isinstance(job_class, str):
            return job_class
        target = job_class if isinstance(job_class, type) else type(job_class)
        return f"{target.__module__}.{target.__name__}"

    @classmethod
    def connection(cls, name: str = None) -> QueueDriver:
        name = name or cls._default

        if name not in cls._connections:
            cls._connections[name] = cls._make_driver(name)

        return cls._connections[name]

    @classmethod
    def _make_driver(cls, name: str) -> QueueDriver:
        driver_map = {
            'sync':     SyncDriver,
            'database': DatabaseDriver,
            'redis':    RedisDriver,
        }
        driver_class = driver_map.get(name, SyncDriver)
        return driver_class()

    @classmethod
    def push(cls, job: Any, queue: str = 'default', delay: int = 0, connection: str = None) -> str:
        return cls.connection(connection).push(job, queue, delay)

    @classmethod
    def later(cls, delay: int, job: Any, queue: str = 'default', connection: str = None) -> str:
        return cls.connection(connection).later(delay, job, queue)

    @classmethod
    def dispatch(cls, job: Any) -> str:
        """
        [ID] Dispatch job ke queue. Jika class job sudah didaftarkan lewat
        `Queue.route()`, connection/queue dari route tersebut dipakai sebagai
        default — atribut `queue`/`delay` yang di-set langsung pada instance
        job (cara lama) tetap diutamakan kalau berbeda dari default kelas,
        sehingga tetap 100% backward compatible.

        [EN] Dispatch a job to the queue. If the job's class was registered
        via `Queue.route()`, that route's connection/queue is used as the
        default — attributes explicitly set on the job instance (the old
        way) still take priority when they differ from the class default,
        keeping this 100% backward compatible.
        """
        route = cls.route_for(type(job)) if not isinstance(job, str) else {}

        queue_name = getattr(job, 'queue', 'default')
        if route.get('queue') and queue_name == type(job).queue:
            # The job didn't override `queue` on the instance — use the routed default.
            queue_name = route['queue']

        connection_name = route.get('connection')

        return cls.push(job, queue_name, getattr(job, 'delay', 0), connection=connection_name)

    @classmethod
    def size(cls, queue: str = 'default') -> int:
        return cls.connection().size(queue)

    @classmethod
    def clear(cls, queue: str = 'default') -> int:
        return cls.connection().clear(queue)


# ─── Worker ───────────────────────────────────────────────────────────────────

class Worker:
    """
    Queue worker — processes jobs from the queue.
    Run with: python artisan.py queue:work

    [ID] Worker menangkap SIGTERM (dan SIGINT) secara graceful: begitu
    sinyal diterima, worker menyelesaikan iterasi loop saat ini, lalu kalau
    job yang sedang berjalan adalah instance `Interruptible`, method
    `interrupted(signal)` dipanggil sebelum worker benar-benar berhenti.

    [EN] The worker catches SIGTERM (and SIGINT) gracefully: once the
    signal arrives, the worker finishes the current loop iteration, and if
    the currently-running job is an `Interruptible` instance, its
    `interrupted(signal)` method is called before the worker actually
    stops.
    """

    def __init__(self, driver: QueueDriver, queue: str = 'default'):
        self._driver = driver
        self._queue = queue
        self._running = True
        self._processed = 0
        self._failed = 0
        self._current_job: Optional[Job] = None
        self._received_signal: Optional[int] = None

    def daemon(self, sleep: int = 3, max_jobs: int = 0, max_time: int = 0):
        """Run the worker as a daemon."""
        start_time = time.time()
        logger.info(f"Worker started on queue [{self._queue}]")
        self._register_signal_handlers()

        while self._running:
            if max_time and (time.time() - start_time) >= max_time:
                break
            if max_jobs and self._processed >= max_jobs:
                break

            message = self._driver.pop(self._queue)
            if message:
                self._process(message)
            else:
                time.sleep(sleep)

            if self._received_signal is not None:
                logger.info(f"Worker received signal {self._received_signal}, shutting down")
                break

        logger.info(f"Worker stopped. Processed: {self._processed}, Failed: {self._failed}")

    def _register_signal_handlers(self) -> None:
        """
        [ID] Daftarkan handler untuk SIGTERM/SIGINT. Handler hanya menandai
        flag dan, jika ada job yang sedang berjalan, langsung memanggil
        `interrupted()` pada job tersebut — bukan menghentikan proses secara
        paksa, supaya job punya kesempatan cleanup sebelum worker exit.

        [EN] Register handlers for SIGTERM/SIGINT. The handler only flags
        the shutdown intent and, if a job is currently running, immediately
        calls `interrupted()` on it — rather than forcibly killing the
        process, so the job gets a chance to clean up before the worker
        exits.
        """
        import signal as signal_module

        def handle_signal(sig, frame):
            self._received_signal = sig
            self._running = False

            if self._current_job is not None and isinstance(self._current_job, Interruptible):
                try:
                    self._current_job.interrupted(sig)
                except Exception as e:
                    logger.error(f"Error in interrupted() handler: {e}")

        try:
            signal_module.signal(signal_module.SIGTERM, handle_signal)
            signal_module.signal(signal_module.SIGINT, handle_signal)
        except ValueError:
            # signal() only works in the main thread — skip gracefully
            # if the worker is running inside a non-main thread (e.g. tests).
            logger.warning("Could not register signal handlers (not in main thread)")

    def _process(self, message: QueueMessage):
        job = None
        try:
            job_data = message.body
            job = Job.deserialize(job_data)
            self._current_job = job

            logger.debug(f"Processing job [{job.__class__.__name__}]")
            start = time.time()
            job.handle()
            elapsed = time.time() - start

            self._driver.delete(message)
            self._processed += 1
            logger.info(f"✓ Processed [{job.__class__.__name__}] in {elapsed:.2f}s")

        except Exception as e:
            self._failed += 1
            max_tries = message.body.get('tries', 3)

            if message.attempts >= max_tries:
                logger.error(f"Job failed after {message.attempts} attempts: {e}")
                if hasattr(self._driver, 'fail'):
                    self._driver.fail(message, e)
                if job is not None:
                    try:
                        job.failed(e)
                    except Exception:
                        pass
            else:
                delay = getattr(job, 'backoff', 30) if job is not None else 30
                self._driver.release(message, delay)
                logger.warning(f"Job released back to queue (attempt {message.attempts}/{max_tries})")
        finally:
            self._current_job = None

    def stop(self):
        self._running = False


def dispatch(job: Job) -> str:
    """Helper to dispatch a job to the queue."""
    return Queue.dispatch(job)


def dispatch_now(job: Job) -> None:
    """Execute a job immediately, bypassing the queue."""
    job.handle()
