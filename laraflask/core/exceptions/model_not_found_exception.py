"""ModelNotFoundException."""

from laraflask.core.exceptions.laraflask_exception import LaraflaskException


class ModelNotFoundException(LaraflaskException):
    """Raised when a model query returns no result via find_or_fail."""

    def __init__(self, model: str = '', id=None):
        self.model = model
        self.id = id
        msg = f"No query results for model [{model}]"
        if id:
            msg += f" with ID [{id}]"
        super().__init__(msg)
