"""EncryptException."""

from laraflask.core.exceptions.laraflask_exception import LaraflaskException


class EncryptException(LaraflaskException):
    """Encryption/decryption failure."""
    pass
