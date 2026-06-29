"""
Laraflask Database Manager
Re-export hub for backward compatibility.
"""

from laraflask.orm.base import Base
from laraflask.orm.database_manager import DatabaseManager
from laraflask.orm.raw_query_builder import RawQueryBuilder

# Global singleton instance
DB = DatabaseManager()

__all__ = [
    'Base',
    'DatabaseManager',
    'RawQueryBuilder',
    'DB',
]
