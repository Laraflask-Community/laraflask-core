"""
Shared test configuration and fixtures for laraflask-core test suite.

Mocks flask, sqlalchemy, and other optional dependencies so that
laraflask modules can be imported in isolation without those packages
being installed.
"""

import sys
import os
from unittest.mock import MagicMock

# Ensure the project root is on sys.path so `import laraflask` resolves.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Mock heavy external dependencies that are not installed in CI/test env.
# ---------------------------------------------------------------------------

_MOCKED_MODULES = [
    "flask",
    "flask.globals",
    "flask.helpers",
    "flask.wrappers",
    "flask.sessions",
    "flask.ctx",
    "flask_cors",
    "flask_session",
    "flask_socketio",
    "flask_debugtoolbar",
    "sqlalchemy",
    "sqlalchemy.orm",
    "sqlalchemy.ext",
    "sqlalchemy.ext.declarative",
    "sqlalchemy.engine",
    "sqlalchemy.types",
    "sqlalchemy.schema",
    "alembic",
    "alembic.config",
    "alembic.command",
    "redis",
    "celery",
    "bcrypt",
    "jwt",
    "cryptography",
    "boto3",
    "twilio",
    "werkzeug",
    "werkzeug.security",
    "werkzeug.exceptions",
    "werkzeug.routing",
    "jinja2",
    "click",
    "dotenv",
    "apscheduler",
]

for mod_name in _MOCKED_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Make croniter raise ImportError so that the scheduler's fallback
# _field_match logic is exercised instead of returning MagicMock objects.
# Also make email_validator raise ImportError so the regex fallback is used.
_IMPORT_ERROR_MODULES = [
    "croniter",
    "email_validator",
]


def _make_fail_import(module_name):
    """Create a module-like object that raises ImportError on attribute access."""
    class _FailImport:
        def __getattr__(self, name):
            raise ImportError(f"No module named '{module_name}'")
    return _FailImport()


for mod_name in _IMPORT_ERROR_MODULES:
    sys.modules[mod_name] = _make_fail_import(mod_name)
