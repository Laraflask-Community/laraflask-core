"""
Laraflask Core Service Providers
Bootstraps all framework services: DB, Cache, Auth, Queue, Events, etc.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from laraflask.core.application import Application


class ServiceProvider:
    """Base class for all service providers."""

    def __init__(self, app: 'Application'):
        self.app = app

    def register(self) -> None:
        """Register bindings into the container."""
        pass

    def boot(self) -> None:
        """Bootstrap any application services."""
        pass

    def provides(self) -> list:
        """Get the services provided by the provider."""
        return []

    def when(self) -> list:
        """Get the events that trigger deferred loading."""
        return []


class RouteServiceProvider(ServiceProvider):
    """Register routing services."""

    def register(self):
        pass

    def boot(self):
        pass


class DatabaseServiceProvider(ServiceProvider):
    """Register database services."""

    def register(self):
        self.app.singleton('db', self._make_db)

    def boot(self):
        db = self.app.make('db')
        db_url = self.app._flask.config.get('SQLALCHEMY_DATABASE_URI')
        if db_url:
            try:
                db.connect(url=db_url)
            except Exception as e:
                import logging
                logging.getLogger('laraflask').warning(f"DB connect failed: {e}")

    def _make_db(self, app):
        from laraflask.orm.db import DB
        return DB


class CacheServiceProvider(ServiceProvider):
    """Register cache services."""

    def register(self):
        self.app.singleton('cache', self._make_cache)

    def boot(self):
        from laraflask.cache.cache import Cache
        driver = self.app._config.get('cache.default', 'file') if self.app._config else 'file'
        prefix = self.app._config.get('cache.prefix', '') if self.app._config else ''
        Cache.configure(default=driver, prefix=prefix)

    def _make_cache(self, app):
        from laraflask.cache.cache import Cache
        return Cache


class SessionServiceProvider(ServiceProvider):
    """Register session services."""

    def register(self):
        pass

    def boot(self):
        import os
        flask_app = self.app._flask
        flask_app.config['SESSION_TYPE'] = os.getenv('SESSION_DRIVER', 'filesystem')
        flask_app.config['SESSION_FILE_DIR'] = os.path.join(
            self.app.storage_path(), 'framework', 'sessions'
        )
        flask_app.config['SESSION_PERMANENT'] = False
        flask_app.config['SESSION_USE_SIGNER'] = True
        flask_app.config['PERMANENT_SESSION_LIFETIME'] = int(
            os.getenv('SESSION_LIFETIME', 120)
        ) * 60

        try:
            from flask_session import Session
            Session(flask_app)
        except ImportError:
            pass  # Flask-Session optional; fall back to cookie sessions


class AuthServiceProvider(ServiceProvider):
    """Register authentication services."""

    def register(self):
        self.app.singleton('auth', self._make_auth)
        self.app.singleton('gate', self._make_gate)

    def boot(self):
        from laraflask.auth.auth import Auth, Gate
        Auth.configure(
            guards={
                'web': {'driver': 'session', 'provider': 'users'},
                'api': {'driver': 'jwt', 'provider': 'users'},
            },
            default='web',
        )

        # Register Gate abilities
        self._define_abilities(Gate)

    def _make_auth(self, app):
        from laraflask.auth.auth import Auth
        return Auth

    def _make_gate(self, app):
        from laraflask.auth.auth import Gate
        return Gate

    def _define_abilities(self, Gate):
        """Register application abilities. Override in app/Providers/AuthServiceProvider.py"""
        pass


class ValidationServiceProvider(ServiceProvider):
    """Register validation services."""

    def register(self):
        self.app.singleton('validator', self._make_validator)

    def _make_validator(self, app):
        from laraflask.validation.validator import Validator
        return Validator


class EventServiceProvider(ServiceProvider):
    """Register event and listener services."""

    def register(self):
        self.app.singleton('events', self._make_dispatcher)

    def boot(self):
        from laraflask.events.dispatcher import Events
        self._register_listeners(Events)

    def _make_dispatcher(self, app):
        from laraflask.events.dispatcher import Events
        return Events

    def _register_listeners(self, Events):
        """Register event listeners. Override in app/Providers/EventServiceProvider.py"""
        pass


class QueueServiceProvider(ServiceProvider):
    """Register queue services."""

    def register(self):
        self.app.singleton('queue', self._make_queue)

    def boot(self):
        import os
        from laraflask.queue.queue import Queue
        Queue.configure(default=os.getenv('QUEUE_CONNECTION', 'sync'))

    def _make_queue(self, app):
        from laraflask.queue.queue import Queue
        return Queue


class NotificationServiceProvider(ServiceProvider):
    """Register notification services."""

    def register(self):
        self.app.singleton('notification', self._make_notification)

    def _make_notification(self, app):
        from laraflask.notifications.notification import NotificationSender
        return NotificationSender()


class StorageServiceProvider(ServiceProvider):
    """Register storage services."""

    def register(self):
        self.app.singleton('storage', self._make_storage)

    def boot(self):
        import os
        from laraflask.storage.storage import Storage
        Storage.configure(default=os.getenv('FILESYSTEM_DISK', 'local'))

        # Register public storage symlink route
        flask_app = self.app._flask
        storage_path = self.app.storage_path('app', 'public')
        public_path = self.app.public_path('storage')

        if not os.path.exists(public_path) and os.path.exists(storage_path):
            try:
                os.symlink(storage_path, public_path)
            except Exception:
                pass

    def _make_storage(self, app):
        from laraflask.storage.storage import Storage
        return Storage


class SchedulerServiceProvider(ServiceProvider):
    """Register the task scheduler."""

    def register(self):
        self.app.singleton('schedule', self._make_schedule)

    def _make_schedule(self, app):
        from laraflask.scheduler.schedule import Schedule
        return Schedule
