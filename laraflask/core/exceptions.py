"""
Laraflask Core Exceptions
Single source of truth — all framework exceptions live here.
"""


class LaraflaskException(Exception):
    """Base exception for all Laraflask errors."""
    pass


class ApplicationException(LaraflaskException):
    pass


class ModelNotFoundException(LaraflaskException):
    """Raised when a model query returns no result via find_or_fail."""

    def __init__(self, model: str = '', id=None):
        self.model = model
        self.id = id
        msg = f"No query results for model [{model}]"
        if id:
            msg += f" with ID [{id}]"
        super().__init__(msg)


class AuthorizationException(LaraflaskException):
    """Raised when a Gate check fails."""

    def __init__(self, message: str = 'This action is unauthorized.'):
        super().__init__(message)


class AuthenticationException(LaraflaskException):
    """Raised when authentication fails."""

    def __init__(self, guards=None):
        self.guards = guards or []
        super().__init__('Unauthenticated.')


class ValidationException(LaraflaskException):
    """Raised when validation fails."""

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")

    def get_errors(self) -> dict:
        return self.errors


class HttpException(LaraflaskException):
    """HTTP-level exception with status code."""

    def __init__(self, status_code: int, message: str = ''):
        self.status_code = status_code
        super().__init__(message or f"HTTP {status_code}")


class NotFoundHttpException(HttpException):
    def __init__(self, message: str = 'Not Found'):
        super().__init__(404, message)


class UnauthorizedHttpException(HttpException):
    def __init__(self, message: str = 'Unauthorized'):
        super().__init__(401, message)


class ForbiddenHttpException(HttpException):
    def __init__(self, message: str = 'Forbidden'):
        super().__init__(403, message)


class MethodNotAllowedHttpException(HttpException):
    def __init__(self, allowed: list = None):
        self.allowed = allowed or []
        super().__init__(405, 'Method Not Allowed')


class TooManyRequestsException(HttpException):
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(429, 'Too Many Requests')


class MaintenanceModeException(HttpException):
    def __init__(self):
        super().__init__(503, 'Service Unavailable')


class TokenMismatchException(LaraflaskException):
    """CSRF token mismatch."""

    def __init__(self):
        super().__init__('CSRF token mismatch.')


class EncryptException(LaraflaskException):
    """Encryption/decryption failure."""
    pass


class QueueException(LaraflaskException):
    pass


class CacheException(LaraflaskException):
    pass


class StorageException(LaraflaskException):
    pass


class NotificationException(LaraflaskException):
    pass
