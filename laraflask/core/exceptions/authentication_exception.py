"""AuthenticationException."""

from laraflask.core.exceptions.laraflask_exception import LaraflaskException


class AuthenticationException(LaraflaskException):
    """Raised when authentication fails."""

    def __init__(self, guards=None):
        self.guards = guards or []
        super().__init__('Unauthenticated.')
