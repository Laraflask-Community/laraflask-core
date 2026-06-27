"""
Laraflask Migration System
Laravel-inspired schema migrations with rollback support.
"""

from __future__ import annotations
import os
import datetime
from typing import Any, Callable, Dict, List, Optional
try:
    from sqlalchemy import (
        Column, Integer, String, Text, Boolean, Float, DateTime,
        Date, BigInteger, SmallInteger, Numeric, LargeBinary,
        ForeignKey, UniqueConstraint, Index, inspect as sa_inspect,
        text
    )
    from sqlalchemy import Table, MetaData
    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False
    Column = Integer = String = Text = Boolean = Float = DateTime = None
    Date = BigInteger = SmallInteger = Numeric = LargeBinary = None
    ForeignKey = UniqueConstraint = Index = sa_inspect = text = None
    Table = MetaData = None

try:
    from pgvector.sqlalchemy import Vector
    _PGVECTOR_AVAILABLE = True
except ImportError:
    _PGVECTOR_AVAILABLE = False
    Vector = None


class Blueprint:
    """
    Schema blueprint — define table columns and indexes
    with an expressive, fluent interface.
    """

    def __init__(self, table: str, prefix: str = ''):
        self.table = table
        self.prefix = prefix
        self._columns: List[Column] = []
        self._indexes: List[Any] = []
        self._constraints: List[Any] = []
        self._commands: List[Dict] = []

    # ─── Integer Types ────────────────────────────────────────────────────────

    def id(self, name: str = 'id') -> 'ColumnDefinition':
        col = Column(name, Integer, primary_key=True, autoincrement=True)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def big_increments(self, name: str = 'id') -> 'ColumnDefinition':
        col = Column(name, BigInteger, primary_key=True, autoincrement=True)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def integer(self, name: str) -> 'ColumnDefinition':
        col = Column(name, Integer, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def big_integer(self, name: str) -> 'ColumnDefinition':
        col = Column(name, BigInteger, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def small_integer(self, name: str) -> 'ColumnDefinition':
        col = Column(name, SmallInteger, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def unsigned_integer(self, name: str) -> 'ColumnDefinition':
        col = Column(name, Integer, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def unsigned_big_integer(self, name: str) -> 'ColumnDefinition':
        col = Column(name, BigInteger, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    # ─── Float / Decimal ──────────────────────────────────────────────────────

    def float(self, name: str, precision: int = 8, scale: int = 2) -> 'ColumnDefinition':
        col = Column(name, Float, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def decimal(self, name: str, precision: int = 8, scale: int = 2) -> 'ColumnDefinition':
        col = Column(name, Numeric(precision=precision, scale=scale), nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def double(self, name: str) -> 'ColumnDefinition':
        return self.float(name)

    # ─── String Types ─────────────────────────────────────────────────────────

    def string(self, name: str, length: int = 255) -> 'ColumnDefinition':
        col = Column(name, String(length), nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def char(self, name: str, length: int = 1) -> 'ColumnDefinition':
        return self.string(name, length)

    def text(self, name: str) -> 'ColumnDefinition':
        col = Column(name, Text, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def long_text(self, name: str) -> 'ColumnDefinition':
        return self.text(name)

    def medium_text(self, name: str) -> 'ColumnDefinition':
        return self.text(name)

    def json(self, name: str) -> 'ColumnDefinition':
        return self.text(name)

    def jsonb(self, name: str) -> 'ColumnDefinition':
        return self.text(name)

    def enum(self, name: str, values: List[str]) -> 'ColumnDefinition':
        col = Column(name, String(50), nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def binary(self, name: str) -> 'ColumnDefinition':
        col = Column(name, LargeBinary, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def vector(self, name: str, dimensions: int = 1536) -> 'ColumnDefinition':
        """
        [ID] Kolom vector untuk semantic/similarity search, didukung oleh
        ekstensi `pgvector` di PostgreSQL (via SQLAlchemy). Wajib
        menjalankan `CREATE EXTENSION IF NOT EXISTS vector;` di database
        terlebih dahulu (lihat `Schema.enable_pgvector()`). Dimensi default
        1536 cocok untuk embedding model populer (mis. OpenAI
        text-embedding-3-small).

        [EN] A vector column for semantic/similarity search, backed by
        PostgreSQL's `pgvector` extension (via SQLAlchemy). Requires
        running `CREATE EXTENSION IF NOT EXISTS vector;` on the database
        first (see `Schema.enable_pgvector()`). The default dimension of
        1536 matches popular embedding models (e.g. OpenAI
        text-embedding-3-small).
        """
        if not _PGVECTOR_AVAILABLE:
            raise ImportError(
                "Column.vector() requires the 'pgvector' package. "
                "Install it with: pip install pgvector"
            )
        col = Column(name, Vector(dimensions), nullable=True)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    # ─── Boolean ──────────────────────────────────────────────────────────────

    def boolean(self, name: str) -> 'ColumnDefinition':
        col = Column(name, Boolean, nullable=False, default=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    # ─── Date / Time ──────────────────────────────────────────────────────────

    def date(self, name: str) -> 'ColumnDefinition':
        col = Column(name, Date, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def datetime(self, name: str) -> 'ColumnDefinition':
        col = Column(name, DateTime, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def timestamp(self, name: str) -> 'ColumnDefinition':
        return self.datetime(name)

    def timestamps(self):
        """Add created_at and updated_at columns."""
        self._columns.append(Column('created_at', DateTime, nullable=True))
        self._columns.append(Column('updated_at', DateTime, nullable=True))

    def soft_deletes(self, column: str = 'deleted_at'):
        """Add deleted_at column for soft deletes."""
        self._columns.append(Column(column, DateTime, nullable=True))

    def nullable_timestamps(self):
        self.timestamps()

    # ─── Foreign Keys ─────────────────────────────────────────────────────────

    def foreign_id(self, name: str) -> 'ColumnDefinition':
        col = Column(name, BigInteger, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def foreign(self, column: str) -> 'ForeignKeyDefinition':
        return ForeignKeyDefinition(column, self)

    # ─── Indexes & Unique ─────────────────────────────────────────────────────

    def unique(self, columns: List[str] | str, name: str = None):
        cols = [columns] if isinstance(columns, str) else columns
        self._constraints.append(UniqueConstraint(*cols, name=name))

    def index(self, columns: List[str] | str, name: str = None):
        cols = [columns] if isinstance(columns, str) else columns
        self._indexes.append(Index(name or f"idx_{'_'.join(cols)}", *cols))

    def primary(self, columns: List[str]):
        pass  # Handled by primary_key=True on column

    # ─── Utility ─────────────────────────────────────────────────────────────

    def remember_token(self):
        return self.string('remember_token', 100).nullable()

    def morphs(self, name: str):
        self.string(f"{name}_type")
        self.unsigned_big_integer(f"{name}_id")

    def nullable_morphs(self, name: str):
        self.string(f"{name}_type").nullable()
        self.unsigned_big_integer(f"{name}_id").nullable()

    def ip_address(self, name: str = 'ip_address') -> 'ColumnDefinition':
        return self.string(name, 45)

    def mac_address(self, name: str = 'mac_address') -> 'ColumnDefinition':
        return self.string(name, 17)

    def uuid(self, name: str = 'uuid') -> 'ColumnDefinition':
        return self.string(name, 36)

    def ul_id(self, name: str = 'ulid') -> 'ColumnDefinition':
        return self.string(name, 26)

    def get_columns(self) -> List[Column]:
        return self._columns

    def get_indexes(self) -> List[Any]:
        return self._indexes

    def get_constraints(self) -> List[Any]:
        return self._constraints


class ColumnDefinition:
    """Fluent column modifier — chain .nullable(), .default(), .unique()."""

    def __init__(self, column: Column, blueprint: Blueprint):
        self._column = column
        self._blueprint = blueprint

    def nullable(self) -> 'ColumnDefinition':
        self._column.nullable = True
        return self

    def default(self, value: Any) -> 'ColumnDefinition':
        self._column.default = value
        return self

    def unique(self) -> 'ColumnDefinition':
        self._column.unique = True
        return self

    def index(self) -> 'ColumnDefinition':
        self._blueprint.index([self._column.name])
        return self

    def unsigned(self) -> 'ColumnDefinition':
        return self

    def auto_increment(self) -> 'ColumnDefinition':
        self._column.autoincrement = True
        return self

    def comment(self, text: str) -> 'ColumnDefinition':
        self._column.comment = text
        return self

    def references(self, column: str) -> 'ForeignKeyDefinition':
        return ForeignKeyDefinition(self._column.name, self._blueprint).references(column)

    def on(self, table: str) -> 'ColumnDefinition':
        return self

    def on_delete(self, action: str) -> 'ColumnDefinition':
        return self

    def on_update(self, action: str) -> 'ColumnDefinition':
        return self


class ForeignKeyDefinition:
    def __init__(self, column: str, blueprint: Blueprint):
        self._column = column
        self._blueprint = blueprint
        self._references = None
        self._on_table = None
        self._on_delete_action = 'RESTRICT'
        self._on_update_action = 'CASCADE'

    def references(self, column: str) -> 'ForeignKeyDefinition':
        self._references = column
        return self

    def on(self, table: str) -> 'ForeignKeyDefinition':
        self._on_table = table
        return self

    def on_delete(self, action: str) -> 'ForeignKeyDefinition':
        self._on_delete_action = action
        return self

    def on_update(self, action: str) -> 'ForeignKeyDefinition':
        self._on_update_action = action
        return self

    def cascade_on_delete(self) -> 'ForeignKeyDefinition':
        return self.on_delete('CASCADE')

    def nullify_on_delete(self) -> 'ForeignKeyDefinition':
        return self.on_delete('SET NULL')


class Schema:
    """
    Schema builder — create, modify, and drop database tables.
    """

    _engine = None

    @classmethod
    def _get_engine(cls):
        from laraflask.orm.db import DB
        return DB.engine()

    @classmethod
    def create(cls, table_name: str, callback: Callable[[Blueprint], None]):
        """Create a new table."""
        engine = cls._get_engine()
        blueprint = Blueprint(table_name)
        callback(blueprint)

        metadata = MetaData()
        table = Table(
            table_name,
            metadata,
            *blueprint.get_columns(),
            *blueprint.get_constraints(),
        )

        metadata.create_all(engine)
        print(f"  ✓ Created table [{table_name}]")

    @classmethod
    def table(cls, table_name: str, callback: Callable[[Blueprint], None]):
        """Modify an existing table."""
        engine = cls._get_engine()
        blueprint = Blueprint(table_name)
        callback(blueprint)

        with engine.connect() as conn:
            inspector = sa_inspect(engine)
            existing = [col['name'] for col in inspector.get_columns(table_name)]

            for col in blueprint.get_columns():
                if col.name not in existing:
                    col_type = col.type.compile(engine.dialect)
                    nullable = "" if col.nullable else " NOT NULL"
                    default = f" DEFAULT {col.default.arg}" if col.default else ""
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{nullable}{default}"
                    ))
                    conn.commit()
                    print(f"  ✓ Added column [{col.name}] to [{table_name}]")

    @classmethod
    def drop(cls, table_name: str):
        """Drop a table."""
        engine = cls._get_engine()
        with engine.connect() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            conn.commit()
        print(f"  ✓ Dropped table [{table_name}]")

    @classmethod
    def drop_if_exists(cls, table_name: str):
        cls.drop(table_name)

    @classmethod
    def rename(cls, from_table: str, to_table: str):
        engine = cls._get_engine()
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {from_table} RENAME TO {to_table}"))
            conn.commit()

    @classmethod
    def enable_pgvector(cls):
        """
        [ID] Aktifkan ekstensi `pgvector` pada database PostgreSQL yang
        sedang dipakai. Wajib dijalankan sekali (mis. di migration paling
        awal) sebelum menggunakan `Blueprint.vector()` atau
        `QueryBuilder.order_by_similarity()`.

        [EN] Enable the `pgvector` extension on the currently-used
        PostgreSQL database. Must be run once (e.g. in the very first
        migration) before using `Blueprint.vector()` or
        `QueryBuilder.order_by_similarity()`.
        """
        engine = cls._get_engine()
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        print("  ✓ Enabled pgvector extension")

    @classmethod
    def has_table(cls, table_name: str) -> bool:
        engine = cls._get_engine()
        inspector = sa_inspect(engine)
        return table_name in inspector.get_table_names()

    @classmethod
    def has_column(cls, table_name: str, column: str) -> bool:
        engine = cls._get_engine()
        inspector = sa_inspect(engine)
        cols = [c['name'] for c in inspector.get_columns(table_name)]
        return column in cols

    @classmethod
    def get_column_listing(cls, table_name: str) -> List[str]:
        engine = cls._get_engine()
        inspector = sa_inspect(engine)
        return [c['name'] for c in inspector.get_columns(table_name)]


class Migration:
    """
    Base class for all database migrations.
    Override up() and down() to define schema changes.
    """

    def up(self):
        """Run the migration."""
        raise NotImplementedError

    def down(self):
        """Reverse the migration."""
        raise NotImplementedError


class Migrator:
    """
    Runs, rolls back, and tracks database migrations.
    """

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
            Table(
                self.MIGRATIONS_TABLE,
                metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('migration', String(255), nullable=False),
                Column('batch', Integer, nullable=False),
                Column('executed_at', DateTime, default=datetime.datetime.utcnow),
            )
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
        files = sorted([
            f for f in os.listdir(self._path)
            if f.endswith('.py') and not f.startswith('_')
        ])
        return files

    def _load_migration(self, filename: str) -> Migration:
        import importlib.util
        filepath = os.path.join(self._path, filename)
        spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find Migration subclass in module
        for attr in dir(module):
            obj = getattr(module, attr)
            if (isinstance(obj, type) and issubclass(obj, Migration)
                    and obj is not Migration):
                return obj()
        raise ValueError(f"No Migration class found in {filename}")

    def run(self) -> int:
        """Run all pending migrations."""
        ran = self._get_ran()
        batch = self._get_last_batch() + 1
        count = 0

        for filename in self._get_migration_files():
            name = filename[:-3]
            if name in ran:
                continue

            print(f"  Migrating: {name}")
            migration = self._load_migration(filename)
            migration.up()
            self._log_migration(name, batch)
            print(f"  ✓ Migrated:  {name}")
            count += 1

        return count

    def rollback(self, steps: int = 1) -> int:
        """Roll back the last batch of migrations."""
        from laraflask.orm.db import DB
        batch = self._get_last_batch()
        rows = DB.select(
            f"SELECT migration FROM {self.MIGRATIONS_TABLE} "
            f"WHERE batch = {batch} ORDER BY id DESC"
        )
        count = 0
        for row in rows:
            name = row['migration']
            filename = f"{name}.py"
            print(f"  Rolling back: {name}")
            migration = self._load_migration(filename)
            migration.down()
            DB.delete(
                f"DELETE FROM {self.MIGRATIONS_TABLE} WHERE migration = :m",
                {'m': name}
            )
            print(f"  ✓ Rolled back: {name}")
            count += 1

        return count

    def reset(self) -> int:
        """Roll back all migrations."""
        from laraflask.orm.db import DB
        rows = DB.select(
            f"SELECT migration FROM {self.MIGRATIONS_TABLE} ORDER BY id DESC"
        )
        count = 0
        for row in rows:
            name = row['migration']
            filename = f"{name}.py"
            if os.path.exists(os.path.join(self._path, filename)):
                migration = self._load_migration(filename)
                migration.down()
            DB.delete(
                f"DELETE FROM {self.MIGRATIONS_TABLE} WHERE migration = :m",
                {'m': name}
            )
            count += 1
        return count

    def fresh(self):
        """Drop all tables and re-run all migrations."""
        from laraflask.orm.db import DB
        DB.drop_all()
        self._ensure_migrations_table()
        return self.run()

    def _log_migration(self, name: str, batch: int):
        from laraflask.orm.db import DB
        DB.insert(
            f"INSERT INTO {self.MIGRATIONS_TABLE} (migration, batch, executed_at) "
            f"VALUES (:migration, :batch, :executed_at)",
            {
                'migration': name,
                'batch': batch,
                'executed_at': datetime.datetime.utcnow().isoformat(),
            }
        )

    def status(self) -> List[Dict]:
        ran = set(self._get_ran())
        return [
            {
                'migration': f[:-3],
                'ran': f[:-3] in ran,
            }
            for f in self._get_migration_files()
        ]
