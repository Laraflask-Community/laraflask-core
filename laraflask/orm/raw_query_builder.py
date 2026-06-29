"""RawQueryBuilder - Fluent raw query builder for quick DB::table() queries."""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class RawQueryBuilder:
    """Fluent raw query builder for quick DB::table() queries."""

    def __init__(self, db: 'DatabaseManager', table: str):
        self._db = db
        self._table = table
        self._wheres: list = []
        self._selects: list = ['*']
        self._limit_val: Optional[int] = None
        self._order_bys: list = []

    def select(self, *cols) -> 'RawQueryBuilder':
        self._selects = list(cols)
        return self

    def where(self, col: str, val: Any) -> 'RawQueryBuilder':
        self._wheres.append((col, val))
        return self

    def limit(self, n: int) -> 'RawQueryBuilder':
        self._limit_val = n
        return self

    def order_by(self, col: str, direction: str = 'ASC') -> 'RawQueryBuilder':
        self._order_bys.append(f"{col} {direction}")
        return self

    def _build(self) -> tuple:
        cols = ', '.join(self._selects)
        sql = f"SELECT {cols} FROM {self._table}"
        bindings = {}
        if self._wheres:
            clauses = []
            for i, (col, val) in enumerate(self._wheres):
                param = f"p{i}"
                clauses.append(f"{col} = :{param}")
                bindings[param] = val
            sql += " WHERE " + " AND ".join(clauses)
        if self._order_bys:
            sql += " ORDER BY " + ", ".join(self._order_bys)
        if self._limit_val:
            sql += f" LIMIT {self._limit_val}"
        return sql, bindings

    def get(self) -> list:
        sql, bindings = self._build()
        return self._db.select(sql, bindings)

    def first(self) -> Optional[Dict]:
        results = self.limit(1).get()
        return results[0] if results else None

    def insert(self, data: Dict) -> bool:
        cols = ', '.join(data.keys())
        params = ', '.join(f":{k}" for k in data.keys())
        sql = f"INSERT INTO {self._table} ({cols}) VALUES ({params})"
        return self._db.insert(sql, data)

    def update(self, data: Dict) -> int:
        set_clause = ', '.join(f"{k} = :{k}" for k in data.keys())
        sql = f"UPDATE {self._table} SET {set_clause}"
        bindings = dict(data)
        if self._wheres:
            clauses = []
            for i, (col, val) in enumerate(self._wheres):
                param = f"w{i}"
                clauses.append(f"{col} = :{param}")
                bindings[param] = val
            sql += " WHERE " + " AND ".join(clauses)
        return self._db.update(sql, bindings)

    def delete(self) -> int:
        sql = f"DELETE FROM {self._table}"
        bindings = {}
        if self._wheres:
            clauses = []
            for i, (col, val) in enumerate(self._wheres):
                param = f"p{i}"
                clauses.append(f"{col} = :{param}")
                bindings[param] = val
            sql += " WHERE " + " AND ".join(clauses)
        return self._db.delete(sql, bindings)

    def count(self) -> int:
        sql = f"SELECT COUNT(*) as cnt FROM {self._table}"
        bindings = {}
        if self._wheres:
            clauses = []
            for i, (col, val) in enumerate(self._wheres):
                param = f"p{i}"
                clauses.append(f"{col} = :{param}")
                bindings[param] = val
            sql += " WHERE " + " AND ".join(clauses)
        result = self._db.select(sql, bindings)
        return result[0]['cnt'] if result else 0
