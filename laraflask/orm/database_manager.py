"""DatabaseManager - Manages database connections and sessions."""

from __future__ import annotations
import os
from typing import Any, Dict, Optional

try:
    from sqlalchemy import create_engine, text, MetaData, Table
    from sqlalchemy.orm import sessionmaker, scoped_session
    from sqlalchemy.pool import QueuePool, StaticPool, NullPool
    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False

from laraflask.orm.base import Base
from laraflask.orm.raw_query_builder import RawQueryBuilder


class DatabaseManager:
    """
    Manages database connections and sessions.
    Supports multiple connections defined in config/database.py
    """

    _instance: Optional['DatabaseManager'] = None
    _engines: Dict[str, Any] = {}
    _sessions: Dict[str, Any] = {}
    _models: Dict[str, Any] = {}
    _metadata: MetaData = MetaData() if _SA_AVAILABLE else None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self, connection_name: str = 'default', url: str = None) -> 'DatabaseManager':
        """Establish a database connection."""
        if url is None:
            url = self._build_url(connection_name)

        if url.startswith('sqlite://'):
            if ':memory:' in url:
                engine = create_engine(
                    url,
                    connect_args={'check_same_thread': False},
                    poolclass=StaticPool,
                    echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
                )
            else:
                engine = create_engine(
                    url,
                    connect_args={'check_same_thread': False},
                    poolclass=NullPool,
                    echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
                )
        else:
            engine = create_engine(
                url,
                poolclass=QueuePool,
                pool_size=int(os.getenv('DB_POOL_SIZE', 5)),
                max_overflow=int(os.getenv('DB_POOL_OVERFLOW', 10)),
                pool_pre_ping=True,
                echo=os.getenv('DB_ECHO', 'false').lower() == 'true',
            )

        session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=True)
        self._engines[connection_name] = engine
        self._sessions[connection_name] = scoped_session(session_factory)
        return self

    def _build_url(self, name: str) -> str:
        driver = os.getenv('DB_CONNECTION', 'sqlite')
        if driver == 'sqlite':
            path = os.getenv('DB_DATABASE', './database/laraflask.db')
            return f"sqlite:///{path}"
        elif driver == 'mysql':
            return (f"mysql+pymysql://{os.getenv('DB_USERNAME')}:"
                    f"{os.getenv('DB_PASSWORD')}@"
                    f"{os.getenv('DB_HOST', '127.0.0.1')}:"
                    f"{os.getenv('DB_PORT', '3306')}/"
                    f"{os.getenv('DB_DATABASE')}")
        elif driver == 'postgresql':
            return (f"postgresql+psycopg2://{os.getenv('DB_USERNAME')}:"
                    f"{os.getenv('DB_PASSWORD')}@"
                    f"{os.getenv('DB_HOST', '127.0.0.1')}:"
                    f"{os.getenv('DB_PORT', '5432')}/"
                    f"{os.getenv('DB_DATABASE')}")
        raise ValueError(f"Unsupported DB driver: {driver}")

    def session(self, connection: str = 'default'):
        if connection not in self._sessions:
            self.connect(connection)
        return self._sessions[connection]

    def engine(self, connection: str = 'default'):
        if connection not in self._engines:
            self.connect(connection)
        return self._engines[connection]

    def get_model(self, table_name: str):
        if table_name in self._models:
            return self._models[table_name]

        engine = self.engine()
        try:
            table = Table(table_name, self._metadata, autoload_with=engine)
            model_class = type(
                f"_{table_name.title().replace('_', '')}",
                (Base,),
                {'__table__': table, '__tablename__': table_name},
            )
            self._models[table_name] = model_class
            return model_class
        except Exception:
            return None

    def register_model(self, table_name: str, model_class: Any):
        self._models[table_name] = model_class

    def create_all(self):
        Base.metadata.create_all(self.engine())

    def drop_all(self):
        Base.metadata.drop_all(self.engine())

    def select(self, query: str, bindings: Dict = None) -> list:
        with self.engine().connect() as conn:
            result = conn.execute(text(query), bindings or {})
            return [dict(row._mapping) for row in result]

    def statement(self, query: str, bindings: Dict = None) -> bool:
        with self.engine().connect() as conn:
            conn.execute(text(query), bindings or {})
            conn.commit()
            return True

    def insert(self, query: str, bindings: Dict = None) -> bool:
        return self.statement(query, bindings)

    def update(self, query: str, bindings: Dict = None) -> int:
        with self.engine().connect() as conn:
            result = conn.execute(text(query), bindings or {})
            conn.commit()
            return result.rowcount

    def delete(self, query: str, bindings: Dict = None) -> int:
        return self.update(query, bindings)

    def transaction(self, callback):
        session = self.session()
        try:
            result = callback(session)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise e

    def table(self, table_name: str) -> 'RawQueryBuilder':
        return RawQueryBuilder(self, table_name)

    def begin_transaction(self):
        self.session().begin_nested()

    def commit(self):
        self.session().commit()

    def rollback(self):
        self.session().rollback()

    def close(self):
        for session in self._sessions.values():
            session.remove()
