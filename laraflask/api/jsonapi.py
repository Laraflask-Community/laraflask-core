"""
Laraflask JSON:API Resource
[ID] Implementasi transformer resource sesuai spesifikasi JSON:API
(https://jsonapi.org/format/), melengkapi `ApiResource` yang sudah ada di
api/api.py dengan struktur response `{data, included, links, meta}`,
sparse fieldset (`?fields[type]=...`), dan relationship inclusion
(`?include=...`).

[EN] A resource transformer implementation that follows the JSON:API
specification (https://jsonapi.org/format/), complementing the existing
`ApiResource` in api/api.py with the `{data, included, links, meta}`
response structure, sparse fieldsets (`?fields[type]=...`), and
relationship inclusion (`?include=...`).
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Type, Union
from flask import jsonify, request, Response


class JsonApiResource:
    """
    [ID] Base class untuk resource ala JSON:API. Subclass biasanya cukup
    mengisi `type_` dan, kalau perlu, override `attributes()` /
    `relationships()` untuk kustomisasi. Contoh:

        class UserResource(JsonApiResource):
            type_ = 'users'

            def attributes(self) -> Dict:
                return {'name': self.model.name, 'email': self.model.email}

            def relationships(self) -> Dict:
                return {'posts': self.model.posts}

        UserResource(user).to_response()

    [EN] Base class for JSON:API-style resources. Subclasses typically only
    need to set `type_` and, when needed, override `attributes()` /
    `relationships()` for customization. Example above.
    """

    type_: str = None  # JSON:API "type" member — override in subclasses, or pass at construction.

    def __init__(self, model: Any, type_: str = None):
        self.model = model
        if type_ is not None:
            self.type_ = type_
        if self.type_ is None:
            self.type_ = self._infer_type(model)

        self._included_registry: Dict[tuple, Dict] = {}

    # ─── Resource Definition (override in subclasses as needed) ───────────────

    def get_id(self) -> str:
        """[ID] Ambil nilai primary key sebagai string. [EN] Get the primary key value as a string."""
        primary_key = getattr(self.model, '__primary_key__', 'id')
        value = self._get_attribute(self.model, primary_key)
        return str(value) if value is not None else None

    def attributes(self) -> Dict[str, Any]:
        """
        [ID] Definisikan attributes JSON:API. Default: semua field dari
        `to_dict()` model, dikurangi primary key (karena primary key sudah
        muncul sebagai `id` di level atas, bukan dalam attributes).

        [EN] Define the JSON:API attributes. Defaults to every field from
        the model's `to_dict()`, minus the primary key (which already
        appears as the top-level `id`, not inside attributes).
        """
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
        """
        [ID] Definisikan relationships JSON:API sebagai dict nama_relasi ->
        model/list-model terkait. Default: kosong (override di subclass).

        [EN] Define JSON:API relationships as a dict of relation_name ->
        related model/list-of-models. Defaults to empty (override in
        subclasses).
        """
        return {}

    def resource_class_for(self, relation_name: str, related_model: Any) -> Type['JsonApiResource']:
        """
        [ID] Tentukan JsonApiResource class apa yang dipakai untuk
        mentransform model dalam relasi `relation_name`. Default: generic
        `JsonApiResource` (type otomatis diinfer dari nama class model).

        [EN] Determine which JsonApiResource class to use when transforming
        a model found in the `relation_name` relationship. Defaults to a
        generic `JsonApiResource` (type auto-inferred from the model's
        class name).
        """
        return JsonApiResource

    # ─── Sparse Fieldsets & Include (query param driven) ───────────────────────

    def _requested_fields(self) -> Optional[List[str]]:
        """Parse `?fields[type]=a,b,c` for this resource's type, if present."""
        try:
            raw = request.args.get(f'fields[{self.type_}]')
        except RuntimeError:
            # No active Flask request context (e.g. unit tests calling to_array() directly).
            raw = None
        if raw is None:
            return None
        return [f.strip() for f in raw.split(',') if f.strip()]

    def _requested_includes(self) -> List[str]:
        """Parse `?include=a,b.c` into a list of dotted relationship paths."""
        try:
            raw = request.args.get('include', '')
        except RuntimeError:
            raw = ''
        return [i.strip() for i in raw.split(',') if i.strip()]

    # ─── Core Transformation ────────────────────────────────────────────────────

    def to_array(self, fields: Optional[List[str]] = None,
                 includes: Optional[List[str]] = None) -> Dict:
        """
        [ID] Hasilkan satu resource object JSON:API: `{type, id, attributes, relationships}`.
        Sparse fieldset dan include diambil dari query string kecuali
        di-pass eksplisit (berguna untuk dipanggil tanpa Flask request context).

        [EN] Produce a single JSON:API resource object:
        `{type, id, attributes, relationships}`. Sparse fieldsets and
        includes are read from the query string unless passed explicitly
        (useful for calling this outside a Flask request context).
        """
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
        """
        [ID] Bangun member `relationships` (selalu berisi resource
        identifier object `{type, id}`) dan, untuk relasi yang ada di
        `includes`, kumpulkan resource lengkapnya ke `_included_registry`
        supaya bisa dipasang di top-level `included` nanti.

        [EN] Build the `relationships` member (always a resource identifier
        object `{type, id}`) and, for relations present in `includes`,
        collect their full resource into `_included_registry` so it can be
        placed in the top-level `included` member later.
        """
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
        """
        [ID] Bangun Flask Response sesuai JSON:API: `{data, included, links, meta}`.
        Header `Content-Type` diset ke `application/vnd.api+json` sesuai spek.

        [EN] Build a Flask Response per JSON:API: `{data, included, links, meta}`.
        The `Content-Type` header is set to `application/vnd.api+json` per
        the spec.
        """
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

    # ─── Collection Helper ───────────────────────────────────────────────────────

    @classmethod
    def collection(cls, items: List[Any]) -> 'JsonApiResourceCollection':
        """Wrap a list of models into a JSON:API resource collection."""
        return JsonApiResourceCollection(items, cls)

    def __call__(self) -> Response:
        return self.to_response()

    # ─── Internals ────────────────────────────────────────────────────────────

    @staticmethod
    def _infer_type(model: Any) -> str:
        """Infer a JSON:API `type` from the model class name (e.g. User -> 'users')."""
        name = type(model).__name__ if not isinstance(model, type) else model.__name__
        return f"{name.lower()}s"

    @staticmethod
    def _is_collection(value: Any) -> bool:
        """Detect Laraflask's Collection (core/collection.py) without importing it eagerly."""
        return hasattr(value, 'to_list') and hasattr(value, 'count') and not isinstance(value, (dict, str))

    @staticmethod
    def _get_attribute(model: Any, key: str) -> Any:
        if isinstance(model, dict):
            return model.get(key)
        return getattr(model, key, None)


class JsonApiResourceCollection:
    """
    [ID] Bungkus banyak model menjadi response JSON:API dengan `data` sebagai
    array resource object, menggabungkan `included` dari seluruh item tanpa
    duplikasi.

    [EN] Wraps multiple models into a JSON:API response with `data` as an
    array of resource objects, merging `included` across all items without
    duplication.
    """

    def __init__(self, items: List[Any], resource_class: Type[JsonApiResource] = JsonApiResource):
        self._items = list(items)
        self._resource_class = resource_class

    def to_array(self, fields: Optional[List[str]] = None,
                 includes: Optional[List[str]] = None) -> List[Dict]:
        return [self._resource_class(item).to_array(fields=fields, includes=includes) for item in self._items]

    def to_response(self, status: int = 200, meta: Dict = None, links: Dict = None) -> Response:
        merged_included: Dict[tuple, Dict] = {}
        data = []

        for item in self._items:
            resource = self._resource_class(item)
            resource._included_registry = {}
            data.append(resource.to_array())
            merged_included.update(resource._included_registry)

        payload: Dict[str, Any] = {'data': data}
        if merged_included:
            payload['included'] = list(merged_included.values())
        if links:
            payload['links'] = links
        if meta:
            payload['meta'] = meta

        response = jsonify(payload)
        response.status_code = status
        response.headers['Content-Type'] = 'application/vnd.api+json'
        return response

    def __call__(self) -> Response:
        return self.to_response()
