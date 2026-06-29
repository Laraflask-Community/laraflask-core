"""Schema - Schema builder for creating, modifying, and dropping database tables."""

from __future__ import annotations
from typing import Callable, List

try:
    from sqlalchemy import MetaData, Table, inspect as sa_inspect, text
    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False
    MetaData = Table = sa_inspect = text = None

from laraflask.orm.blueprint import Blueprint


class Schema:
    """Schema builder - create, modify, and drop database tables."""

    _engine = None

    @classmethod
    def _get_engine(cls):
        from laraflask.orm.db import DB
        return DB.engine()

    @classmethod
    def create(cls, table_name: str, callback: Callable[[Blueprint], None]):
        engine = cls._get_engine()
        blueprint = Blueprint(table_name)
        callback(blueprint)
        metadata = MetaData()
        table = Table(table_name, metadata, *blueprint.get_columns(), *blueprint.get_constraints())
        metadata.create_all(engine)

    @classmethod
    def table(cls, table_name: str, callback: Callable[[Blueprint], None]):
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
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{nullable}{default}"))
                    conn.commit()

    @classmethod
    def drop(cls, table_name: str):
        engine = cls._get_engine()
        with engine.connect() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            conn.commit()

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
        engine = cls._get_engine()
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

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
