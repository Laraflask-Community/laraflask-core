"""Base - SQLAlchemy DeclarativeBase."""

from __future__ import annotations
try:
    from sqlalchemy.orm import DeclarativeBase
    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False
    class DeclarativeBase:
        pass


class Base(DeclarativeBase):
    pass
