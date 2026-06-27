"""
ArtisanPy — The Laraflask Command Line Interface
python artisan.py make:model User
python artisan.py migrate
python artisan.py queue:work
"""

from __future__ import annotations
import os
import sys
import re
import datetime
import argparse
import textwrap
from typing import Any, Callable, Dict, List, Optional


CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'


class Command:
    """Base class for Artisan commands."""

    name: str = ''
    description: str = ''
    arguments: List[Dict] = []
    options: List[Dict] = []

    def __init__(self):
        self._output: List[str] = []

    def handle(self, args: argparse.Namespace) -> int:
        raise NotImplementedError

    def info(self, message: str):
        print(f"{GREEN}{message}{RESET}")

    def error(self, message: str):
        print(f"{RED}ERROR: {message}{RESET}", file=sys.stderr)

    def warn(self, message: str):
        print(f"{YELLOW}WARNING: {message}{RESET}")

    def line(self, message: str = ''):
        print(message)

    def comment(self, message: str):
        print(f"{CYAN}{message}{RESET}")

    def ask(self, question: str, default: str = '') -> str:
        try:
            answer = input(f"{CYAN}{question}{RESET} [{default}]: ").strip()
            return answer or default
        except KeyboardInterrupt:
            return default

    def confirm(self, question: str, default: bool = False) -> bool:
        suffix = '[Y/n]' if default else '[y/N]'
        try:
            answer = input(f"{CYAN}{question} {suffix}: {RESET}").strip().lower()
            if not answer:
                return default
            return answer in ('y', 'yes')
        except KeyboardInterrupt:
            return default

    def table(self, headers: List[str], rows: List[List]) -> None:
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))

        border = '+' + '+'.join('-' * (w + 2) for w in widths) + '+'
        header_row = '|' + '|'.join(f" {h:<{w}} " for h, w in zip(headers, widths)) + '|'

        print(border)
        print(header_row)
        print(border)
        for row in rows:
            print('|' + '|'.join(f" {str(c):<{w}} " for c, w in zip(row, widths)) + '|')
        print(border)


class TinkerCommand(Command):
    """
    [ID] Membuka REPL interaktif Python dengan semua Model dan helper
    framework (DB, Cache, Auth, Events, Queue, dll) sudah otomatis di-import
    ke dalam namespace, mirip `php artisan tinker` di Laravel.

    [EN] Opens an interactive Python REPL with all Models and core framework
    helpers (DB, Cache, Auth, Events, Queue, etc.) automatically imported
    into the namespace, similar to Laravel's `php artisan tinker`.
    """

    name = 'tinker'
    description = 'Interact with your application via an interactive REPL'

    def handle(self, args: argparse.Namespace) -> int:
        namespace = self._build_namespace()

        self.info(f"Laraflask Tinker [Python {sys.version.split()[0]}]")
        self.comment(f"{len(namespace)} variable(s) auto-imported. Type `dir()` to see them, `exit()` to quit.\n")

        if self._try_ipython(namespace):
            return 0

        self._run_stdlib_console(namespace)
        return 0

    # ─── Namespace Bootstrap ──────────────────────────────────────────────────

    def _build_namespace(self) -> Dict[str, Any]:
        """
        [ID] Bootstrap Application lalu kumpulkan semua Model (dari app/Models)
        dan helper/facade inti framework ke satu dict namespace.

        [EN] Bootstraps the Application then collects all Models (from
        app/Models) plus core framework helpers/facades into a single
        namespace dict.
        """
        namespace: Dict[str, Any] = {}

        # Boot the application container so DB/Cache/Auth/etc. are ready to use.
        try:
            from laraflask.core.application import Application
            app = Application(os.getcwd())
            app.bootstrap()
            namespace['app'] = app
        except Exception as e:
            self.warn(f"Application failed to bootstrap fully: {e}")
            self.warn("Some helpers (DB-backed models, config, etc.) may not work.")

        # Core framework facades/helpers — best-effort imports, never fatal.
        helper_imports = [
            ('laraflask.orm.db', 'DB'),
            ('laraflask.cache.cache', 'Cache'),
            ('laraflask.auth.auth', 'Auth'),
            ('laraflask.auth.auth', 'Gate'),
            ('laraflask.auth.auth', 'Hash'),
            ('laraflask.events.dispatcher', 'Events'),
            ('laraflask.queue.queue', 'Queue'),
            ('laraflask.storage.storage', 'Storage'),
            ('laraflask.scheduler.schedule', 'Schedule'),
            ('laraflask.validation.validator', 'Validator'),
        ]
        for module_path, attr_name in helper_imports:
            try:
                module = __import__(module_path, fromlist=[attr_name])
                namespace[attr_name] = getattr(module, attr_name)
            except Exception:
                continue

        # Auto-import every Model class declared in app/Models/*.py
        namespace.update(self._discover_models())

        return namespace

    def _discover_models(self) -> Dict[str, Any]:
        """
        [ID] Scan folder app/Models dan import setiap class Model yang
        ditemukan ke namespace REPL (key = nama class).

        [EN] Scans the app/Models folder and imports every Model class
        found into the REPL namespace (keyed by class name).
        """
        models: Dict[str, Any] = {}
        models_dir = os.path.join('app', 'Models')

        if not os.path.isdir(models_dir):
            return models

        sys.path.insert(0, os.getcwd())

        from laraflask.orm.model import Model

        for filename in sorted(os.listdir(models_dir)):
            if not filename.endswith('.py') or filename.startswith('__'):
                continue

            module_name = filename[:-3]
            try:
                import importlib
                module = importlib.import_module(f'app.Models.{module_name}')
            except Exception as e:
                self.warn(f"Could not import model [{module_name}]: {e}")
                continue

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and issubclass(attr, Model)
                        and attr is not Model and attr.__module__ == module.__name__):
                    models[attr_name] = attr

        return models

    # ─── REPL Backends ────────────────────────────────────────────────────────

    def _try_ipython(self, namespace: Dict[str, Any]) -> bool:
        """Attempt to launch IPython if it's installed; returns False if unavailable."""
        try:
            from IPython import start_ipython
            from traitlets.config import Config as IPyConfig

            ipy_config = IPyConfig()
            ipy_config.TerminalInteractiveShell.banner1 = ''
            start_ipython(argv=[], user_ns=namespace, config=ipy_config)
            return True
        except ImportError:
            return False

    def _run_stdlib_console(self, namespace: Dict[str, Any]) -> None:
        """Fall back to the standard library's `code.InteractiveConsole`."""
        import code
        import atexit

        # Nicer arrow-key history / editing where readline is available.
        try:
            import readline
            histfile = os.path.join(os.path.expanduser('~'), '.laraflask_tinker_history')
            try:
                readline.read_history_file(histfile)
            except (FileNotFoundError, PermissionError):
                pass
            atexit.register(readline.write_history_file, histfile)
        except ImportError:
            pass

        banner = ''
        exit_msg = 'Goodbye.'
        console = code.InteractiveConsole(locals=namespace)
        try:
            console.interact(banner=banner, exitmsg=exit_msg)
        except SystemExit:
            pass


class MakeModelCommand(Command):
    name = 'make:model'
    description = 'Create a new Eloquent model class'

    def handle(self, args: argparse.Namespace) -> int:
        name = args.name
        migration = getattr(args, 'migration', False)
        controller = getattr(args, 'controller', False)
        resource = getattr(args, 'resource', False)

        stub = self._get_stub(name)
        path = os.path.join('app', 'Models', f"{name}.py")

        if os.path.exists(path):
            self.error(f"Model [{name}] already exists!")
            return 1

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(stub)

        self.info(f"Model [{name}] created successfully.")

        if migration:
            table_name = self._to_table_name(name)
            MakeMigrationCommand().handle(
                argparse.Namespace(name=f"create_{table_name}_table")
            )

        if controller or resource:
            MakeControllerCommand().handle(
                argparse.Namespace(
                    name=f"{name}Controller",
                    resource=resource,
                    model=name,
                )
            )

        return 0

    def _get_stub(self, name: str) -> str:
        return f'''"""
{name} Model
"""

from laraflask.orm.model import Model


class {name}(Model):
    """
    {name} model.
    """

    # __table__ = '{self._to_table_name(name)}'
    __fillable__ = []
    __hidden__ = ['password']
    __casts__ = {{}}

    # ─── Relationships ────────────────────────────────────────────────────────

    # @property
    # def posts(self):
    #     from app.Models.Post import Post
    #     return self.has_many(Post)

    # ─── Accessors & Mutators ─────────────────────────────────────────────────

    # def get_full_name_attribute(self):
    #     return f"{{self.first_name}} {{self.last_name}}"

    # def set_password_attribute(self, value):
    #     from laraflask.auth.auth import Hash
    #     return Hash.make(value)
'''

    @staticmethod
    def _to_table_name(class_name: str) -> str:
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        snake = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        if snake.endswith('y'):
            return snake[:-1] + 'ies'
        return snake + 's'


class MakeControllerCommand(Command):
    name = 'make:controller'
    description = 'Create a new controller class'

    def handle(self, args: argparse.Namespace) -> int:
        name = args.name
        resource = getattr(args, 'resource', False)
        model = getattr(args, 'model', None)
        api = getattr(args, 'api', False)

        stub = self._get_resource_stub(name, model) if resource else self._get_basic_stub(name)
        path = os.path.join('app', 'Controllers', f"{name}.py")

        if os.path.exists(path):
            self.error(f"Controller [{name}] already exists!")
            return 1

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(stub)

        self.info(f"Controller [{name}] created successfully.")
        return 0

    def _get_basic_stub(self, name: str) -> str:
        return f'''"""
{name}
"""

from flask import jsonify, request, render_template
from laraflask.routing.router import Router


class {name}:
    """
    {name}
    """

    def index(self):
        return jsonify({{'message': 'Hello from {name}'}})
'''

    def _get_resource_stub(self, name: str, model: str = None) -> str:
        model_name = model or name.replace('Controller', '')
        model_lower = model_name.lower()
        return f'''"""
{name} — Resource Controller
"""

from flask import jsonify, request
from laraflask.validation.validator import Validator
from laraflask.auth.auth import auth_required
from app.Models.{model_name} import {model_name}


class {name}:
    """
    RESTful resource controller for {model_name}.
    """

    def index(self):
        """GET /{model_lower}s — List all {model_lower}s."""
        items = {model_name}.paginate(per_page=15, page=request.args.get('page', 1, type=int))
        return jsonify(items)

    def create(self):
        """GET /{model_lower}s/create — Show creation form."""
        return jsonify({{'message': 'Show create form'}})

    def store(self):
        """POST /{model_lower}s — Create a new {model_lower}."""
        data = request.get_json() or request.form.to_dict()

        validator = Validator(data, {{
            # 'name': 'required|string|max:255',
        }})

        if validator.fails():
            return jsonify({{'errors': validator.errors()}}), 422

        item = {model_name}.create(**validator.get_validated())
        return jsonify(item.to_dict()), 201

    def show(self, id: int):
        """GET /{model_lower}s/<id> — Show a specific {model_lower}."""
        item = {model_name}.find_or_fail(id)
        return jsonify(item.to_dict())

    def edit(self, id: int):
        """GET /{model_lower}s/<id>/edit — Show edit form."""
        item = {model_name}.find_or_fail(id)
        return jsonify(item.to_dict())

    def update(self, id: int):
        """PUT/PATCH /{model_lower}s/<id> — Update a {model_lower}."""
        item = {model_name}.find_or_fail(id)
        data = request.get_json() or request.form.to_dict()
        item.fill(data).save()
        return jsonify(item.to_dict())

    def destroy(self, id: int):
        """DELETE /{model_lower}s/<id> — Delete a {model_lower}."""
        item = {model_name}.find_or_fail(id)
        item.delete()
        return '', 204
'''


class MakeMigrationCommand(Command):
    name = 'make:migration'
    description = 'Create a new database migration file'

    def handle(self, args: argparse.Namespace) -> int:
        migration_name = args.name
        timestamp = datetime.datetime.now().strftime('%Y_%m_%d_%H%M%S')
        filename = f"{timestamp}_{migration_name}.py"
        path = os.path.join('database', 'migrations', filename)

        os.makedirs(os.path.dirname(path), exist_ok=True)

        stub = self._detect_stub(migration_name)
        with open(path, 'w') as f:
            f.write(stub)

        self.info(f"Created Migration: {filename}")
        return 0

    def _detect_stub(self, name: str) -> str:
        create_match = re.match(r'create_(\w+)_table', name)
        add_match = re.match(r'add_(\w+)_to_(\w+)_table', name)

        if create_match:
            table = create_match.group(1)
            return self._create_stub(table)
        elif add_match:
            columns = add_match.group(1)
            table = add_match.group(2)
            return self._add_column_stub(table, columns)
        return self._blank_stub()

    def _create_stub(self, table: str) -> str:
        return f'''"""
Create {table} table migration.
"""

from laraflask.orm.migration import Migration, Schema


class Migration_{table.title()}(Migration):

    def up(self):
        """Run the migration."""
        Schema.create('{table}', lambda table: [
            table.id(),
            table.string('name'),
            table.timestamps(),
        ])

    def down(self):
        """Reverse the migration."""
        Schema.drop_if_exists('{table}')
'''

    def _add_column_stub(self, table: str, columns: str) -> str:
        return f'''"""
Add {columns} to {table} table.
"""

from laraflask.orm.migration import Migration, Schema


class Migration_Add_{columns}(Migration):

    def up(self):
        """Run the migration."""
        Schema.table('{table}', lambda table: [
            table.string('{columns}').nullable(),
        ])

    def down(self):
        """Reverse the migration."""
        # Schema.table('{table}', lambda table: table.drop_column('{columns}'))
        pass
'''

    def _blank_stub(self) -> str:
        return '''"""
Database migration.
"""

from laraflask.orm.migration import Migration, Schema


class CustomMigration(Migration):

    def up(self):
        """Run the migration."""
        pass

    def down(self):
        """Reverse the migration."""
        pass
'''


class MakeMiddlewareCommand(Command):
    name = 'make:middleware'
    description = 'Create a new middleware class'

    def handle(self, args: argparse.Namespace) -> int:
        name = args.name
        path = os.path.join('app', 'Middleware', f"{name}.py")
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as f:
            f.write(f'''"""
{name} Middleware
"""

from typing import Callable, Any
from flask import Request
from laraflask.middleware.middleware import Middleware


class {name}(Middleware):
    """
    {name} middleware.
    """

    def handle(self, request: Request, next: Callable) -> Any:
        # Perform action before request
        response = next(request)
        # Perform action after response
        return response
''')

        self.info(f"Middleware [{name}] created successfully.")
        return 0


class MakeJobCommand(Command):
    name = 'make:job'
    description = 'Create a new job class'

    def handle(self, args: argparse.Namespace) -> int:
        name = args.name
        path = os.path.join('app', 'Jobs', f"{name}.py")
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as f:
            f.write(f'''"""
{name} Job
"""

from laraflask.queue.queue import Job


class {name}(Job):
    """
    {name} queued job.
    """

    queue = 'default'
    tries = 3
    timeout = 60

    def __init__(self, **data):
        for key, value in data.items():
            setattr(self, key, value)

    def handle(self) -> None:
        """Execute the job."""
        pass

    def failed(self, exception: Exception) -> None:
        """Handle job failure."""
        pass
''')

        self.info(f"Job [{name}] created successfully.")
        return 0


class MakeEventCommand(Command):
    name = 'make:event'
    description = 'Create a new event class'

    def handle(self, args: argparse.Namespace) -> int:
        name = args.name
        path = os.path.join('app', 'Events', f"{name}.py")
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as f:
            f.write(f'''"""
{name} Event
"""

from laraflask.events.dispatcher import Event


class {name}(Event):
    """
    {name} event.
    """

    def __init__(self, **data):
        super().__init__(**data)

    def broadcast_on(self):
        """Define broadcast channels."""
        return []
''')

        self.info(f"Event [{name}] created successfully.")
        return 0


class MakeListenerCommand(Command):
    name = 'make:listener'
    description = 'Create a new event listener class'

    def handle(self, args: argparse.Namespace) -> int:
        name = args.name
        event = getattr(args, 'event', None)
        path = os.path.join('app', 'Listeners', f"{name}.py")
        os.makedirs(os.path.dirname(path), exist_ok=True)

        event_import = f"from app.Events.{event} import {event}" if event else ""
        event_type = event or 'Event'

        with open(path, 'w') as f:
            f.write(f'''"""
{name} Listener
"""

{event_import}
from laraflask.events.dispatcher import Listener, Event


class {name}(Listener):
    """
    {name} listener.
    """

    def handle(self, event: {event_type}) -> None:
        """Handle the event."""
        pass

    def should_queue(self) -> bool:
        return False
''')

        self.info(f"Listener [{name}] created successfully.")
        return 0


class MakeNotificationCommand(Command):
    name = 'make:notification'
    description = 'Create a new notification class'

    def handle(self, args: argparse.Namespace) -> int:
        name = args.name
        path = os.path.join('app', 'Notifications', f"{name}.py")
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as f:
            f.write(f'''"""
{name} Notification
"""

from laraflask.notifications.notification import Notification, MailMessage


class {name}(Notification):
    """
    {name} notification.
    """

    def __init__(self, **data):
        for key, value in data.items():
            setattr(self, key, value)

    def via(self, notifiable) -> list:
        return ['mail']

    def to_mail(self, notifiable) -> MailMessage:
        return (MailMessage()
                .subject('{name}')
                .line('Hello,')
                .line('This is your notification.')
                .action('Visit Site', 'https://example.com'))
''')

        self.info(f"Notification [{name}] created successfully.")
        return 0


class MigrateCommand(Command):
    name = 'migrate'
    description = 'Run the database migrations'

    def handle(self, args: argparse.Namespace) -> int:
        from laraflask.orm.migration import Migrator
        self.info('Running migrations...')

        migrator = Migrator(os.path.join('database', 'migrations'))
        count = migrator.run()

        if count == 0:
            self.info('Nothing to migrate.')
        else:
            self.info(f'{count} migration(s) ran successfully.')
        return 0


class MigrateRollbackCommand(Command):
    name = 'migrate:rollback'
    description = 'Rollback the last database migration'

    def handle(self, args: argparse.Namespace) -> int:
        from laraflask.orm.migration import Migrator
        steps = getattr(args, 'step', 1)
        self.info(f'Rolling back {steps} batch(es)...')

        migrator = Migrator(os.path.join('database', 'migrations'))
        count = migrator.rollback(steps)
        self.info(f'Rolled back {count} migration(s).')
        return 0


class MigrateRefreshCommand(Command):
    name = 'migrate:refresh'
    description = 'Reset and re-run all migrations'

    def handle(self, args: argparse.Namespace) -> int:
        from laraflask.orm.migration import Migrator
        self.warn('Rolling back all migrations...')
        migrator = Migrator(os.path.join('database', 'migrations'))
        migrator.reset()
        self.info('Re-running all migrations...')
        count = migrator.run()
        self.info(f'{count} migration(s) ran successfully.')
        return 0


class MigrateFreshCommand(Command):
    name = 'migrate:fresh'
    description = 'Drop all tables and re-run all migrations'

    def handle(self, args: argparse.Namespace) -> int:
        from laraflask.orm.migration import Migrator
        if not self.confirm('This will drop all tables. Are you sure?', False):
            self.line('Operation cancelled.')
            return 0

        self.warn('Dropping all tables...')
        migrator = Migrator(os.path.join('database', 'migrations'))
        count = migrator.fresh()
        self.info(f'{count} migration(s) ran successfully.')
        return 0


class MigrateStatusCommand(Command):
    name = 'migrate:status'
    description = 'Show the status of each migration'

    def handle(self, args: argparse.Namespace) -> int:
        from laraflask.orm.migration import Migrator
        migrator = Migrator(os.path.join('database', 'migrations'))
        status = migrator.status()

        if not status:
            self.info('No migration files found.')
            return 0

        rows = [[
            f"{GREEN}✓ Ran{RESET}" if s['ran'] else f"{YELLOW}Pending{RESET}",
            s['migration']
        ] for s in status]
        self.table(['Status', 'Migration'], rows)
        return 0


class DbSeedCommand(Command):
    name = 'db:seed'
    description = 'Seed the database with records'

    def handle(self, args: argparse.Namespace) -> int:
        seeder_class = getattr(args, 'class', 'DatabaseSeeder')
        self.info(f'Seeding database with [{seeder_class}]...')

        try:
            import importlib
            module = importlib.import_module(f'database.seeders.{seeder_class}')
            seeder = getattr(module, seeder_class)()
            seeder.run()
            self.info('Database seeded successfully.')
        except Exception as e:
            self.error(f'Seeder failed: {e}')
            return 1
        return 0


class RouteListCommand(Command):
    name = 'route:list'
    description = 'List all registered routes'

    def handle(self, args: argparse.Namespace) -> int:
        try:
            from laraflask.core.application import Application
            app = Application()
            app.bootstrap()

            rows = []
            for route in app._router.get_routes():
                rows.append([
                    ', '.join(m for m in route.methods if m != 'HEAD'),
                    route.uri,
                    route.get_name() or '',
                    str(route.action)[:40],
                    ', '.join(route.get_middleware()),
                ])

            self.table(['Method', 'URI', 'Name', 'Action', 'Middleware'], rows)
        except Exception as e:
            self.error(f'Could not load routes: {e}')
        return 0


class QueueWorkCommand(Command):
    name = 'queue:work'
    description = 'Start processing jobs on the queue'

    def handle(self, args: argparse.Namespace) -> int:
        queue = getattr(args, 'queue', 'default')
        sleep = getattr(args, 'sleep', 3)
        tries = getattr(args, 'tries', 3)
        connection = getattr(args, 'connection', None)

        from laraflask.queue.queue import Queue, Worker
        driver = Queue.connection(connection)
        worker = Worker(driver, queue)

        self.info(f"Worker started on [{queue}] queue. Press Ctrl+C to stop.")
        try:
            worker.daemon(sleep=sleep)
        except KeyboardInterrupt:
            self.warn('\nWorker stopped.')
        return 0


class QueueListenCommand(Command):
    name = 'queue:listen'
    description = 'Listen to a given queue'

    def handle(self, args: argparse.Namespace) -> int:
        return QueueWorkCommand().handle(args)


class ScheduleRunCommand(Command):
    name = 'schedule:run'
    description = 'Run the scheduled commands'

    def handle(self, args: argparse.Namespace) -> int:
        # Load console routes
        console_path = os.path.join('routes', 'console.py')
        if os.path.exists(console_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location('routes.console', console_path)
            module = importlib.util.module_from_spec(spec)
            from laraflask.scheduler.schedule import Schedule
            module.Schedule = Schedule
            spec.loader.exec_module(module)

        from laraflask.scheduler.schedule import Schedule
        count = Schedule.run_due()
        if count:
            self.info(f'{count} scheduled task(s) ran.')
        else:
            self.info('No scheduled tasks are due.')
        return 0


class ScheduleWorkCommand(Command):
    name = 'schedule:work'
    description = 'Start the schedule worker (run every minute)'

    def handle(self, args: argparse.Namespace) -> int:
        from laraflask.scheduler.schedule import Schedule
        self.info('Schedule worker started. Press Ctrl+C to stop.')
        try:
            Schedule.start_daemon()
        except KeyboardInterrupt:
            self.warn('\nSchedule worker stopped.')
        return 0


class CacheClearCommand(Command):
    name = 'cache:clear'
    description = 'Flush the application cache'

    def handle(self, args: argparse.Namespace) -> int:
        from laraflask.cache.cache import Cache
        Cache.flush()
        self.info('Application cache cleared.')
        return 0


class ServeCommand(Command):
    name = 'serve'
    description = 'Serve the application on the PHP development server'

    def handle(self, args: argparse.Namespace) -> int:
        host = getattr(args, 'host', '127.0.0.1')
        port = getattr(args, 'port', 8000)

        self.info(f"Laraflask development server started: http://{host}:{port}")
        os.system(f"python laraflask.py --host={host} --port={port}")
        return 0


class KeyGenerateCommand(Command):
    name = 'key:generate'
    description = 'Set the application key'

    def handle(self, args: argparse.Namespace) -> int:
        import secrets
        key = 'base64:' + secrets.token_hex(32)
        self.info(f"Application key set: {key}")

        env_file = '.env'
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                content = f.read()
            content = re.sub(r'APP_KEY=.*', f'APP_KEY={key}', content)
            with open(env_file, 'w') as f:
                f.write(content)
            self.info('Application key written to .env file.')
        return 0


class EnvDecryptCommand(Command):
    name = 'env:decrypt'
    description = 'Decrypt an environment file'

    def handle(self, args: argparse.Namespace) -> int:
        self.warn('env:decrypt not implemented yet.')
        return 0


class AboutCommand(Command):
    name = 'about'
    description = 'Display basic information about your application'

    def handle(self, args: argparse.Namespace) -> int:
        print(f"""
{BOLD}{CYAN}╔══════════════════════════════════════════════╗{RESET}
{BOLD}{CYAN}║     🚀 Laraflask Framework Information       ║{RESET}
{BOLD}{CYAN}╚══════════════════════════════════════════════╝{RESET}

{BOLD}Framework{RESET}     Laraflask v1.0.0
{BOLD}Python{RESET}        {sys.version.split()[0]}
{BOLD}Environment{RESET}   {os.getenv('APP_ENV', 'production')}
{BOLD}Debug{RESET}         {os.getenv('APP_DEBUG', 'false')}
{BOLD}Database{RESET}      {os.getenv('DB_CONNECTION', 'sqlite')}
{BOLD}Cache{RESET}         {os.getenv('CACHE_DRIVER', 'file')}
{BOLD}Queue{RESET}         {os.getenv('QUEUE_CONNECTION', 'sync')}
""")
        return 0


# ─── ArtisanPy CLI ────────────────────────────────────────────────────────────

class ArtisanPy:
    """The Laraflask command runner."""

    COMMANDS = [
        TinkerCommand,
        MakeModelCommand,
        MakeControllerCommand,
        MakeMigrationCommand,
        MakeMiddlewareCommand,
        MakeJobCommand,
        MakeEventCommand,
        MakeListenerCommand,
        MakeNotificationCommand,
        MigrateCommand,
        MigrateRollbackCommand,
        MigrateRefreshCommand,
        MigrateFreshCommand,
        MigrateStatusCommand,
        DbSeedCommand,
        RouteListCommand,
        QueueWorkCommand,
        QueueListenCommand,
        ScheduleRunCommand,
        ScheduleWorkCommand,
        CacheClearCommand,
        ServeCommand,
        KeyGenerateCommand,
        AboutCommand,
    ]

    def __init__(self):
        self._commands: Dict[str, Command] = {}
        for cmd_class in self.COMMANDS:
            cmd = cmd_class()
            self._commands[cmd.name] = cmd

    def add(self, command: Command) -> 'ArtisanPy':
        self._commands[command.name] = command
        return self

    def run(self, argv: List[str] = None) -> int:
        argv = argv or sys.argv[1:]

        if not argv or argv[0] in ('-h', '--help'):
            self._print_help()
            return 0

        if argv[0] == 'list':
            self._print_help()
            return 0

        command_name = argv[0]
        command = self._commands.get(command_name)

        if not command:
            print(f"{RED}Command [{command_name}] not found.{RESET}")
            print(f"Run {CYAN}python artisan.py list{RESET} to see all commands.")
            return 1

        # Parse arguments for the command
        parser = argparse.ArgumentParser(
            prog=f"python artisan.py {command_name}",
            description=command.description,
            add_help=True,
        )

        # Add command-specific arguments
        self._add_command_args(parser, command_name)
        args = parser.parse_args(argv[1:])

        return command.handle(args)

    def _add_command_args(self, parser: argparse.ArgumentParser, command_name: str):
        """Add arguments specific to each command."""
        args_map = {
            'make:model':        [('name', {}), ('-m', {'dest': 'migration', 'action': 'store_true'}),
                                   ('-c', {'dest': 'controller', 'action': 'store_true'}),
                                   ('-r', {'dest': 'resource', 'action': 'store_true'})],
            'make:controller':   [('name', {}), ('-r', {'dest': 'resource', 'action': 'store_true'}),
                                   ('--model', {'dest': 'model', 'default': None}),
                                   ('--api', {'action': 'store_true'})],
            'make:migration':    [('name', {})],
            'make:middleware':   [('name', {})],
            'make:job':          [('name', {})],
            'make:event':        [('name', {})],
            'make:listener':     [('name', {}), ('-e', {'dest': 'event', 'default': None})],
            'make:notification': [('name', {})],
            'migrate:rollback':  [('--step', {'type': int, 'default': 1})],
            'db:seed':           [('--class', {'dest': 'class', 'default': 'DatabaseSeeder'})],
            'queue:work':        [('--queue', {'default': 'default'}),
                                   ('--sleep', {'type': int, 'default': 3}),
                                   ('--tries', {'type': int, 'default': 3}),
                                   ('--connection', {'default': None})],
            'serve':             [('--host', {'default': '127.0.0.1'}),
                                   ('--port', {'type': int, 'default': 8000})],
        }

        for arg_def in args_map.get(command_name, []):
            name, kwargs = arg_def
            if name.startswith('-'):
                parser.add_argument(name, **kwargs)
            else:
                parser.add_argument(name, **kwargs)

    def _print_help(self):
        print(f"""
{BOLD}{CYAN}
  ██╗      █████╗ ██████╗  █████╗ ███████╗██╗      █████╗ ███████╗██╗  ██╗
  ██║     ██╔══██╗██╔══██╗██╔══██╗██╔════╝██║     ██╔══██╗██╔════╝██║ ██╔╝
  ██║     ███████║██████╔╝███████║█████╗  ██║     ███████║███████╗█████╔╝
  ██║     ██╔══██║██╔══██╗██╔══██║██╔══╝  ██║     ██╔══██║╚════██║██╔═██╗
  ███████╗██║  ██║██║  ██║██║  ██║██║     ███████╗██║  ██║███████║██║  ██╗
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
{RESET}
  {DIM}Elegant · Expressive · Modern · Fast · Scalable{RESET}   v1.0.0

{BOLD}Usage:{RESET}
  python artisan.py <command> [options] [arguments]

{BOLD}Available Commands:{RESET}""")

        groups: Dict[str, List] = {}
        for name, cmd in self._commands.items():
            group = name.split(':')[0] if ':' in name else 'basic'
            groups.setdefault(group, []).append((name, cmd.description))

        for group, cmds in sorted(groups.items()):
            if group != 'basic':
                print(f"\n {BOLD}{group}{RESET}")
            for name, desc in sorted(cmds):
                print(f"  {GREEN}{name:<30}{RESET} {desc}")

        print()
