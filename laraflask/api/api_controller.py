"""ApiController - Base controller for API endpoints."""

from __future__ import annotations
from typing import Any, Dict, List, Type
from flask import request, Response

from laraflask.api.api_response import ApiResponse
from laraflask.api.api_resource import ApiResource
from laraflask.api.api_resource_collection import ApiResourceCollection


class ApiController:
    """
    Base controller for API endpoints.
    Provides helpers for common API patterns.
    """

    def respond(self, data: Any = None, message: str = 'Success',
                status: int = 200) -> Response:
        return ApiResponse.success(data, message, status)

    def created(self, data: Any = None, message: str = 'Created') -> Response:
        return ApiResponse.created(data, message)

    def no_content(self) -> Response:
        return ApiResponse.no_content()

    def error(self, message: str, status: int = 400,
              errors: Dict = None) -> Response:
        return ApiResponse.error(message, status, errors)

    def not_found(self, message: str = 'Resource not found') -> Response:
        return ApiResponse.not_found(message)

    def unauthorized(self) -> Response:
        return ApiResponse.unauthorized()

    def forbidden(self) -> Response:
        return ApiResponse.forbidden()

    def validation_error(self, errors: Dict) -> Response:
        return ApiResponse.validation_error(errors)

    def paginate(self, query_builder, per_page: int = 15) -> Response:
        page = request.args.get('page', 1, type=int)
        paginator = query_builder.paginate(per_page=per_page, page=page)
        return ApiResponse.paginated(paginator)

    def resource(self, resource: Any,
                 resource_class: Type[ApiResource] = None) -> Response:
        if resource_class:
            return resource_class(resource).to_response()
        return ApiResponse.success(
            resource.to_dict() if hasattr(resource, 'to_dict') else resource
        )

    def collection(self, items: List,
                   resource_class: Type[ApiResource] = None) -> Response:
        if resource_class:
            return ApiResourceCollection(items, resource_class).to_response()
        return ApiResponse.success([
            item.to_dict() if hasattr(item, 'to_dict') else item
            for item in items
        ])
