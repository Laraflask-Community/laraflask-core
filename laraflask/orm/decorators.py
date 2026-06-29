"""ORM Decorators - table, hidden, fillable."""

from __future__ import annotations
from typing import Callable, Type, TypeVar

M = TypeVar('M', bound='Model')


def table(name: str, primary_key: str = None) -> 'Callable[[Type[M]], Type[M]]':
    """Set the table name (and optionally the primary key) for a Model via decorator."""
    def decorator(cls: Type[M]) -> Type[M]:
        cls.__table__ = name
        if primary_key is not None:
            cls.__primary_key__ = primary_key
        return cls
    return decorator


def hidden(*fields: str) -> 'Callable[[Type[M]], Type[M]]':
    """Set the fields hidden from to_dict()/to_json() via decorator."""
    def decorator(cls: Type[M]) -> Type[M]:
        cls.__hidden__ = list(fields)
        return cls
    return decorator


def fillable(*fields: str) -> 'Callable[[Type[M]], Type[M]]':
    """Set the mass-assignable fields via decorator."""
    def decorator(cls: Type[M]) -> Type[M]:
        cls.__fillable__ = list(fields)
        return cls
    return decorator
