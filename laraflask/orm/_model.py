"""Model - EloquentPy Base Model (Active Record implementation)."""

from __future__ import annotations
import datetime
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar, TYPE_CHECKING

from laraflask.core.exceptions import ModelNotFoundException
from laraflask.orm.model_meta import ModelMeta
from laraflask.orm.query_builder import QueryBuilder

if TYPE_CHECKING:
    from laraflask.core.collection import Collection

M = TypeVar('M', bound='Model')


class Model(metaclass=ModelMeta):
    """
    EloquentPy Base Model.
    All application models extend this class.
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
    _soft_delete: ClassVar[bool] = False
    _db_model = None

    def __init__(self, **attributes):
        self._attributes: Dict[str, Any] = {}
        self._original: Dict[str, Any] = {}
        self._relations: Dict[str, Any] = {}
        self._exists: bool = False
        self._dirty: Dict[str, Any] = {}

        for key, value in attributes.items():
            setattr(self, key, value)

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

    def save(self) -> bool:
        from laraflask.orm.db import DB
        session = DB.session()
        if self.__timestamps__:
            now = datetime.datetime.utcnow()
            if not self._exists:
                self._attributes.setdefault('created_at', now)
            self._attributes['updated_at'] = now
        try:
            if self._exists:
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
                self._attributes[self.__primary_key__] = getattr(db_obj, self.__primary_key__)
                self._exists = True
            session.commit()
            self._original = self._attributes.copy()
            self._dirty.clear()
            return True
        except Exception as e:
            session.rollback()
            raise e

    def delete(self) -> bool:
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
        if self.__soft_delete__:
            self._attributes['deleted_at'] = None
            return self.save()
        return False

    def fresh(self) -> 'Model':
        return self.__class__.find(self._attributes[self.__primary_key__])

    def refresh(self) -> 'Model':
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

    @classmethod
    def query(cls) -> QueryBuilder:
        return QueryBuilder(cls)

    @classmethod
    def observe(cls, observer_class: type) -> None:
        from laraflask.events.dispatcher import (
            Events, ModelCreating, ModelCreated, ModelUpdating, ModelUpdated,
            ModelDeleting, ModelDeleted, ModelSaving, ModelSaved,
        )
        observer = observer_class()
        hook_map = [
            (ModelCreating, 'creating'), (ModelCreated, 'created'),
            (ModelUpdating, 'updating'), (ModelUpdated, 'updated'),
            (ModelDeleting, 'deleting'), (ModelDeleted, 'deleted'),
            (ModelSaving, 'saving'), (ModelSaved, 'saved'),
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
        qb = cls.query()
        qb._include_trashed = True
        return qb

    @classmethod
    def only_trashed(cls) -> QueryBuilder:
        qb = cls.query()
        qb._only_trashed = True
        return qb

    @classmethod
    def _from_db(cls, db_obj) -> Optional['Model']:
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
        from laraflask.orm.db import DB
        return DB.get_model(cls.__table__)

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
