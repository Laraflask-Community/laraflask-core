"""ForeignKeyDefinition - Foreign key constraint builder."""

from __future__ import annotations


class ForeignKeyDefinition:
    def __init__(self, column: str, blueprint: 'Blueprint'):
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
