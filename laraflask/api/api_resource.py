"""ApiResource - Transform a single model instance to JSON."""

from __future__ import annotations
from typing import Any, Dict, List, Type
from flask import jsonify, Response


class ApiResource:
    """
    Transform a single model instance to JSON.
    Laravel-style API resource transformers.
    """

    def __init__(self, resource: Any):
        self._resource = resource
        self._additional: Dict = {}
        self._with_data: Dict = {}

    def to_array(self) -> Dict:
        """Override to define the resource's array representation."""
        if hasattr(self._resource, 'to_dict'):
            return self._resource.to_dict()
        return dict(self._resource) if hasattr(self._resource, '__iter__') else {}

    def with_(self, **kwargs) -> 'ApiResource':
        self._with_data.update(kwargs)
        return self

    def additional(self, **kwargs) -> 'ApiResource':
        self._additional.update(kwargs)
        return self

    def to_response(self) -> Response:
        data = self.to_array()
        payload = {'data': data}
        if self._with_data:
            payload.update(self._with_data)
        if self._additional:
            payload.update(self._additional)
        return jsonify(payload)

    def resolve(self) -> Dict:
        return self.to_array()

    @classmethod
    def make(cls, resource: Any) -> 'ApiResource':
        return cls(resource)

    @classmethod
    def collection(cls, resources: List) -> 'ApiResourceCollection':
        from laraflask.api.api_resource_collection import ApiResourceCollection
        return ApiResourceCollection(resources, cls)

    def __call__(self) -> Response:
        return self.to_response()
