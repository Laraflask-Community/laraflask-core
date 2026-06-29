"""FormRequest - Laravel-style Form Request."""

from __future__ import annotations
from typing import Dict, Optional

from laraflask.validation._validator import Validator


class FormRequest:
    """
    Laravel-style Form Request - encapsulates validation logic.
    Extend this class and define rules() and authorize().
    """

    def __init__(self):
        from flask import request as flask_request
        self._request = flask_request
        self._validator: Optional[Validator] = None

    def authorize(self) -> bool:
        """Return True if the request is authorized."""
        return True

    def rules(self) -> Dict:
        """Define validation rules."""
        return {}

    def messages(self) -> Dict:
        """Custom error messages."""
        return {}

    def attributes(self) -> Dict:
        """Custom attribute names."""
        return {}

    def validate(self) -> Dict:
        """Run validation and return validated data."""
        if not self.authorize():
            from flask import abort
            abort(403)

        data = {
            **self._request.form.to_dict(),
            **self._request.args.to_dict(),
            **(self._request.get_json(silent=True) or {}),
        }

        self._validator = Validator(data, self.rules(), self.messages(), self.attributes())
        return self._validator.validate()

    def validated(self) -> Dict:
        if self._validator:
            return self._validator._validated
        return self.validate()

    def errors(self) -> Dict:
        if self._validator:
            return self._validator.errors()
        return {}
