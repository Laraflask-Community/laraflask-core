"""
Laraflask Application Core
The heart of the framework — elegant, expressive, and modern.
"""

from __future__ import annotations
import os
import sys
import importlib
import importlib.util
from typing import Any, Callable, Dict, List, Optional, Type
from flask import Flask
from dotenv import load_dotenv

from laraflask.core.container import Container
from laraflask.core.config import Config
from laraflask.routing.router import Router
from laraflask.core.exceptions import ApplicationException


class Application(Container):
    """
    The Laraflask Application.

    This is the main entry point for the framework. It extends the IoC container,
    bootstraps all service providers, and ties together all framework components.
    """

    VERSION = "1.0.0"

    def __init__(self, base_path: str = None):
        super().__init__()
        self._base_path = base_path or os.getcwd()
        self._booted = False
        self._service_providers: List[Any] = []
        self._loaded_providers: List[Any] = []
        self._deferred_services: Dict[str, Any] = {}
        self._flask: Optional[Flask] = None
        self._config: Optional[Config] = None
        self._router: Optional[Router] = None
        self._environment: Optional[str] = None

        self._register_base_bindings()
        self._load_environment()

    def _register_base_bindings(self):
        """Register the base bindings into the container."""
        self.instance('app', self)
        self.instance(Application, self)

    def _load_environment(self):
        """Load environment variables from .env file."""
        env_file = os.path.join(self._base_path, '.env')
        if os.path.exists(env_file):
            load_dotenv(env_file)
        self._environment = os.getenv('APP_ENV', 'production')

    def bootstrap(self) -> 'Application':
        """Bootstrap the application with all service providers."""
        if self._booted:
            return self

        self._flask = Flask(
            __name__,
            template_folder=self.resource_path('views'),
            static_folder=self.path('public'),
        )

        self._config = Config(self.config_path())
        self.instance('config', self._config)

        self._configure_flask()
        self._router = Router(self._flask, self)
        self.instance('router', self._router)

        self._register_core_providers()
        self._boot_providers()

        self._booted = True
        return self

    def _configure_flask(self):
        """Configure Flask with Laraflask settings."""
        self._flask.secret_key = os.getenv('APP_KEY', 'laraflask-secret-key')
        self._flask.config['DEBUG'] = os.getenv('APP_DEBUG', 'false').lower() == 'true'
        self._flask.config['TESTING'] = self._environment == 'testing'
        self._flask.config['JSON_SORT_KEYS'] = False

        # Database
        db_url = self._build_database_url()
        if db_url:
            self._flask.config['SQLALCHEMY_DATABASE_URI'] = db_url
            self._flask.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    def _build_database_url(self) -> Optional[str]:
        """Build database URL from environment variables."""
        driver = os.getenv('DB_CONNECTION', 'sqlite')
        if driver == 'sqlite':
            db_path = os.path.join(self._base_path, 'database', os.getenv('DB_DATABASE', 'laraflask.db'))
            return f"sqlite:///{db_path}"
        elif driver == 'mysql':
            return (f"mysql+pymysql://{os.getenv('DB_USERNAME', 'root')}:"
                    f"{os.getenv('DB_PASSWORD', '')}@"
                    f"{os.getenv('DB_HOST', '127.0.0.1')}:"
                    f"{os.getenv('DB_PORT', '3306')}/"
                    f"{os.getenv('DB_DATABASE', 'laraflask')}")
        elif driver == 'postgresql':
            return (f"postgresql://{os.getenv('DB_USERNAME', 'postgres')}:"
                    f"{os.getenv('DB_PASSWORD', '')}@"
                    f"{os.getenv('DB_HOST', '127.0.0.1')}:"
                    f"{os.getenv('DB_PORT', '5432')}/"
                    f"{os.getenv('DB_DATABASE', 'laraflask')}")
        return None

    def _register_core_providers(self):
        """Register all core framework service providers."""
        from laraflask.core.providers import (
            RouteServiceProvider,
            DatabaseServiceProvider,
            CacheServiceProvider,
            SessionServiceProvider,
            AuthServiceProvider,
            ValidationServiceProvider,
            EventServiceProvider,
            QueueServiceProvider,
            NotificationServiceProvider,
            StorageServiceProvider,
            SchedulerServiceProvider,
        )

        providers = [
            RouteServiceProvider,
            DatabaseServiceProvider,
            CacheServiceProvider,
            SessionServiceProvider,
            AuthServiceProvider,
            ValidationServiceProvider,
            EventServiceProvider,
            QueueServiceProvider,
            NotificationServiceProvider,
            StorageServiceProvider,
            SchedulerServiceProvider,
        ]

        # Load user-defined providers from config
        user_providers = self._config.get('app.providers', [])
        for provider_class_path in user_providers:
            try:
                module_path, class_name = provider_class_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                providers.append(getattr(module, class_name))
            except (ImportError, AttributeError) as e:
                print(f"Warning: Could not load provider {provider_class_path}: {e}")

        for provider_class in providers:
            provider = provider_class(self)
            self._service_providers.append(provider)
            provider.register()
            self._loaded_providers.append(provider)

    def _boot_providers(self):
        """Boot all registered service providers."""
        for provider in self._loaded_providers:
            if hasattr(provider, 'boot'):
                provider.boot()

    def register_provider(self, provider_class: Type) -> 'Application':
        """Register a service provider at runtime."""
        provider = provider_class(self)
        provider.register()
        if self._booted and hasattr(provider, 'boot'):
            provider.boot()
        self._service_providers.append(provider)
        self._loaded_providers.append(provider)
        return self

    def run(self, host: str = '0.0.0.0', port: int = 8000, **kwargs):
        """Run the application server."""
        if not self._booted:
            self.bootstrap()

        self._load_routes()

        debug = self._flask.config.get('DEBUG', False)
        print(self._startup_banner(host, port))

        self._flask.run(host=host, port=port, debug=debug, **kwargs)

    def get_flask(self) -> Flask:
        """Get the underlying Flask application."""
        return self._flask

    def _load_routes(self):
        """Load all route files."""
        routes_path = self.routes_path()

        for route_file in ['web.py', 'api.py']:
            route_module_path = os.path.join(routes_path, route_file)
            if os.path.exists(route_module_path):
                spec = importlib.util.spec_from_file_location(
                    f"routes.{route_file[:-3]}", route_module_path
                )
                module = importlib.util.module_from_spec(spec)
                # Inject router into routes module
                module.Route = self._router
                spec.loader.exec_module(module)

    def environment(self, *environments: str) -> bool:
        """Check if application is in the given environment(s)."""
        if not environments:
            return self._environment
        return self._environment in environments

    def is_production(self) -> bool:
        return self._environment == 'production'

    def is_local(self) -> bool:
        return self._environment == 'local'

    def is_testing(self) -> bool:
        return self._environment == 'testing'

    # ─── Path Helpers ────────────────────────────────────────────────────────

    def path(self, *parts: str) -> str:
        return os.path.join(self._base_path, *parts)

    def app_path(self, *parts: str) -> str:
        return os.path.join(self._base_path, 'app', *parts)

    def config_path(self, *parts: str) -> str:
        return os.path.join(self._base_path, 'config', *parts)

    def database_path(self, *parts: str) -> str:
        return os.path.join(self._base_path, 'database', *parts)

    def resource_path(self, *parts: str) -> str:
        return os.path.join(self._base_path, 'resources', *parts)

    def storage_path(self, *parts: str) -> str:
        return os.path.join(self._base_path, 'storage', *parts)

    def public_path(self, *parts: str) -> str:
        return os.path.join(self._base_path, 'public', *parts)

    def routes_path(self, *parts: str) -> str:
        return os.path.join(self._base_path, 'routes', *parts)

    def _startup_banner(self, host: str, port: int) -> str:
        env = self._environment.upper()
        return f"""
╔══════════════════════════════════════════════════════════╗
║           🚀  L A R A F L A S K  v{self.VERSION}               ║
║     Elegant · Expressive · Modern · Fast · Scalable      ║
╠══════════════════════════════════════════════════════════╣
║  Environment : {env:<43}║
║  Server      : http://{host}:{port:<35}║
║  Debug Mode  : {'ON' if self._flask.config.get('DEBUG') else 'OFF':<43}║
╚══════════════════════════════════════════════════════════╝
"""

    def __repr__(self) -> str:
        return f"<Laraflask Application v{self.VERSION} [{self._environment}]>"
