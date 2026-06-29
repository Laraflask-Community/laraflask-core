"""JsonApiResourceCollection - JSON:API collection response."""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Type
from flask import jsonify, Response

from laraflask.api.json_api_resource import JsonApiResource


class JsonApiResourceCollection:
    """Wraps multiple models into a JSON:API response."""

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
