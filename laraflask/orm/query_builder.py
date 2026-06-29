"""QueryBuilder - Fluent query builder for EloquentPy models."""

from __future__ import annotations
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, TypeVar, TYPE_CHECKING

from laraflask.core.exceptions import ModelNotFoundException
from laraflask.core.macroable import Macroable

if TYPE_CHECKING:
    from laraflask.core.collection import Collection
    from laraflask.orm._model import Model


class QueryBuilder(Macroable):
    """
    Fluent query builder for EloquentPy models.
    Chainable interface like Laravel's Query Builder.
    """

    def __init__(self, model_class: Type['Model']):
        self._model = model_class
        self._wheres: List[Dict] = []
        self._order_bys: List[Dict] = []
        self._limit_val: Optional[int] = None
        self._offset_val: Optional[int] = None
        self._with_relations: List[str] = []
        self._selects: List[str] = ['*']
        self._joins: List[Dict] = []
        self._groups: List[str] = []
        self._havings: List[Dict] = []
        self._distinct_flag = False
        self._include_trashed = False
        self._only_trashed = False
        self._similarity_order: Optional[Dict[str, Any]] = None

    def select(self, *columns: str) -> 'QueryBuilder':
        self._selects = list(columns)
        return self

    def distinct(self) -> 'QueryBuilder':
        self._distinct_flag = True
        return self

    def where(self, column: str, operator_or_value: Any = None,
              value: Any = None) -> 'QueryBuilder':
        if value is None:
            value = operator_or_value
            operator = '='
        else:
            operator = operator_or_value
        self._wheres.append({
            'type': 'basic', 'column': column,
            'operator': operator, 'value': value, 'boolean': 'AND',
        })
        return self

    def or_where(self, column: str, operator_or_value: Any = None,
                 value: Any = None) -> 'QueryBuilder':
        if value is None:
            value = operator_or_value
            operator = '='
        else:
            operator = operator_or_value
        self._wheres.append({
            'type': 'basic', 'column': column,
            'operator': operator, 'value': value, 'boolean': 'OR',
        })
        return self

    def where_in(self, column: str, values: List) -> 'QueryBuilder':
        self._wheres.append({'type': 'in', 'column': column, 'values': values, 'boolean': 'AND'})
        return self

    def where_not_in(self, column: str, values: List) -> 'QueryBuilder':
        self._wheres.append({'type': 'not_in', 'column': column, 'values': values, 'boolean': 'AND'})
        return self

    def where_null(self, column: str) -> 'QueryBuilder':
        self._wheres.append({'type': 'null', 'column': column, 'boolean': 'AND'})
        return self

    def where_not_null(self, column: str) -> 'QueryBuilder':
        self._wheres.append({'type': 'not_null', 'column': column, 'boolean': 'AND'})
        return self

    def where_between(self, column: str, values: List) -> 'QueryBuilder':
        self._wheres.append({'type': 'between', 'column': column, 'values': values, 'boolean': 'AND'})
        return self

    def where_like(self, column: str, pattern: str) -> 'QueryBuilder':
        return self.where(column, 'LIKE', pattern)

    def order_by(self, column: str, direction: str = 'ASC') -> 'QueryBuilder':
        self._order_bys.append({'column': column, 'direction': direction.upper()})
        return self

    def order_by_desc(self, column: str) -> 'QueryBuilder':
        return self.order_by(column, 'DESC')

    def latest(self, column: str = 'created_at') -> 'QueryBuilder':
        return self.order_by_desc(column)

    def oldest(self, column: str = 'created_at') -> 'QueryBuilder':
        return self.order_by(column, 'ASC')

    def order_by_similarity(self, column: str, vector: List[float],
                            limit: int = 10, metric: str = 'cosine') -> 'QueryBuilder':
        valid_metrics = ('cosine', 'l2', 'inner_product')
        if metric not in valid_metrics:
            raise ValueError(f"Unsupported similarity metric '{metric}'. Use one of: {valid_metrics}")
        self._similarity_order = {'column': column, 'vector': vector, 'metric': metric}
        if self._limit_val is None:
            self._limit_val = limit
        return self

    def limit(self, value: int) -> 'QueryBuilder':
        self._limit_val = value
        return self

    def take(self, value: int) -> 'QueryBuilder':
        return self.limit(value)

    def offset(self, value: int) -> 'QueryBuilder':
        self._offset_val = value
        return self

    def skip(self, value: int) -> 'QueryBuilder':
        return self.offset(value)

    def paginate(self, per_page: int = 15, page: int = 1) -> Dict:
        total = self.count()
        items = self.offset((page - 1) * per_page).limit(per_page).get()
        return {
            'data': items, 'total': total, 'per_page': per_page,
            'current_page': page,
            'last_page': max(1, (total + per_page - 1) // per_page),
            'from': (page - 1) * per_page + 1 if total else 0,
            'to': min(page * per_page, total),
        }

    def with_relations(self, *relations: str) -> 'QueryBuilder':
        self._with_relations.extend(relations)
        return self

    def join(self, table: str, first: str, operator: str, second: str,
             join_type: str = 'INNER') -> 'QueryBuilder':
        self._joins.append({
            'table': table, 'first': first,
            'operator': operator, 'second': second, 'type': join_type,
        })
        return self

    def left_join(self, table: str, first: str, operator: str, second: str) -> 'QueryBuilder':
        return self.join(table, first, operator, second, 'LEFT')

    def right_join(self, table: str, first: str, operator: str, second: str) -> 'QueryBuilder':
        return self.join(table, first, operator, second, 'RIGHT')

    def _build_query(self):
        from laraflask.orm.db import DB
        session = DB.session()
        db_model = self._model._get_db_model()
        if db_model is None:
            return None
        query = session.query(db_model)

        for where in self._wheres:
            wtype = where['type']
            col = getattr(db_model, where['column'], None)
            if col is None:
                continue
            if wtype == 'basic':
                op = where['operator']
                val = where['value']
                if op == '=':      query = query.filter(col == val)
                elif op == '!=':   query = query.filter(col != val)
                elif op == '>':    query = query.filter(col > val)
                elif op == '>=':   query = query.filter(col >= val)
                elif op == '<':    query = query.filter(col < val)
                elif op == '<=':   query = query.filter(col <= val)
                elif op == 'LIKE': query = query.filter(col.like(val))
            elif wtype == 'in':
                query = query.filter(col.in_(where['values']))
            elif wtype == 'not_in':
                query = query.filter(~col.in_(where['values']))
            elif wtype == 'null':
                query = query.filter(col.is_(None))
            elif wtype == 'not_null':
                query = query.filter(col.isnot(None))
            elif wtype == 'between':
                query = query.filter(col.between(*where['values']))

        if self._model.__soft_delete__ and not self._include_trashed:
            deleted_col = getattr(db_model, 'deleted_at', None)
            if deleted_col is not None:
                if self._only_trashed:
                    query = query.filter(deleted_col.isnot(None))
                else:
                    query = query.filter(deleted_col.is_(None))

        for ob in self._order_bys:
            col = getattr(db_model, ob['column'], None)
            if col is not None:
                query = query.order_by(col.desc() if ob['direction'] == 'DESC' else col)

        if self._similarity_order is not None:
            query = self._apply_similarity_order(query, db_model)

        if self._limit_val is not None:
            query = query.limit(self._limit_val)
        if self._offset_val is not None:
            query = query.offset(self._offset_val)

        return query

    def _apply_similarity_order(self, query, db_model):
        order = self._similarity_order
        col = getattr(db_model, order['column'], None)
        if col is None:
            return query
        metric = order['metric']
        vector = order['vector']
        if metric == 'cosine':
            distance_expr = col.cosine_distance(vector)
        elif metric == 'l2':
            distance_expr = col.l2_distance(vector)
        elif metric == 'inner_product':
            distance_expr = col.max_inner_product(vector)
        else:
            return query
        return query.order_by(distance_expr)

    def get(self, as_collection: bool = False) -> 'List[Model] | Collection':
        query = self._build_query()
        if query is None:
            results = []
        else:
            db_results = query.all()
            results = [self._model._from_db(r) for r in db_results]
            if self._with_relations:
                for relation in self._with_relations:
                    for model_instance in results:
                        if hasattr(model_instance, relation):
                            getattr(model_instance, relation)
        if as_collection:
            from laraflask.core.collection import Collection
            return Collection(results)
        return results

    def first(self) -> Optional['Model']:
        query = self._build_query()
        if query is None:
            return None
        result = query.first()
        return self._model._from_db(result) if result else None

    def first_or_fail(self) -> 'Model':
        result = self.first()
        if result is None:
            raise ModelNotFoundException(self._model.__name__)
        return result

    def find(self, id: Any) -> Optional['Model']:
        return self.where('id', id).first()

    def find_or_fail(self, id: Any) -> 'Model':
        result = self.where('id', id).first()
        if result is None:
            raise ModelNotFoundException(self._model.__name__, id)
        return result

    def count(self) -> int:
        query = self._build_query()
        return query.count() if query is not None else 0

    def exists(self) -> bool:
        return self.count() > 0

    def doesnt_exist(self) -> bool:
        return not self.exists()

    def sum(self, column: str) -> float:
        from sqlalchemy import func
        from laraflask.orm.db import DB
        db_model = self._model._get_db_model()
        col = getattr(db_model, column)
        result = DB.session().query(func.sum(col)).scalar()
        return result or 0

    def avg(self, column: str) -> float:
        from sqlalchemy import func
        from laraflask.orm.db import DB
        db_model = self._model._get_db_model()
        col = getattr(db_model, column)
        result = DB.session().query(func.avg(col)).scalar()
        return result or 0

    def max(self, column: str) -> Any:
        from sqlalchemy import func
        from laraflask.orm.db import DB
        db_model = self._model._get_db_model()
        col = getattr(db_model, column)
        return DB.session().query(func.max(col)).scalar()

    def min(self, column: str) -> Any:
        from sqlalchemy import func
        from laraflask.orm.db import DB
        db_model = self._model._get_db_model()
        col = getattr(db_model, column)
        return DB.session().query(func.min(col)).scalar()

    def delete(self) -> int:
        query = self._build_query()
        if query is None:
            return 0
        count = query.count()
        query.delete(synchronize_session=False)
        from laraflask.orm.db import DB
        DB.session().commit()
        return count

    def update(self, values: Dict) -> int:
        query = self._build_query()
        if query is None:
            return 0
        count = query.update(values, synchronize_session=False)
        from laraflask.orm.db import DB
        DB.session().commit()
        return count

    def chunk(self, size: int, callback: callable) -> None:
        page = 1
        while True:
            results = self.offset((page - 1) * size).limit(size).get()
            if not results:
                break
            callback(results)
            if len(results) < size:
                break
            page += 1

    def each(self, callback: callable) -> None:
        for item in self.get():
            callback(item)

    def pluck(self, column: str, key: str = None) -> 'List | Dict':
        items = self.get()
        if key:
            return {getattr(item, key): getattr(item, column) for item in items}
        return [getattr(item, column) for item in items]

    def to_list(self) -> List[Dict]:
        return [item.to_dict() for item in self.get()]
