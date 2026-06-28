"""
EloquentPy ORM
Laravel-inspired Eloquent ORM for Python — elegant Active Record implementation.
"""

from __future__ import annotations
import re
import datetime
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, TypeVar, TYPE_CHECKING

# Import exceptions from single source of truth
from laraflask.core.exceptions import ModelNotFoundException
from laraflask.core.macroable import Macroable

if TYPE_CHECKING:
    from laraflask.core.collection import Collection

M = TypeVar('M', bound='Model')


# ─── Decorator-based Model Config ──────────────────────────────────────────────
#
# [ID] Alternatif gaya deklaratif untuk konfigurasi Model, terinspirasi dari
# PHP Attributes di Laravel 13 (`#[Table('users')]`, dst), diadaptasikan ke
# idiom Python sebagai class decorator. Decorator ini berjalan SETELAH
# class selesai dibuat oleh `ModelMeta` (termasuk auto-inferensi nama tabel),
# sehingga nilai yang diberikan decorator akan menimpa nilai default/auto —
# sama seperti menulis `__table__`/`__hidden__`/`__fillable__` secara manual.
# Model lama yang masih menulis atribut class secara manual tetap berfungsi
# tanpa perubahan apa pun (sepenuhnya backward compatible) karena decorator
# bersifat opsional dan hanya memodifikasi atribut yang sudah ada.
#
# [EN] A declarative alternative for Model configuration, inspired by
# Laravel 13's PHP Attributes (`#[Table('users')]`, etc.), adapted to
# Python idioms as class decorators. These decorators run AFTER the class
# has been fully built by `ModelMeta` (including table-name
# auto-inference), so values provided by the decorator override the
# default/inferred ones — exactly like writing `__table__`/`__hidden__`/
# `__fillable__` manually. Existing models that still declare these as
# manual class attributes keep working unchanged (fully backward
# compatible), since the decorators are optional and only mutate
# attributes that already exist on the class.

def table(name: str, primary_key: str = None) -> 'Callable[[Type[M]], Type[M]]':
    """
    [ID] Set nama tabel (dan opsional primary key) untuk sebuah Model lewat
    decorator, sebagai alternatif menulis `__table__`/`__primary_key__`
    secara manual. Contoh:

        @table(name='users', primary_key='user_id')
        class User(Model):
            ...

    [EN] Set the table name (and optionally the primary key) for a Model
    via decorator, as an alternative to manually writing
    `__table__`/`__primary_key__`. Example above.
    """
    def decorator(cls: Type[M]) -> Type[M]:
        cls.__table__ = name
        if primary_key is not None:
            cls.__primary_key__ = primary_key
        return cls
    return decorator


def hidden(*fields: str) -> 'Callable[[Type[M]], Type[M]]':
    """
    [ID] Set field yang disembunyikan dari `to_dict()`/`to_json()` lewat
    decorator, sebagai alternatif menulis `__hidden__` secara manual.
    Contoh: `@hidden('password', 'remember_token')`.

    [EN] Set the fields hidden from `to_dict()`/`to_json()` via decorator,
    as an alternative to manually writing `__hidden__`. Example:
    `@hidden('password', 'remember_token')`.
    """
    def decorator(cls: Type[M]) -> Type[M]:
        cls.__hidden__ = list(fields)
        return cls
    return decorator


def fillable(*fields: str) -> 'Callable[[Type[M]], Type[M]]':
    """
    [ID] Set field yang boleh diisi secara mass-assignment lewat decorator,
    sebagai alternatif menulis `__fillable__` secara manual.
    Contoh: `@fillable('name', 'email')`.

    [EN] Set the mass-assignable fields via decorator, as an alternative to
    manually writing `__fillable__`. Example: `@fillable('name', 'email')`.
    """
    def decorator(cls: Type[M]) -> Type[M]:
        cls.__fillable__ = list(fields)
        return cls
    return decorator


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


class QueryBuilder(Macroable):
    """
    Fluent query builder for EloquentPy models.
    Chainable interface like Laravel's Query Builder.

    [ID] Mewarisi `Macroable` sehingga method baru bisa ditambahkan secara
    dinamis saat runtime, mis. `QueryBuilder.macro('whereActive', lambda self: self.where('active', True))`.
    [EN] Inherits `Macroable` so new methods can be registered dynamically
    at runtime, e.g. `QueryBuilder.macro('whereActive', lambda self: self.where('active', True))`.
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

    # ─── Selection ────────────────────────────────────────────────────────────

    def select(self, *columns: str) -> 'QueryBuilder':
        self._selects = list(columns)
        return self

    def distinct(self) -> 'QueryBuilder':
        self._distinct_flag = True
        return self

    # ─── Where Clauses ────────────────────────────────────────────────────────

    def where(self, column: str, operator_or_value: Any = None,
              value: Any = None) -> 'QueryBuilder':
        if value is None:
            value = operator_or_value
            operator = '='
        else:
            operator = operator_or_value

        self._wheres.append({
            'type': 'basic',
            'column': column,
            'operator': operator,
            'value': value,
            'boolean': 'AND',
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
            'type': 'basic',
            'column': column,
            'operator': operator,
            'value': value,
            'boolean': 'OR',
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

    # ─── Ordering / Limiting ──────────────────────────────────────────────────

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
        """
        [ID] Urutkan hasil berdasarkan kemiripan (similarity) terhadap
        `vector` pada kolom vector `column` — untuk semantic search via
        pgvector di PostgreSQL. Otomatis mengatur `limit()` ke `limit`
        kecuali sudah di-set sebelumnya secara eksplisit. Pilihan `metric`:
        'cosine' (default, cocok untuk embedding ternormalisasi), 'l2'
        (Euclidean), atau 'inner_product'.

        Contoh: `Article.query().order_by_similarity('embedding', query_vector, limit=5).get()`

        [EN] Order results by similarity to `vector` on the vector column
        `column` — for semantic search via PostgreSQL's pgvector. Also sets
        `limit()` to `limit` unless one was already set explicitly.
        `metric` options: 'cosine' (default, suited for normalized
        embeddings), 'l2' (Euclidean), or 'inner_product'.

        Example: `Article.query().order_by_similarity('embedding', query_vector, limit=5).get()`
        """
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
            'data': items,
            'total': total,
            'per_page': per_page,
            'current_page': page,
            'last_page': max(1, (total + per_page - 1) // per_page),
            'from': (page - 1) * per_page + 1 if total else 0,
            'to': min(page * per_page, total),
        }

    # ─── Eager Loading ────────────────────────────────────────────────────────

    def with_relations(self, *relations: str) -> 'QueryBuilder':
        self._with_relations.extend(relations)
        return self

    # ─── Joins ────────────────────────────────────────────────────────────────

    def join(self, table: str, first: str, operator: str, second: str,
             join_type: str = 'INNER') -> 'QueryBuilder':
        self._joins.append({
            'table': table, 'first': first,
            'operator': operator, 'second': second,
            'type': join_type,
        })
        return self

    def left_join(self, table: str, first: str, operator: str, second: str) -> 'QueryBuilder':
        return self.join(table, first, operator, second, 'LEFT')

    def right_join(self, table: str, first: str, operator: str, second: str) -> 'QueryBuilder':
        return self.join(table, first, operator, second, 'RIGHT')

    # ─── Execution ────────────────────────────────────────────────────────────

    def _build_query(self):
        """Build and return a SQLAlchemy query."""
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

        # Soft delete filter
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
        """
        [ID] Terapkan pengurutan berdasarkan jarak vektor (pgvector) ke
        query SQLAlchemy. Operator yang dipilih mengikuti `metric`: cosine
        distance (`<=>`), L2/Euclidean distance (`<->`), atau negative inner
        product (`<#>`) — ketiganya disediakan langsung oleh ekstensi
        pgvector lewat method pada kolom hasil reflect.

        [EN] Apply vector-distance ordering (pgvector) to the SQLAlchemy
        query. The operator chosen follows `metric`: cosine distance
        (`<=>`), L2/Euclidean distance (`<->`), or negative inner product
        (`<#>`) — all three are provided directly by the pgvector
        extension via methods on the reflected column.
        """
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
        """
        [ID] Eksekusi query dan kembalikan semua hasil. Secara default tetap
        mengembalikan `list` Python biasa (backward compatible). Set
        `as_collection=True` untuk mendapatkan hasil yang dibungkus dalam
        `Collection` ber-method-chaining (map, filter, pluck, dst).

        [EN] Execute the query and return all results. By default this still
        returns a plain Python `list` (backward compatible). Pass
        `as_collection=True` to get the results wrapped in a chainable
        `Collection` (map, filter, pluck, etc).
        """
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
        """Get first result."""
        query = self._build_query()
        if query is None:
            return None
        result = query.first()
        return self._model._from_db(result) if result else None

    def first_or_fail(self) -> 'Model':
        """Get first result or raise ModelNotFoundException."""
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
        """Process results in chunks."""
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
        """Process each result."""
        for item in self.get():
            callback(item)

    def pluck(self, column: str, key: str = None) -> List | Dict:
        items = self.get()
        if key:
            return {getattr(item, key): getattr(item, column) for item in items}
        return [getattr(item, column) for item in items]

    def to_list(self) -> List[Dict]:
        return [item.to_dict() for item in self.get()]


class Model(metaclass=ModelMeta):
    """
    EloquentPy Base Model.

    All application models extend this class. Provides Active Record
    functionality: find, save, delete, relationships, and more.
    """

    __table__: ClassVar[Optional[str]] = None
    __primary_key__: ClassVar[str] = 'id'
    __timestamps__: ClassVar[bool] = True
    __soft_delete__: ClassVar[bool] = False
    __fillable__: ClassVar[List[str]] = []
    __guarded__: ClassVar[List[str]] = ['id']
    __hidden__: ClassVar[List[str]] = ['password']
    __casts__: ClassVar[Dict[str, str]] = {}
    __appends__: ClassVar[List[str]] = []
    _abstract: ClassVar[bool] = False
    _soft_delete: ClassVar[bool] = False  # kept for backward compat
    _db_model = None

    def __init__(self, **attributes):
        self._attributes: Dict[str, Any] = {}
        self._original: Dict[str, Any] = {}
        self._relations: Dict[str, Any] = {}
        self._exists: bool = False
        self._dirty: Dict[str, Any] = {}

        for key, value in attributes.items():
            setattr(self, key, value)

    # ─── Attribute Access ─────────────────────────────────────────────────────

    def __setattr__(self, key: str, value: Any):
        if key.startswith('_') or key.startswith('__'):
            super().__setattr__(key, value)
            return

        mutator = f"set_{key}_attribute"
        if hasattr(self, mutator):
            value = getattr(self, mutator)(value)

        self._attributes[key] = value
        if self._exists:
            self._dirty[key] = value

    def __getattr__(self, key: str) -> Any:
        if key.startswith('_'):
            raise AttributeError(key)

        accessor = f"get_{key}_attribute"
        if accessor in self.__class__.__dict__:
            return getattr(self, accessor)()

        if hasattr(self, '_attributes') and key in self._attributes:
            return self._cast(key, self._attributes[key])

        if hasattr(self, '_relations') and key in self._relations:
            return self._relations[key]

        if key in self._get_relation_methods():
            result = getattr(self.__class__, key).fget(self)
            self._relations[key] = result
            return result

        raise AttributeError(f"'{type(self).__name__}' has no attribute '{key}'")

    def _get_relation_methods(self) -> List[str]:
        return [k for k, v in vars(self.__class__).items()
                if isinstance(v, property) and not k.startswith('_')]

    def _cast(self, key: str, value: Any) -> Any:
        """Cast attribute to the configured type."""
        cast_type = self.__casts__.get(key)
        if cast_type is None or value is None:
            return value

        if cast_type in ('int', 'integer'):
            return int(value)
        elif cast_type in ('float', 'double'):
            return float(value)
        elif cast_type in ('bool', 'boolean'):
            return bool(value)
        elif cast_type in ('str', 'string'):
            return str(value)
        elif cast_type in ('json', 'array'):
            import json
            if isinstance(value, str):
                return json.loads(value)
            return value
        elif cast_type == 'datetime':
            if isinstance(value, datetime.datetime):
                return value
            return datetime.datetime.fromisoformat(str(value))
        return value

    # ─── CRUD Operations ──────────────────────────────────────────────────────

    def save(self) -> bool:
        """Save the model to the database."""
        from laraflask.orm.db import DB
        session = DB.session()

        if self.__timestamps__:
            now = datetime.datetime.utcnow()
            if not self._exists:
                self._attributes.setdefault('created_at', now)
            self._attributes['updated_at'] = now

        try:
            if self._exists:
                # Use Session.get() instead of deprecated Query.get()
                db_model = self._get_db_model()
                pk = self._attributes.get(self.__primary_key__)
                db_obj = session.get(db_model, pk)
                if db_obj:
                    for k, v in self._dirty.items():
                        setattr(db_obj, k, v)
            else:
                db_model = self._get_db_model()
                db_obj = db_model(**self._attributes)
                session.add(db_obj)
                session.flush()
                self._attributes[self.__primary_key__] = getattr(
                    db_obj, self.__primary_key__)
                self._exists = True

            session.commit()
            self._original = self._attributes.copy()
            self._dirty.clear()
            return True
        except Exception as e:
            session.rollback()
            raise e

    def delete(self) -> bool:
        """Delete the model from the database."""
        from laraflask.orm.db import DB
        session = DB.session()

        try:
            if self.__soft_delete__:
                self._attributes['deleted_at'] = datetime.datetime.utcnow()
                return self.save()
            else:
                db_model = self._get_db_model()
                pk = self._attributes.get(self.__primary_key__)
                db_obj = session.get(db_model, pk)
                if db_obj:
                    session.delete(db_obj)
                    session.commit()
                    self._exists = False
                    return True
        except Exception as e:
            session.rollback()
            raise e
        return False

    def restore(self) -> bool:
        """Restore a soft-deleted model."""
        if self.__soft_delete__:
            self._attributes['deleted_at'] = None
            return self.save()
        return False

    def fresh(self) -> 'Model':
        """Reload the model from the database."""
        return self.__class__.find(self._attributes[self.__primary_key__])

    def refresh(self) -> 'Model':
        """Reload and sync the model."""
        fresh = self.fresh()
        self._attributes = fresh._attributes
        self._original = fresh._original
        return self

    def is_dirty(self, attribute: str = None) -> bool:
        if attribute:
            return attribute in self._dirty
        return bool(self._dirty)

    def get_dirty(self) -> Dict:
        return self._dirty.copy()

    def was_changed(self, attribute: str = None) -> bool:
        return self.is_dirty(attribute)

    # ─── Class-level Query Methods ────────────────────────────────────────────

    @classmethod
    def query(cls) -> QueryBuilder:
        return QueryBuilder(cls)

    @classmethod
    def observe(cls, observer_class: type) -> None:
        """
        [ID] Daftarkan sebuah Observer untuk model ini, menghubungkannya ke
        event lifecycle yang sudah ada di `laraflask.events.dispatcher`
        (ModelCreating, ModelCreated, dst) tanpa duplikasi logic — observer
        hanya bereaksi pada event yang `event.model` adalah instance dari
        model ini.

        CATATAN: event lifecycle ini saat ini belum di-dispatch otomatis
        dari `save()`/`delete()` — lihat docstring `Observer` dan README
        bagian "Known Limitations" untuk cara dispatch manual sementara.

        [EN] Register an Observer for this model, wiring it to the
        existing lifecycle events in `laraflask.events.dispatcher`
        (ModelCreating, ModelCreated, etc.) without duplicating logic —
        the observer only reacts to events whose `event.model` is an
        instance of this model.

        NOTE: these lifecycle events are not yet automatically dispatched
        from `save()`/`delete()` — see the `Observer` docstring and the
        README's "Known Limitations" section for the manual dispatch
        workaround.
        """
        from laraflask.events.dispatcher import (
            Events, ModelCreating, ModelCreated, ModelUpdating, ModelUpdated,
            ModelDeleting, ModelDeleted, ModelSaving, ModelSaved,
        )

        observer = observer_class()
        hook_map = [
            (ModelCreating, 'creating'),
            (ModelCreated, 'created'),
            (ModelUpdating, 'updating'),
            (ModelUpdated, 'updated'),
            (ModelDeleting, 'deleting'),
            (ModelDeleted, 'deleted'),
            (ModelSaving, 'saving'),
            (ModelSaved, 'saved'),
        ]

        for event_class, hook_name in hook_map:
            if not hasattr(observer, hook_name):
                continue

            def make_listener(observer=observer, hook_name=hook_name, model_cls=cls):
                def listener(event):
                    if isinstance(getattr(event, 'model', None), model_cls):
                        getattr(observer, hook_name)(event.model)
                return listener

            Events.listen(event_class, make_listener())

    @classmethod
    def all(cls, as_collection: bool = False) -> 'List[Model] | Collection':
        """Get all records. Pass `as_collection=True` for a chainable Collection."""
        return cls.query().get(as_collection=as_collection)

    @classmethod
    def find(cls, id: Any) -> Optional['Model']:
        return cls.query().find(id)

    @classmethod
    def find_or_fail(cls, id: Any) -> 'Model':
        return cls.query().find_or_fail(id)

    @classmethod
    def where(cls, column: str, operator_or_value: Any = None,
              value: Any = None) -> QueryBuilder:
        return cls.query().where(column, operator_or_value, value)

    @classmethod
    def where_in(cls, column: str, values: List) -> QueryBuilder:
        return cls.query().where_in(column, values)

    @classmethod
    def order_by(cls, column: str, direction: str = 'ASC') -> QueryBuilder:
        return cls.query().order_by(column, direction)

    @classmethod
    def latest(cls, column: str = 'created_at') -> QueryBuilder:
        return cls.query().latest(column)

    @classmethod
    def oldest(cls, column: str = 'created_at') -> QueryBuilder:
        return cls.query().oldest(column)

    @classmethod
    def first(cls) -> Optional['Model']:
        return cls.query().first()

    @classmethod
    def count(cls) -> int:
        return cls.query().count()

    @classmethod
    def create(cls, **attributes) -> 'Model':
        instance = cls(**attributes)
        instance.save()
        return instance

    @classmethod
    def first_or_create(cls, search: Dict, attributes: Dict = None) -> 'Model':
        query = cls.query()
        for k, v in search.items():
            query = query.where(k, v)
        result = query.first()
        if result:
            return result
        return cls.create(**(search | (attributes or {})))

    @classmethod
    def update_or_create(cls, search: Dict, values: Dict) -> 'Model':
        query = cls.query()
        for k, v in search.items():
            query = query.where(k, v)
        result = query.first()
        if result:
            for k, v in values.items():
                setattr(result, k, v)
            result.save()
            return result
        return cls.create(**(search | values))

    @classmethod
    def with_trashed(cls) -> QueryBuilder:
        """Include soft-deleted records."""
        qb = cls.query()
        qb._include_trashed = True
        return qb

    @classmethod
    def only_trashed(cls) -> QueryBuilder:
        """Return only soft-deleted records."""
        qb = cls.query()
        qb._only_trashed = True
        return qb

    @classmethod
    def _from_db(cls, db_obj) -> Optional['Model']:
        """Construct a Model from a SQLAlchemy object."""
        if db_obj is None:
            return None
        instance = cls.__new__(cls)
        instance._attributes = {}
        instance._original = {}
        instance._relations = {}
        instance._exists = True
        instance._dirty = {}

        for col in db_obj.__table__.columns:
            instance._attributes[col.name] = getattr(db_obj, col.name, None)

        instance._original = instance._attributes.copy()
        return instance

    @classmethod
    def _get_db_model(cls):
        """Return the SQLAlchemy model for this class."""
        from laraflask.orm.db import DB
        return DB.get_model(cls.__table__)

    # ─── Relationships ────────────────────────────────────────────────────────

    def has_one(self, related: Type['Model'], foreign_key: str = None,
                local_key: str = None) -> Optional['Model']:
        fk = foreign_key or f"{self.__class__.__name__.lower()}_id"
        lk = local_key or self.__primary_key__
        return related.where(fk, self._attributes.get(lk)).first()

    def has_many(self, related: Type['Model'], foreign_key: str = None,
                 local_key: str = None) -> List['Model']:
        fk = foreign_key or f"{self.__class__.__name__.lower()}_id"
        lk = local_key or self.__primary_key__
        return related.where(fk, self._attributes.get(lk)).get()

    def belongs_to(self, related: Type['Model'], foreign_key: str = None,
                   owner_key: str = None) -> Optional['Model']:
        fk = foreign_key or f"{related.__name__.lower()}_id"
        ok = owner_key or related.__primary_key__
        return related.where(ok, self._attributes.get(fk)).first()

    def belongs_to_many(self, related: Type['Model'], pivot_table: str = None,
                        foreign_key: str = None, related_key: str = None) -> List['Model']:
        raise NotImplementedError("belongs_to_many requires pivot table setup")

    # ─── Serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        data = {k: v for k, v in self._attributes.items()
                if k not in self.__hidden__}

        for attr in self.__appends__:
            accessor = f"get_{attr}_attribute"
            if hasattr(self, accessor):
                data[attr] = getattr(self, accessor)()

        for key, value in self._relations.items():
            if isinstance(value, list):
                data[key] = [v.to_dict() if hasattr(v, 'to_dict') else v for v in value]
            elif hasattr(value, 'to_dict'):
                data[key] = value.to_dict()
            else:
                data[key] = value

        return data

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), default=str)

    def fill(self, attributes: Dict) -> 'Model':
        """Mass-assign fillable attributes."""
        for key, value in attributes.items():
            if self.__fillable__:
                if key in self.__fillable__:
                    setattr(self, key, value)
            else:
                if not self.__guarded__ or key not in self.__guarded__:
                    setattr(self, key, value)
        return self

    def __repr__(self) -> str:
        pk = self._attributes.get(self.__primary_key__, '?')
        return f"<{self.__class__.__name__} {self.__primary_key__}={pk}>"
