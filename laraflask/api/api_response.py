"""ApiResponse - Standardized JSON API response builder."""

from __future__ import annotations
from typing import Any, Dict
from flask import jsonify, Response


class ApiResponse:
    """Standardized JSON API response builder."""

    @staticmethod
    def success(data: Any = None, message: str = 'Success',
                status: int = 200, meta: Dict = None) -> Response:
        payload = {'success': True, 'message': message}
        if data is not None:
            payload['data'] = data
        if meta:
            payload['meta'] = meta
        return jsonify(payload), status

    @staticmethod
    def created(data: Any = None, message: str = 'Created') -> Response:
        return ApiResponse.success(data, message, 201)

    @staticmethod
    def error(message: str = 'Error', status: int = 400,
              errors: Dict = None, code: str = None) -> Response:
        payload = {'success': False, 'message': message}
        if errors:
            payload['errors'] = errors
        if code:
            payload['code'] = code
        return jsonify(payload), status

    @staticmethod
    def not_found(message: str = 'Resource not found') -> Response:
        return ApiResponse.error(message, 404)

    @staticmethod
    def unauthorized(message: str = 'Unauthenticated.') -> Response:
        return ApiResponse.error(message, 401)

    @staticmethod
    def forbidden(message: str = 'Forbidden.') -> Response:
        return ApiResponse.error(message, 403)

    @staticmethod
    def validation_error(errors: Dict, message: str = 'Validation failed') -> Response:
        return ApiResponse.error(message, 422, errors=errors)

    @staticmethod
    def server_error(message: str = 'Internal Server Error') -> Response:
        return ApiResponse.error(message, 500)

    @staticmethod
    def no_content() -> Response:
        return Response(status=204)

    @staticmethod
    def paginated(paginator: Dict, message: str = 'Success') -> Response:
        data = paginator.get('data', [])
        meta = {
            'total':        paginator.get('total', 0),
            'per_page':     paginator.get('per_page', 15),
            'current_page': paginator.get('current_page', 1),
            'last_page':    paginator.get('last_page', 1),
            'from':         paginator.get('from', 0),
            'to':           paginator.get('to', 0),
        }
        return ApiResponse.success(data, message, meta=meta)
