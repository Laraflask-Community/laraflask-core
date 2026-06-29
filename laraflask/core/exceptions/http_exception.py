"""HttpException and HTTP-specific exception subclasses."""

from laraflask.core.exceptions.laraflask_exception import LaraflaskException


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
