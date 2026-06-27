"""
Laraflask Validation System
Expressive validation rules inspired by Laravel's Validator.
"""

from __future__ import annotations
import re
import os
from typing import Any, Callable, Dict, List, Optional, Union

# Import ValidationException from single source of truth
from laraflask.core.exceptions import ValidationException


class Validator:
    """
    Validates data against a set of rules.

    Usage:
        validator = Validator(data, {
            'email': 'required|email|unique:users',
            'name': 'required|string|min:2|max:100',
            'age': 'required|integer|min:18',
        })
        if validator.fails():
            return validator.errors()
    """

    RULE_HANDLERS: Dict[str, str] = {}

    def __init__(self, data: Dict, rules: Dict[str, Any],
                 messages: Dict = None, attributes: Dict = None):
        self._data = data
        self._rules = self._parse_rules(rules)
        self._custom_messages = messages or {}
        self._custom_attributes = attributes or {}
        self._errors: Dict[str, List[str]] = {}
        self._validated: Dict = {}
        self._validated_flag = False
        self._sometimes: List[str] = []

    def _parse_rules(self, rules: Dict) -> Dict[str, List]:
        parsed = {}
        for field, rule in rules.items():
            if isinstance(rule, str):
                parsed[field] = rule.split('|')
            elif isinstance(rule, list):
                parsed[field] = rule
            else:
                parsed[field] = [rule]
        return parsed

    def validate(self) -> Dict:
        """Run validation and return validated data or raise ValidationException."""
        self._run_validation()
        if self._errors:
            raise ValidationException(self._errors)
        return self._validated

    def fails(self) -> bool:
        """Run validation and return True if it fails."""
        if not self._validated_flag:
            self._run_validation()
        return bool(self._errors)

    def passes(self) -> bool:
        return not self.fails()

    def errors(self) -> Dict[str, List[str]]:
        if not self._validated_flag:
            self._run_validation()
        return self._errors

    def _run_validation(self):
        self._errors = {}
        self._validated = {}
        self._validated_flag = True

        for field, rules in self._rules.items():
            if field in self._sometimes and field not in self._data:
                continue

            value = self._get_value(field)

            for rule in rules:
                rule_name, params = self._parse_rule(rule)
                if rule_name == 'sometimes':
                    self._sometimes.append(field)
                    continue
                if rule_name == 'nullable' and value is None:
                    break

                method = f"_validate_{rule_name}"
                if hasattr(self, method):
                    passed, message = getattr(self, method)(field, value, params)
                    if not passed:
                        self._errors.setdefault(field, []).append(
                            self._get_message(field, rule_name, message)
                        )
                        break  # Stop on first failure per field
                elif callable(rule_name) if not isinstance(rule_name, str) else False:
                    passed = rule_name(value)
                    if not passed:
                        self._errors.setdefault(field, []).append(
                            f"The {field} field is invalid."
                        )

            if field not in self._errors:
                self._validated[field] = value

    def _get_value(self, field: str) -> Any:
        """Support dot-notation for nested keys."""
        keys = field.split('.')
        value = self._data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def _parse_rule(self, rule: Any) -> tuple:
        if callable(rule):
            return rule, []
        if isinstance(rule, str):
            if ':' in rule:
                name, params_str = rule.split(':', 1)
                return name, params_str.split(',')
            return rule, []
        return str(rule), []

    def _get_message(self, field: str, rule: str, default: str) -> str:
        key = f"{field}.{rule}"
        if key in self._custom_messages:
            return self._custom_messages[key]
        if rule in self._custom_messages:
            return self._custom_messages[rule]
        attr = self._custom_attributes.get(field, field.replace('_', ' '))
        return default.replace(':attribute', attr)

    # ─── Built-in Rules ───────────────────────────────────────────────────────

    def _validate_required(self, field, value, params):
        passed = value is not None and value != '' and value != [] and value != {}
        return passed, f"The :attribute field is required."

    def _validate_nullable(self, field, value, params):
        return True, ''

    def _validate_string(self, field, value, params):
        if value is None:
            return True, ''
        return isinstance(value, str), f"The :attribute must be a string."

    def _validate_integer(self, field, value, params):
        if value is None:
            return True, ''
        try:
            int(value)
            return True, ''
        except (TypeError, ValueError):
            return False, f"The :attribute must be an integer."

    def _validate_numeric(self, field, value, params):
        if value is None:
            return True, ''
        try:
            float(value)
            return True, ''
        except (TypeError, ValueError):
            return False, f"The :attribute must be a number."

    def _validate_boolean(self, field, value, params):
        if value is None:
            return True, ''
        return value in (True, False, 0, 1, '0', '1', 'true', 'false'), \
               f"The :attribute must be true or false."

    def _validate_array(self, field, value, params):
        if value is None:
            return True, ''
        return isinstance(value, (list, tuple)), f"The :attribute must be an array."

    def _validate_email(self, field, value, params):
        if not value:
            return True, ''
        try:
            from email_validator import validate_email
            validate_email(value)
            return True, ''
        except Exception:
            pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, str(value))), \
                   f"The :attribute must be a valid email address."

    def _validate_url(self, field, value, params):
        if not value:
            return True, ''
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, str(value))), \
               f"The :attribute must be a valid URL."

    def _validate_min(self, field, value, params):
        if value is None or not params:
            return True, ''
        min_val = float(params[0])
        if isinstance(value, str):
            return len(value) >= min_val, \
                   f"The :attribute must be at least {params[0]} characters."
        if isinstance(value, (list, tuple)):
            return len(value) >= min_val, \
                   f"The :attribute must have at least {params[0]} items."
        try:
            return float(value) >= min_val, \
                   f"The :attribute must be at least {params[0]}."
        except (TypeError, ValueError):
            return False, f"The :attribute must be at least {params[0]}."

    def _validate_max(self, field, value, params):
        if value is None or not params:
            return True, ''
        max_val = float(params[0])
        if isinstance(value, str):
            return len(value) <= max_val, \
                   f"The :attribute may not be greater than {params[0]} characters."
        if isinstance(value, (list, tuple)):
            return len(value) <= max_val, \
                   f"The :attribute may not have more than {params[0]} items."
        try:
            return float(value) <= max_val, \
                   f"The :attribute may not be greater than {params[0]}."
        except (TypeError, ValueError):
            return False, f"The :attribute may not be greater than {params[0]}."

    def _validate_between(self, field, value, params):
        if value is None or len(params) < 2:
            return True, ''
        min_val, max_val = float(params[0]), float(params[1])
        try:
            v = float(value) if not isinstance(value, (str, list)) else len(value)
            return min_val <= v <= max_val, \
                   f"The :attribute must be between {params[0]} and {params[1]}."
        except (TypeError, ValueError):
            return False, f"The :attribute must be between {params[0]} and {params[1]}."

    def _validate_size(self, field, value, params):
        return self._validate_min(field, value, params) and \
               self._validate_max(field, value, params)

    def _validate_in(self, field, value, params):
        if value is None:
            return True, ''
        return str(value) in params, \
               f"The selected :attribute is invalid."

    def _validate_not_in(self, field, value, params):
        if value is None:
            return True, ''
        return str(value) not in params, \
               f"The selected :attribute is invalid."

    def _validate_regex(self, field, value, params):
        if not value or not params:
            return True, ''
        return bool(re.match(params[0], str(value))), \
               f"The :attribute format is invalid."

    def _validate_alpha(self, field, value, params):
        if not value:
            return True, ''
        return bool(re.match(r'^[a-zA-Z]+$', str(value))), \
               f"The :attribute may only contain letters."

    def _validate_alpha_num(self, field, value, params):
        if not value:
            return True, ''
        return bool(re.match(r'^[a-zA-Z0-9]+$', str(value))), \
               f"The :attribute may only contain letters and numbers."

    def _validate_alpha_dash(self, field, value, params):
        if not value:
            return True, ''
        return bool(re.match(r'^[a-zA-Z0-9_\-]+$', str(value))), \
               f"The :attribute may only contain letters, numbers, dashes and underscores."

    def _validate_confirmed(self, field, value, params):
        confirm_field = f"{field}_confirmation"
        confirm_value = self._data.get(confirm_field)
        return value == confirm_value, \
               f"The :attribute confirmation does not match."

    def _validate_same(self, field, value, params):
        if not params:
            return True, ''
        other = self._data.get(params[0])
        return value == other, \
               f"The :attribute and {params[0]} must match."

    def _validate_different(self, field, value, params):
        if not params:
            return True, ''
        other = self._data.get(params[0])
        return value != other, \
               f"The :attribute and {params[0]} must be different."

    def _validate_unique(self, field, value, params):
        """unique:table,column,except_id,id_column"""
        if not value or not params:
            return True, ''
        try:
            from laraflask.orm.db import DB
            table = params[0]
            column = params[1] if len(params) > 1 else field
            except_id = params[2] if len(params) > 2 else None
            id_column = params[3] if len(params) > 3 else 'id'

            sql = f"SELECT COUNT(*) as cnt FROM {table} WHERE {column} = :val"
            bindings = {'val': value}
            if except_id:
                sql += f" AND {id_column} != :except_id"
                bindings['except_id'] = except_id

            result = DB.select(sql, bindings)
            count = result[0]['cnt'] if result else 0
            return count == 0, f"The :attribute has already been taken."
        except Exception:
            return True, ''

    def _validate_exists(self, field, value, params):
        """exists:table,column"""
        if not value or not params:
            return True, ''
        try:
            from laraflask.orm.db import DB
            table = params[0]
            column = params[1] if len(params) > 1 else field
            result = DB.select(
                f"SELECT COUNT(*) as cnt FROM {table} WHERE {column} = :val",
                {'val': value}
            )
            count = result[0]['cnt'] if result else 0
            return count > 0, f"The selected :attribute is invalid."
        except Exception:
            return True, ''

    def _validate_date(self, field, value, params):
        if not value:
            return True, ''
        import datetime
        try:
            datetime.datetime.fromisoformat(str(value))
            return True, ''
        except ValueError:
            return False, f"The :attribute is not a valid date."

    def _validate_before(self, field, value, params):
        import datetime
        if not value or not params:
            return True, ''
        try:
            val_date = datetime.datetime.fromisoformat(str(value))
            ref_date = datetime.datetime.fromisoformat(params[0])
            return val_date < ref_date, \
                   f"The :attribute must be a date before {params[0]}."
        except ValueError:
            return False, f"The :attribute must be a valid date."

    def _validate_after(self, field, value, params):
        import datetime
        if not value or not params:
            return True, ''
        try:
            val_date = datetime.datetime.fromisoformat(str(value))
            ref_date = datetime.datetime.fromisoformat(params[0])
            return val_date > ref_date, \
                   f"The :attribute must be a date after {params[0]}."
        except ValueError:
            return False, f"The :attribute must be a valid date."

    def _validate_file(self, field, value, params):
        if value is None:
            return True, ''
        return hasattr(value, 'filename'), f"The :attribute must be a file."

    def _validate_image(self, field, value, params):
        if value is None:
            return True, ''
        if not hasattr(value, 'filename'):
            return False, f"The :attribute must be an image."
        ext = os.path.splitext(value.filename)[1].lower()
        return ext in ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'), \
               f"The :attribute must be an image."

    def _validate_mimes(self, field, value, params):
        if value is None or not params or not hasattr(value, 'filename'):
            return True, ''
        ext = os.path.splitext(value.filename)[1].lower().lstrip('.')
        return ext in params, \
               f"The :attribute must be a file of type: {', '.join(params)}."

    def _validate_json(self, field, value, params):
        if not value:
            return True, ''
        import json
        try:
            json.loads(value)
            return True, ''
        except (TypeError, ValueError):
            return False, f"The :attribute must be a valid JSON string."

    def _validate_ip(self, field, value, params):
        if not value:
            return True, ''
        import ipaddress
        try:
            ipaddress.ip_address(str(value))
            return True, ''
        except ValueError:
            return False, f"The :attribute must be a valid IP address."

    def _validate_uuid(self, field, value, params):
        if not value:
            return True, ''
        import uuid
        try:
            uuid.UUID(str(value))
            return True, ''
        except ValueError:
            return False, f"The :attribute must be a valid UUID."

    def _validate_required_if(self, field, value, params):
        if len(params) < 2:
            return True, ''
        other_field, other_value = params[0], params[1]
        if str(self._data.get(other_field)) == other_value:
            return value is not None and value != '', \
                   f"The :attribute field is required when {other_field} is {other_value}."
        return True, ''

    def _validate_required_unless(self, field, value, params):
        if len(params) < 2:
            return True, ''
        other_field, other_value = params[0], params[1]
        if str(self._data.get(other_field)) != other_value:
            return value is not None and value != '', \
                   f"The :attribute field is required unless {other_field} is {other_value}."
        return True, ''

    def _validate_required_with(self, field, value, params):
        if any(self._data.get(f) for f in params):
            return value is not None and value != '', \
                   f"The :attribute field is required when {', '.join(params)} is present."
        return True, ''

    def _validate_prohibited(self, field, value, params):
        return value is None or value == '', \
               f"The :attribute field is prohibited."

    def sometimes(self, field: str, rules: Any, callback: Callable = None) -> 'Validator':
        """Conditionally add validation rules."""
        if callback is None or callback(self._data):
            self._rules[field] = self._parse_rules({field: rules})[field]
        return self

    def after(self, callback: Callable) -> 'Validator':
        """Add an after-validation hook."""
        if not self._errors:
            callback(self)
        return self

    @classmethod
    def make(cls, data: Dict, rules: Dict, messages: Dict = None,
             attributes: Dict = None) -> 'Validator':
        return cls(data, rules, messages, attributes)

    @classmethod
    def extend(cls, rule_name: str, callback: Callable) -> None:
        """Register a custom validation rule."""
        method_name = f"_validate_{rule_name}"
        setattr(cls, method_name, lambda self, field, value, params: callback(field, value, params))


class FormRequest:
    """
    Laravel-style Form Request — encapsulates validation logic.
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
