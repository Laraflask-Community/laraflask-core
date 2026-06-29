"""
Laraflask Testing Utilities
Laravel-inspired test helpers for unit, feature, and integration tests.
"""

from __future__ import annotations
import json
import unittest
from typing import Any, Dict, List, Optional, Type, Union
from flask.testing import FlaskClient
from flask import Response


class TestCase(unittest.TestCase):
    """
    Base test case for all Laraflask tests.
    Provides setUp/tearDown lifecycle and test helpers.
    """

    _app = None
    _client: Optional[FlaskClient] = None
    _response: Optional[Response] = None

    @classmethod
    def setUpClass(cls):
        """Set up the test application once per test class."""
        from laraflask.core.application import Application
        import os
        os.environ['APP_ENV'] = 'testing'
        os.environ['DB_CONNECTION'] = 'sqlite'
        os.environ['DB_DATABASE'] = ':memory:'

        cls._app = Application(os.getcwd())
        cls._app.bootstrap()

    def setUp(self):
        """Called before each test method."""
        self._client = self.__class__._app.get_flask().test_client()
        self._client.__enter__()
        self._response = None
        self.before_each()

    def tearDown(self):
        """Called after each test method."""
        self._client.__exit__(None, None, None)
        self.after_each()

    def before_each(self):
        """Override to run code before each test."""
        pass

    def after_each(self):
        """Override to run code after each test."""
        pass

    # ─── HTTP Helpers ─────────────────────────────────────────────────────────

    def get(self, uri: str, headers: Dict = None, **kwargs) -> 'TestResponse':
        response = self._client.get(uri, headers=headers or {}, **kwargs)
        self._response = TestResponse(response)
        return self._response

    def post(self, uri: str, data: Dict = None,
             json: Dict = None, headers: Dict = None, **kwargs) -> 'TestResponse':
        h = headers or {}
        if json is not None:
            h['Content-Type'] = 'application/json'
            response = self._client.post(uri, json=json, headers=h, **kwargs)
        else:
            response = self._client.post(uri, data=data or {}, headers=h, **kwargs)
        self._response = TestResponse(response)
        return self._response

    def put(self, uri: str, data: Dict = None,
            json: Dict = None, headers: Dict = None, **kwargs) -> 'TestResponse':
        h = headers or {}
        if json is not None:
            h['Content-Type'] = 'application/json'
            response = self._client.put(uri, json=json, headers=h, **kwargs)
        else:
            response = self._client.put(uri, data=data or {}, headers=h, **kwargs)
        self._response = TestResponse(response)
        return self._response

    def patch(self, uri: str, data: Dict = None,
              json: Dict = None, headers: Dict = None, **kwargs) -> 'TestResponse':
        h = headers or {}
        if json is not None:
            h['Content-Type'] = 'application/json'
            response = self._client.patch(uri, json=json, headers=h, **kwargs)
        else:
            response = self._client.patch(uri, data=data or {}, headers=h, **kwargs)
        self._response = TestResponse(response)
        return self._response

    def delete(self, uri: str, headers: Dict = None, **kwargs) -> 'TestResponse':
        response = self._client.delete(uri, headers=headers or {}, **kwargs)
        self._response = TestResponse(response)
        return self._response

    def call(self, method: str, uri: str, data: Dict = None,
             headers: Dict = None) -> 'TestResponse':
        method_fn = getattr(self._client, method.lower())
        response = method_fn(uri, data=data, headers=headers or {})
        self._response = TestResponse(response)
        return self._response

    # ─── Auth Helpers ─────────────────────────────────────────────────────────

    def acting_as(self, user: Any, guard: str = None) -> 'TestCase':
        """Log in as the given user for the request."""
        from laraflask.auth.auth import Auth
        with self._client.session_transaction() as sess:
            sess['user_id'] = getattr(user, 'id', None)
            sess['_token'] = 'test-csrf-token'
        return self

    def acting_as_api(self, user: Any) -> 'TestCase':
        """Set API authentication token."""
        from laraflask.auth.auth import JWT
        jwt = JWT()
        token = jwt.encode({
            'sub': str(getattr(user, 'id', 1)),
            'email': getattr(user, 'email', 'test@example.com'),
        })
        self._api_token = token
        return self

    def with_token(self, token: str) -> 'TestCase':
        self._api_token = token
        return self

    def be(self, user: Any) -> 'TestCase':
        """Alias for acting_as."""
        return self.acting_as(user)

    # ─── Database Helpers ─────────────────────────────────────────────────────

    def assert_database_has(self, table: str, data: Dict) -> 'TestCase':
        from laraflask.orm.db import DB
        clauses = ' AND '.join(f"{k} = :{k}" for k in data.keys())
        result = DB.select(f"SELECT COUNT(*) as cnt FROM {table} WHERE {clauses}", data)
        self.assertGreater(result[0]['cnt'], 0,
                           f"Table [{table}] does not contain expected data: {data}")
        return self

    def assert_database_missing(self, table: str, data: Dict) -> 'TestCase':
        from laraflask.orm.db import DB
        clauses = ' AND '.join(f"{k} = :{k}" for k in data.keys())
        result = DB.select(f"SELECT COUNT(*) as cnt FROM {table} WHERE {clauses}", data)
        self.assertEqual(result[0]['cnt'], 0,
                         f"Table [{table}] unexpectedly contains data: {data}")
        return self

    def assert_database_count(self, table: str, count: int) -> 'TestCase':
        from laraflask.orm.db import DB
        result = DB.select(f"SELECT COUNT(*) as cnt FROM {table}")
        self.assertEqual(result[0]['cnt'], count,
                         f"Table [{table}] has {result[0]['cnt']} rows, expected {count}")
        return self

    def refresh_database(self) -> 'TestCase':
        """Reset database between tests."""
        from laraflask.orm.db import DB
        from laraflask.orm.migration import Migrator
        DB.drop_all()
        migrator = Migrator('database/migrations')
        migrator.run()
        return self

    # ─── Factory Helpers ──────────────────────────────────────────────────────

    def create(self, model_class: Type, **attributes) -> Any:
        """Create and persist a model instance."""
        return model_class.create(**attributes)

    def make(self, model_class: Type, **attributes) -> Any:
        """Create a model instance without persisting."""
        return model_class(**attributes)

    # ─── Event / Notification Mocking ────────────────────────────────────────

    def fake_events(self) -> 'EventFake':
        fake = EventFake()
        from laraflask.events.dispatcher import Events
        Events._dispatcher = fake
        return fake

    def fake_queue(self) -> 'QueueFake':
        fake = QueueFake()
        from laraflask.queue.queue import Queue
        Queue._connections['default'] = fake
        return fake

    def fake_notifications(self) -> 'NotificationFake':
        fake = NotificationFake()
        return fake

    def fake_storage(self) -> 'StorageFake':
        fake = StorageFake()
        from laraflask.storage.storage import Storage
        Storage._disks['local'] = fake
        return fake

    def fake_mail(self) -> 'MailFake':
        return MailFake()


class TestResponse:
    """Wraps Flask test response with assertion helpers."""

    def __init__(self, response: Response):
        self._response = response
        self._json: Optional[Dict] = None

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def json(self) -> Optional[Dict]:
        if self._json is None:
            try:
                self._json = json.loads(self._response.data)
            except Exception:
                self._json = {}
        return self._json

    @property
    def data(self) -> bytes:
        return self._response.data

    @property
    def text(self) -> str:
        return self._response.data.decode('utf-8')

    @property
    def headers(self) -> Dict:
        return dict(self._response.headers)

    def assert_status(self, status: int) -> 'TestResponse':
        assert self.status_code == status, \
            f"Expected status {status}, got {self.status_code}. Body: {self.text[:200]}"
        return self

    def assert_ok(self) -> 'TestResponse':
        return self.assert_status(200)

    def assert_created(self) -> 'TestResponse':
        return self.assert_status(201)

    def assert_no_content(self) -> 'TestResponse':
        return self.assert_status(204)

    def assert_not_found(self) -> 'TestResponse':
        return self.assert_status(404)

    def assert_forbidden(self) -> 'TestResponse':
        return self.assert_status(403)

    def assert_unauthorized(self) -> 'TestResponse':
        return self.assert_status(401)

    def assert_unprocessable(self) -> 'TestResponse':
        return self.assert_status(422)

    def assert_redirect(self, url: str = None) -> 'TestResponse':
        assert self.status_code in (301, 302, 303, 307, 308), \
            f"Expected redirect, got {self.status_code}"
        if url:
            assert url in self._response.headers.get('Location', ''), \
                f"Expected redirect to [{url}]"
        return self

    def assert_json(self, expected: Dict) -> 'TestResponse':
        actual = self.json
        for key, value in expected.items():
            assert key in actual, f"Key [{key}] not found in JSON response"
            assert actual[key] == value, \
                f"JSON key [{key}]: expected {value!r}, got {actual[key]!r}"
        return self

    def assert_json_path(self, path: str, value: Any) -> 'TestResponse':
        """Assert a nested JSON value using dot notation."""
        keys = path.split('.')
        data = self.json
        for key in keys:
            data = data.get(key) if isinstance(data, dict) else None
        assert data == value, f"JSON path [{path}]: expected {value!r}, got {data!r}"
        return self

    def assert_json_structure(self, structure: List[str]) -> 'TestResponse':
        data = self.json
        if 'data' in data:
            data = data['data']
        for key in structure:
            assert key in data, f"Expected key [{key}] in JSON response"
        return self

    def assert_json_count(self, key: str, count: int) -> 'TestResponse':
        data = self.json.get(key, [])
        assert len(data) == count, \
            f"Expected {count} items in [{key}], got {len(data)}"
        return self

    def assert_header(self, key: str, value: str = None) -> 'TestResponse':
        assert key in self.headers, f"Header [{key}] not found in response"
        if value:
            assert self.headers[key] == value, \
                f"Header [{key}]: expected {value!r}, got {self.headers[key]!r}"
        return self

    def assert_cookie(self, name: str) -> 'TestResponse':
        cookies = self._response.headers.getlist('Set-Cookie')
        assert any(name in c for c in cookies), \
            f"Cookie [{name}] not found in response"
        return self

    def assert_see(self, text: str) -> 'TestResponse':
        assert text in self.text, f"Text [{text}] not found in response"
        return self

    def assert_dont_see(self, text: str) -> 'TestResponse':
        assert text not in self.text, f"Text [{text}] unexpectedly found in response"
        return self

    def assert_success(self) -> 'TestResponse':
        """Assert API success response."""
        return self.assert_ok().assert_json({'success': True})

    def dump(self) -> 'TestResponse':
        print(f"\nStatus: {self.status_code}")
        print(f"Body: {self.text[:500]}")
        return self

    # Allow chaining with unittest assertions
    def __getattr__(self, name: str) -> Any:
        raise AttributeError(f"TestResponse has no assertion [{name}]")


# ─── Fakes ────────────────────────────────────────────────────────────────────

class EventFake:
    """Fake event dispatcher for testing."""

    def __init__(self):
        self._dispatched: List[Any] = []
        self._listeners: Dict = {}

    def dispatch(self, event: Any, payload: Any = None) -> List:
        self._dispatched.append(event)
        return []

    def listen(self, event: Any, listener: Any):
        pass

    def assert_dispatched(self, event_class: Type, times: int = None) -> 'EventFake':
        dispatched = [e for e in self._dispatched if isinstance(e, event_class)]
        if times is not None:
            assert len(dispatched) == times, \
                f"Event [{event_class.__name__}] dispatched {len(dispatched)} times, expected {times}"
        else:
            assert dispatched, f"Event [{event_class.__name__}] was not dispatched"
        return self

    def assert_not_dispatched(self, event_class: Type) -> 'EventFake':
        dispatched = [e for e in self._dispatched if isinstance(e, event_class)]
        assert not dispatched, f"Event [{event_class.__name__}] was unexpectedly dispatched"
        return self

    def assert_nothing_dispatched(self) -> 'EventFake':
        assert not self._dispatched, f"Events were dispatched: {self._dispatched}"
        return self


class QueueFake:
    """Fake queue driver for testing."""

    def __init__(self):
        self._pushed: List[Any] = []

    def push(self, job: Any, queue: str = 'default', delay: int = 0) -> str:
        self._pushed.append({'job': job, 'queue': queue, 'delay': delay})
        return 'fake-id'

    def later(self, delay: int, job: Any, queue: str = 'default') -> str:
        return self.push(job, queue, delay)

    def pop(self, queue: str = 'default'): return None
    def delete(self, message): pass
    def release(self, message, delay=0): pass
    def size(self, queue='default'): return len(self._pushed)
    def clear(self, queue='default'): self._pushed.clear(); return 0

    def assert_pushed(self, job_class: Type, times: int = None) -> 'QueueFake':
        jobs = [p for p in self._pushed if isinstance(p['job'], job_class)]
        if times is not None:
            assert len(jobs) == times, \
                f"Job [{job_class.__name__}] pushed {len(jobs)} times, expected {times}"
        else:
            assert jobs, f"Job [{job_class.__name__}] was not pushed to queue"
        return self

    def assert_not_pushed(self, job_class: Type) -> 'QueueFake':
        jobs = [p for p in self._pushed if isinstance(p['job'], job_class)]
        assert not jobs, f"Job [{job_class.__name__}] was unexpectedly pushed to queue"
        return self

    def assert_nothing_pushed(self) -> 'QueueFake':
        assert not self._pushed, f"Jobs were pushed: {self._pushed}"
        return self


class NotificationFake:
    """Fake notification sender for testing."""

    def __init__(self):
        self._sent: List[Dict] = []

    def send(self, notifiable: Any, notification: Any) -> None:
        self._sent.append({'notifiable': notifiable, 'notification': notification})

    def assert_sent_to(self, notifiable: Any, notification_class: Type) -> 'NotificationFake':
        sent = [s for s in self._sent
                if s['notifiable'] == notifiable
                and isinstance(s['notification'], notification_class)]
        assert sent, f"Notification [{notification_class.__name__}] was not sent to [{notifiable}]"
        return self

    def assert_not_sent_to(self, notifiable: Any, notification_class: Type) -> 'NotificationFake':
        sent = [s for s in self._sent
                if s['notifiable'] == notifiable
                and isinstance(s['notification'], notification_class)]
        assert not sent, f"Notification [{notification_class.__name__}] was unexpectedly sent"
        return self

    def assert_nothing_sent(self) -> 'NotificationFake':
        assert not self._sent, f"Notifications were sent: {self._sent}"
        return self


class StorageFake:
    """Fake in-memory storage for testing."""

    def __init__(self):
        self._files: Dict[str, bytes] = {}

    def exists(self, path: str) -> bool: return path in self._files
    def missing(self, path: str) -> bool: return path not in self._files
    def get(self, path: str): return self._files.get(path)
    def put(self, path: str, contents, options=None):
        if isinstance(contents, str):
            contents = contents.encode()
        self._files[path] = contents
        return True
    def delete(self, path):
        if isinstance(path, list):
            for p in path: self._files.pop(p, None)
        else:
            self._files.pop(path, None)
        return True
    def url(self, path: str): return f"/storage/{path}"
    def size(self, path: str): return len(self._files.get(path, b''))
    def files(self, directory=''): return [k for k in self._files if k.startswith(directory)]
    def directories(self, directory=''): return []
    def make_directory(self, path): return True
    def delete_directory(self, directory): return True
    def copy(self, from_, to): self._files[to] = self._files.get(from_, b''); return True
    def move(self, from_, to): self.copy(from_, to); self.delete(from_); return True

    def assert_exists(self, path: str) -> 'StorageFake':
        assert path in self._files, f"File [{path}] not found in storage"
        return self

    def assert_missing(self, path: str) -> 'StorageFake':
        assert path not in self._files, f"File [{path}] unexpectedly found in storage"
        return self


class MailFake:
    """Fake mail sender for testing."""

    def __init__(self):
        self._sent: List[Dict] = []

    def send(self, to: str, subject: str, body: str) -> bool:
        self._sent.append({'to': to, 'subject': subject, 'body': body})
        return True

    def assert_sent(self, to: str = None, subject: str = None) -> 'MailFake':
        filtered = self._sent
        if to: filtered = [m for m in filtered if m['to'] == to]
        if subject: filtered = [m for m in filtered if subject in m['subject']]
        assert filtered, f"No mail sent matching criteria"
        return self

    def assert_nothing_sent(self) -> 'MailFake':
        assert not self._sent, f"Mails were sent: {self._sent}"
        return self


# ─── Feature Test Base ────────────────────────────────────────────────────────

class FeatureTestCase(TestCase):
    """
    Feature test case — tests full HTTP stack including routes, middleware.
    """
    pass


class UnitTestCase(unittest.TestCase):
    """
    Unit test case — no application bootstrapping.
    Pure unit tests for isolated components.
    """

    def setUp(self):
        self.before_each()

    def tearDown(self):
        self.after_each()

    def before_each(self):
        pass

    def after_each(self):
        pass
