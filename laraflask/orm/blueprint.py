"""Blueprint - Schema blueprint for defining table columns and indexes."""

from __future__ import annotations
from typing import Any, List

try:
    from sqlalchemy import (
        Column, Integer, String, Text, Boolean, Float, DateTime,
        Date, BigInteger, SmallInteger, Numeric, LargeBinary,
        ForeignKey, UniqueConstraint, Index,
    )
    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False
    Column = Integer = String = Text = Boolean = Float = DateTime = None
    Date = BigInteger = SmallInteger = Numeric = LargeBinary = None
    ForeignKey = UniqueConstraint = Index = None

try:
    from pgvector.sqlalchemy import Vector
    _PGVECTOR_AVAILABLE = True
except ImportError:
    _PGVECTOR_AVAILABLE = False
    Vector = None

from laraflask.orm.column_definition import ColumnDefinition
from laraflask.orm.foreign_key_definition import ForeignKeyDefinition


class Blueprint:
    """Schema blueprint - define table columns and indexes."""

    def __init__(self, table: str, prefix: str = ''):
        self.table = table
        self.prefix = prefix
        self._columns: List = []
        self._indexes: List[Any] = []
        self._constraints: List[Any] = []
        self._commands: List = []

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
        if not _PGVECTOR_AVAILABLE:
            raise ImportError("Column.vector() requires the 'pgvector' package.")
        col = Column(name, Vector(dimensions), nullable=True)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def boolean(self, name: str) -> 'ColumnDefinition':
        col = Column(name, Boolean, nullable=False, default=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

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
        self._columns.append(Column('created_at', DateTime, nullable=True))
        self._columns.append(Column('updated_at', DateTime, nullable=True))

    def soft_deletes(self, column: str = 'deleted_at'):
        self._columns.append(Column(column, DateTime, nullable=True))

    def nullable_timestamps(self):
        self.timestamps()

    def foreign_id(self, name: str) -> 'ColumnDefinition':
        col = Column(name, BigInteger, nullable=False)
        self._columns.append(col)
        return ColumnDefinition(col, self)

    def foreign(self, column: str) -> 'ForeignKeyDefinition':
        return ForeignKeyDefinition(column, self)

    def unique(self, columns, name: str = None):
        cols = [columns] if isinstance(columns, str) else columns
        self._constraints.append(UniqueConstraint(*cols, name=name))

    def index(self, columns, name: str = None):
        cols = [columns] if isinstance(columns, str) else columns
        self._indexes.append(Index(name or f"idx_{'_'.join(cols)}", *cols))

    def primary(self, columns: List[str]):
        pass

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

    def get_columns(self) -> List:
        return self._columns

    def get_indexes(self) -> List[Any]:
        return self._indexes

    def get_constraints(self) -> List[Any]:
        return self._constraints
