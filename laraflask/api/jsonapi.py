"""
Laraflask JSON:API Resource
Re-export hub for backward compatibility.
"""

from laraflask.api.json_api_resource import JsonApiResource
from laraflask.api.json_api_resource_collection import JsonApiResourceCollection

__all__ = [
    'JsonApiResource',
    'JsonApiResourceCollection',
]
