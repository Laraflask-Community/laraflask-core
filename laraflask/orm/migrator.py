"""Migrator - Runs, rolls back, and tracks database migrations."""

from __future__ import annotations
import os
import datetime
from typing import Dict, List

try:
    from sqlalchemy import Column, Integer, String, DateTime, MetaData, Table, inspect as sa_inspect
    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False

from laraflask.orm._migration import Migration


class Migrator:
    """Runs, rolls back, and tracks database migrations."""

    MIGRATIONS_TABLE = 'migrations'

    def __init__(self, migrations_path: str):
        self._path = migrations_path
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        from laraflask.orm.db import DB
        engine = DB.engine()
        inspector = sa_inspect(engine)
        if self.MIGRATIONS_TABLE not in inspector.get_table_names():
            metadata = MetaData()
            Table(self.MIGRATIONS_TABLE, metadata,
                  Column('id', Integer, primary_key=True, autoincrement=True),
                  Column('migration', String(255), nullable=False),
                  Column('batch', Integer, nullable=False),
                  Column('executed_at', DateTime, default=datetime.datetime.utcnow))
            metadata.create_all(engine)

    def _get_ran(self) -> List[str]:
        from laraflask.orm.db import DB
        rows = DB.select(f"SELECT migration FROM {self.MIGRATIONS_TABLE}")
        return [r['migration'] for r in rows]

    def _get_last_batch(self) -> int:
        from laraflask.orm.db import DB
        rows = DB.select(f"SELECT MAX(batch) as b FROM {self.MIGRATIONS_TABLE}")
        return (rows[0]['b'] or 0) if rows else 0

    def _get_migration_files(self) -> List[str]:
        if not os.path.isdir(self._path):
            return []
        return sorted([f for f in os.listdir(self._path) if f.endswith('.py') and not f.startswith('_')])

    def _load_migration(self, filename: str) -> Migration:
        import importlib.util
        filepath = os.path.join(self._path, filename)
        spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for attr in dir(module):
            obj = getattr(module, attr)
            if isinstance(obj, type) and issubclass(obj, Migration) and obj is not Migration:
                return obj()
        raise ValueError(f"No Migration class found in {filename}")

    def run(self) -> int:
        ran = self._get_ran()
        batch = self._get_last_batch() + 1
        count = 0
        for filename in self._get_migration_files():
            name = filename[:-3]
            if name in ran:
                continue
            migration = self._load_migration(filename)
            migration.up()
            self._log_migration(name, batch)
            count += 1
        return count

    def rollback(self, steps: int = 1) -> int:
        from laraflask.orm.db import DB
        batch = self._get_last_batch()
        rows = DB.select(f"SELECT migration FROM {self.MIGRATIONS_TABLE} WHERE batch = {batch} ORDER BY id DESC")
        count = 0
        for row in rows:
            name = row['migration']
            filename = f"{name}.py"
            migration = self._load_migration(filename)
            migration.down()
            DB.delete(f"DELETE FROM {self.MIGRATIONS_TABLE} WHERE migration = :m", {'m': name})
            count += 1
        return count

    def reset(self) -> int:
        from laraflask.orm.db import DB
        rows = DB.select(f"SELECT migration FROM {self.MIGRATIONS_TABLE} ORDER BY id DESC")
        count = 0
        for row in rows:
            name = row['migration']
            filename = f"{name}.py"
            if os.path.exists(os.path.join(self._path, filename)):
                migration = self._load_migration(filename)
                migration.down()
            DB.delete(f"DELETE FROM {self.MIGRATIONS_TABLE} WHERE migration = :m", {'m': name})
            count += 1
        return count

    def fresh(self):
        from laraflask.orm.db import DB
        DB.drop_all()
        self._ensure_migrations_table()
        return self.run()

    def _log_migration(self, name: str, batch: int):
        from laraflask.orm.db import DB
        DB.insert(
            f"INSERT INTO {self.MIGRATIONS_TABLE} (migration, batch, executed_at) VALUES (:migration, :batch, :executed_at)",
            {'migration': name, 'batch': batch, 'executed_at': datetime.datetime.utcnow().isoformat()})

    def status(self) -> List[Dict]:
        ran = set(self._get_ran())
        return [{'migration': f[:-3], 'ran': f[:-3] in ran} for f in self._get_migration_files()]
