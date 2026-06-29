"""ModelMeta - Metaclass that sets up table name and attribute tracking."""

from __future__ import annotations
import re


class ModelMeta(type):
    """Metaclass that sets up table name and attribute tracking."""

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        if name != 'Model' and not getattr(cls, '_abstract', False):
            if not hasattr(cls, '__table__') or cls.__table__ is None:
                cls.__table__ = mcs._to_table_name(name)

        return cls

    @staticmethod
    def _to_table_name(class_name: str) -> str:
        """Convert CamelCase class name to snake_case plural table name."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        snake = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        if snake.endswith('y'):
            return snake[:-1] + 'ies'
        elif snake.endswith(('s', 'x', 'ch', 'sh')):
            return snake + 'es'
        return snake + 's'
