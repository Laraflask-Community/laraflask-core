"""
Laraflask Configuration Manager
Loads and manages config files with dot-notation access.
"""

from __future__ import annotations
import os
import importlib.util
from typing import Any, Dict, Optional


class Config:
    """
    Configuration repository.

    Loads Python config files from the config directory and provides
    dot-notation access: config('database.connections.mysql.host')
    """

    def __init__(self, config_path: str):
        self._config_path = config_path
        self._items: Dict[str, Any] = {}
        self._loaded: set = set()
        self._load_all()

    def _load_all(self):
        """Load all config files from the config directory."""
        if not os.path.isdir(self._config_path):
            return

        for filename in os.listdir(self._config_path):
            if filename.endswith('.py') and not filename.startswith('_'):
                name = filename[:-3]
                self._load_file(name)

    def _load_file(self, name: str) -> None:
        """Load a single config file."""
        if name in self._loaded:
            return

        filepath = os.path.join(self._config_path, f"{name}.py")
        if not os.path.exists(filepath):
            return

        spec = importlib.util.spec_from_file_location(f"config.{name}", filepath)
        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
            # Config files export a dict named after the file or just module attrs
            if hasattr(module, 'config'):
                self._items[name] = module.config
            else:
                self._items[name] = {
                    k: v for k, v in vars(module).items()
                    if not k.startswith('_')
                }
            self._loaded.add(name)
        except Exception as e:
            print(f"Warning: Could not load config [{name}]: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value using dot-notation."""
        keys = key.split('.')
        value = self._items

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Set a config value at runtime."""
        keys = key.split('.')
        d = self._items

        for k in keys[:-1]:
            d = d.setdefault(k, {})

        d[keys[-1]] = value

    def has(self, key: str) -> bool:
        """Check if a config key exists."""
        return self.get(key) is not None

    def all(self) -> Dict[str, Any]:
        """Get all config items."""
        return self._items

    def __call__(self, key: str, default: Any = None) -> Any:
        return self.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)
