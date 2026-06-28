# Laraflask Core v1.4.0

**A Laravel-inspired framework for Python — built on top of Flask + SQLAlchemy.**
Elegant. Expressive. Modern.

Laraflask brings Laravel's developer experience philosophy to the Python ecosystem: an Eloquent-style ORM, an Artisan CLI, a Service Container with dependency injection, Blade-like templating, a Job Queue, a Task Scheduler, and more than 20 other ready-to-use modules — all with an API that feels familiar to anyone who has ever written Laravel code.

## Installation

```bash
pip install laraflask-core
# or with all optional dependencies:
pip install laraflask-core[all]
```

## Changelog

### v1.4.0 (2026-06-28)
- Implemented 9 previously-missing Artisan generator commands: `make:request`, `make:policy`, `make:resource`, `make:rule`, `make:provider`, `make:seeder`, `make:factory`, `make:observer`, `make:command`
- `make:resource` supports `--jsonapi` to scaffold a `JsonApiResource` instead of the default `ApiResource`
- `make:policy` and `make:observer` support `--model` to generate type-hinted methods against a specific model
- Added 3 new base classes required by the generators above, since they didn't exist yet: `laraflask.orm.seeder.Seeder`, `laraflask.orm.factory.Factory` (Faker-backed), `laraflask.orm.observer.Observer`
- Added `Model.observe(ObserverClass)` — wires an `Observer` to the existing `ModelCreating`/`ModelCreated`/etc. lifecycle events without duplicating dispatch logic. Note: these lifecycle events still aren't dispatched automatically from `save()`/`delete()` — see the generated Observer's docstring for the manual-dispatch workaround
- Added 26 new unit tests covering every new command and base class
- Version bump: `1.3.0` → `1.4.0`

### v1.3.0 (2026-06-28)
- Eliminated all top-level `from flask import …` in user-space files (routes, Controller, Handler, tests)
- `Controller.respond()` and `Controller.error()` now delegate to `ApiResponse` from core
- `Handler` uses `ApiResponse.not_found()` / `ApiResponse.validation_error()` instead of raw `jsonify()`
- README examples corrected: middleware uses inline `abort()`, template controller uses `self.view()`, Handler example uses `ApiResponse`
- All Provider imports updated for consistency with top-level `laraflask` namespace
- Version bump: `1.2.0` → `1.3.0`

### v1.2.0 (2026-06-28)
- Updated all dependency versions to latest stable releases
- `flask` → `>=3.1.0`, `sqlalchemy` → `>=2.0.36`, `werkzeug` → `>=3.1.0`
- `bcrypt` → `>=4.2.1`, `pyjwt` → `>=2.10.1`, `cryptography` → `>=44.0.0`
- `celery` → `>=5.4.0`, `redis` → `>=5.2.1`, `gunicorn` → `>=23.0.0`
- `pytest` → `>=8.3.0`, `pytest-cov` → `>=6.0.0`, `faker` → `>=33.0.0`
- `flask-cors` → `>=5.0.0`, `flask-session` → `>=0.8.0`
- Bumped `setuptools` build requirement to `>=75.0`
- Version bump: `1.1.0` → `1.2.0`

### v1.1.0
- Initial public release
