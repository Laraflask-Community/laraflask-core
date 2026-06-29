"""Tests for laraflask.core.config.Config."""

import os
import tempfile
import pytest

from laraflask.core.config import Config


@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary config directory with sample config files."""
    # config/app.py
    app_config = tmp_path / "app.py"
    app_config.write_text(
        "config = {\n"
        "    'name': 'LaraFlask',\n"
        "    'debug': True,\n"
        "    'version': '1.0.0',\n"
        "}\n"
    )

    # config/database.py
    db_config = tmp_path / "database.py"
    db_config.write_text(
        "config = {\n"
        "    'default': 'mysql',\n"
        "    'connections': {\n"
        "        'mysql': {\n"
        "            'host': 'localhost',\n"
        "            'port': 3306,\n"
        "            'database': 'laraflask',\n"
        "        },\n"
        "        'sqlite': {\n"
        "            'path': '/tmp/db.sqlite',\n"
        "        },\n"
        "    },\n"
        "}\n"
    )

    return str(tmp_path)


@pytest.fixture
def config(config_dir):
    """Create a Config instance from the temp directory."""
    return Config(config_dir)


class TestConfigLoading:
    """Test config file loading from directory."""

    def test_loads_all_config_files(self, config):
        assert config.has("app")
        assert config.has("database")

    def test_ignores_underscore_files(self, tmp_path):
        hidden = tmp_path / "_secret.py"
        hidden.write_text("config = {'key': 'value'}")
        cfg = Config(str(tmp_path))
        assert cfg.has("_secret") is False

    def test_nonexistent_directory(self):
        cfg = Config("/nonexistent/path/to/config")
        assert cfg.all() == {}


class TestConfigGet:
    """Test get() with dot-notation access."""

    def test_simple_get(self, config):
        assert config.get("app.name") == "LaraFlask"

    def test_nested_get(self, config):
        assert config.get("database.connections.mysql.host") == "localhost"
        assert config.get("database.connections.mysql.port") == 3306

    def test_get_default(self, config):
        assert config.get("app.nonexistent", "default_val") == "default_val"

    def test_get_none_for_missing(self, config):
        assert config.get("missing.key") is None

    def test_top_level_get(self, config):
        app = config.get("app")
        assert isinstance(app, dict)
        assert app["name"] == "LaraFlask"


class TestConfigSet:
    """Test set() for runtime config modification."""

    def test_set_new_key(self, config):
        config.set("app.timezone", "UTC")
        assert config.get("app.timezone") == "UTC"

    def test_set_nested_creates_intermediates(self, config):
        config.set("cache.driver.name", "redis")
        assert config.get("cache.driver.name") == "redis"

    def test_set_overwrites_existing(self, config):
        config.set("app.debug", False)
        assert config.get("app.debug") is False


class TestConfigHas:
    """Test has() key existence check."""

    def test_has_existing(self, config):
        assert config.has("app.name") is True

    def test_has_missing(self, config):
        assert config.has("nonexistent.key") is False

    def test_has_nested(self, config):
        assert config.has("database.connections.mysql.host") is True


class TestConfigCallable:
    """Test __call__ and __getitem__ / __setitem__."""

    def test_callable_get(self, config):
        assert config("app.name") == "LaraFlask"

    def test_callable_default(self, config):
        assert config("missing", "fallback") == "fallback"

    def test_getitem(self, config):
        assert config["app.name"] == "LaraFlask"

    def test_setitem(self, config):
        config["app.locale"] = "en"
        assert config.get("app.locale") == "en"


class TestConfigAll:
    """Test all() returns the full config dict."""

    def test_all_returns_dict(self, config):
        result = config.all()
        assert isinstance(result, dict)
        assert "app" in result
        assert "database" in result
