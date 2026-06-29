"""JsonApiResource - JSON:API specification resource transformer."""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Type
from flask import jsonify, request, Response


class JsonApiResource:
    """
    Base class for JSON:API-style resources.
    """

    type_: str = None

    def __init__(self, model: Any, type_: str = None):
        self.model = model
        if type_ is not None:
            self.type_ = type_
        if self.type_ is None:
            self.type_ = self._infer_type(model)

        self._included_registry: Dict[tuple, Dict] = {}

    def get_id(self) -> str:
        primary_key = getattr(self.model, '__primary_key__', 'id')
        value = self._get_attribute(self.model, primary_key)
        return str(value) if value is not None else None

    def attributes(self) -> Dict[str, Any]:
        if hasattr(self.model, 'to_dict'):
            data = dict(self.model.to_dict())
        elif isinstance(self.model, dict):
            data = dict(self.model)
        else:
            data = {}

        primary_key = getattr(self.model, '__primary_key__', 'id')
        data.pop(primary_key, None)
        return data

    def relationships(self) -> Dict[str, Any]:
        return {}

    def resource_class_for(self, relation_name: str, related_model: Any) -> Type['JsonApiResource']:
        return JsonApiResource

    def _requested_fields(self) -> Optional[List[str]]:
        try:
            raw = request.args.get(f'fields[{self.type_}]')
        except RuntimeError:
            raw = None
        if raw is None:
            return None
        return [f.strip() for f in raw.split(',') if f.strip()]

    def _requested_includes(self) -> List[str]:
        try:
            raw = request.args.get('include', '')
        except RuntimeError:
            raw = ''
        return [i.strip() for i in raw.split(',') if i.strip()]

    def to_array(self, fields: Optional[List[str]] = None,
                 includes: Optional[List[str]] = None) -> Dict:
        fields = fields if fields is not None else self._requested_fields()
        includes = includes if includes is not None else self._requested_includes()

        attrs = self.attributes()
        if fields is not None:
            attrs = {k: v for k, v in attrs.items() if k in fields}

        resource_object: Dict[str, Any] = {
            'type': self.type_,
            'id': self.get_id(),
            'attributes': attrs,
        }

        rel_data = self._build_relationships(includes)
        if rel_data:
            resource_object['relationships'] = rel_data

        return resource_object

    def _build_relationships(self, includes: List[str]) -> Dict[str, Any]:
        relationships = {}
        defined = self.relationships()

        for name, related in defined.items():
            if related is None:
                relationships[name] = {'data': None}
                continue

            is_many = isinstance(related, (list, tuple)) or self._is_collection(related)
            related_items = list(related) if is_many else [related]

            identifiers = []
            should_include = name in includes

            for item in related_items:
                resource_cls = self.resource_class_for(name, item)
                child = resource_cls(item)
                identifiers.append({'type': child.type_, 'id': child.get_id()})

                if should_include:
                    key = (child.type_, child.get_id())
                    if key not in self._included_registry:
                        self._included_registry[key] = child.to_array()

            relationships[name] = {'data': identifiers if is_many else (identifiers[0] if identifiers else None)}

        return relationships

    def to_response(self, status: int = 200, meta: Dict = None, links: Dict = None) -> Response:
        self._included_registry = {}
        data = self.to_array()

        payload: Dict[str, Any] = {'data': data}

        if self._included_registry:
            payload['included'] = list(self._included_registry.values())
        if links:
            payload['links'] = links
        if meta:
            payload['meta'] = meta

        response = jsonify(payload)
        response.status_code = status
        response.headers['Content-Type'] = 'application/vnd.api+json'
        return response

    @classmethod
    def collection(cls, items: List[Any]) -> 'JsonApiResourceCollection':
        from laraflask.api.json_api_resource_collection import JsonApiResourceCollection
        return JsonApiResourceCollection(items, cls)

    def __call__(self) -> Response:
        return self.to_response()

    @staticmethod
    def _infer_type(model: Any) -> str:
        name = type(model).__name__ if not isinstance(model, type) else model.__name__
        return f"{name.lower()}s"

    @staticmethod
    def _is_collection(value: Any) -> bool:
        return hasattr(value, 'to_list') and hasattr(value, 'count') and not isinstance(value, (dict, str))

    @staticmethod
    def _get_attribute(model: Any, key: str) -> Any:
        if isinstance(model, dict):
            return model.get(key)
        return getattr(model, key, None)
