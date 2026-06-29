"""AuthorizationException."""

from laraflask.core.exceptions.laraflask_exception import LaraflaskException


class AuthorizationException(LaraflaskException):
    """Raised when a Gate check fails."""

    def __init__(self, message: str = 'This action is unauthorized.'):
        super().__init__(message)
