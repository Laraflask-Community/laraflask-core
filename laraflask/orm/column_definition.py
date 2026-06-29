"""ColumnDefinition - Fluent column modifier."""

from __future__ import annotations
from typing import Any

from laraflask.orm.foreign_key_definition import ForeignKeyDefinition


class ColumnDefinition:
    """Fluent column modifier - chain .nullable(), .default(), .unique()."""

    def __init__(self, column, blueprint: 'Blueprint'):
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
