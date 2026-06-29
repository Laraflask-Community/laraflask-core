"""ApiResourceCollection - Transform a collection of models."""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Type
from flask import jsonify, Response

from laraflask.api.api_resource import ApiResource


class ApiResourceCollection:
    """Transform a collection of models."""

    def __init__(self, collection: List, resource_class: Type[ApiResource] = None):
        self._collection = collection
        self._resource_class = resource_class or ApiResource
        self._additional: Dict = {}
        self._pagination: Optional[Dict] = None

    def paginate(self, pagination_data: Dict) -> 'ApiResourceCollection':
        self._pagination = pagination_data
        self._collection = pagination_data.get('data', self._collection)
        return self

    def additional(self, **kwargs) -> 'ApiResourceCollection':
        self._additional.update(kwargs)
        return self

    def to_array(self) -> List[Dict]:
        return [self._resource_class(item).to_array() for item in self._collection]

    def to_response(self) -> Response:
        data = self.to_array()
        payload = {'data': data}

        if self._pagination:
            payload['meta'] = {
                'total':        self._pagination.get('total', len(data)),
                'per_page':     self._pagination.get('per_page', len(data)),
                'current_page': self._pagination.get('current_page', 1),
                'last_page':    self._pagination.get('last_page', 1),
            }
            payload['links'] = {
                'first': f"?page=1",
                'last':  f"?page={payload['meta']['last_page']}",
                'prev':  None,
                'next':  None,
            }

        if self._additional:
            payload.update(self._additional)

        return jsonify(payload)

    def __call__(self) -> Response:
        return self.to_response()
