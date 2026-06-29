"""TokenMismatchException."""

from laraflask.core.exceptions.laraflask_exception import LaraflaskException


class TokenMismatchException(LaraflaskException):
    """CSRF token mismatch."""

    def __init__(self):
        super().__init__('CSRF token mismatch.')
