"""Tests for laraflask.validation._validator.Validator."""

import pytest

from laraflask.core.exceptions import ValidationException
from laraflask.validation._validator import Validator


class TestValidatorRequired:
    """Test the required rule."""

    def test_required_passes(self):
        v = Validator({"name": "Alice"}, {"name": "required"})
        assert v.passes() is True

    def test_required_fails_on_empty_string(self):
        v = Validator({"name": ""}, {"name": "required"})
        assert v.fails() is True
        assert "name" in v.errors()

    def test_required_fails_on_none(self):
        v = Validator({"name": None}, {"name": "required"})
        assert v.fails() is True

    def test_required_fails_on_missing_key(self):
        v = Validator({}, {"name": "required"})
        assert v.fails() is True


class TestValidatorStringRule:
    """Test the string rule."""

    def test_string_passes(self):
        v = Validator({"name": "hello"}, {"name": "string"})
        assert v.passes() is True

    def test_string_fails_on_integer(self):
        v = Validator({"name": 123}, {"name": "string"})
        assert v.fails() is True

    def test_string_allows_none(self):
        v = Validator({"name": None}, {"name": "string"})
        assert v.passes() is True


class TestValidatorIntegerRule:
    """Test the integer rule."""

    def test_integer_passes_with_int(self):
        v = Validator({"age": 25}, {"age": "integer"})
        assert v.passes() is True

    def test_integer_passes_with_string_int(self):
        v = Validator({"age": "25"}, {"age": "integer"})
        assert v.passes() is True

    def test_integer_fails_on_text(self):
        v = Validator({"age": "abc"}, {"age": "integer"})
        assert v.fails() is True


class TestValidatorNumericRule:
    """Test the numeric rule."""

    def test_numeric_passes_with_float(self):
        v = Validator({"price": 9.99}, {"price": "numeric"})
        assert v.passes() is True

    def test_numeric_passes_with_string_float(self):
        v = Validator({"price": "3.14"}, {"price": "numeric"})
        assert v.passes() is True

    def test_numeric_fails_on_text(self):
        v = Validator({"price": "abc"}, {"price": "numeric"})
        assert v.fails() is True


class TestValidatorEmailRule:
    """Test the email rule."""

    def test_email_passes(self):
        v = Validator({"email": "test@example.com"}, {"email": "email"})
        assert v.passes() is True

    def test_email_fails(self):
        v = Validator({"email": "not-an-email"}, {"email": "email"})
        assert v.fails() is True

    def test_email_allows_empty(self):
        v = Validator({"email": ""}, {"email": "email"})
        assert v.passes() is True


class TestValidatorMinMaxBetween:
    """Test min, max, and between rules."""

    def test_min_string_length_passes(self):
        v = Validator({"name": "Alice"}, {"name": "min:3"})
        assert v.passes() is True

    def test_min_string_length_fails(self):
        v = Validator({"name": "Al"}, {"name": "min:3"})
        assert v.fails() is True

    def test_max_string_length_passes(self):
        v = Validator({"name": "Alice"}, {"name": "max:10"})
        assert v.passes() is True

    def test_max_string_length_fails(self):
        v = Validator({"name": "A very long name"}, {"name": "max:5"})
        assert v.fails() is True

    def test_min_numeric_passes(self):
        v = Validator({"age": 18}, {"age": "min:18"})
        assert v.passes() is True

    def test_min_numeric_fails(self):
        v = Validator({"age": 15}, {"age": "min:18"})
        assert v.fails() is True

    def test_between_passes(self):
        v = Validator({"score": 75}, {"score": "between:0,100"})
        assert v.passes() is True

    def test_between_fails(self):
        v = Validator({"score": 150}, {"score": "between:0,100"})
        assert v.fails() is True


class TestValidatorInNotIn:
    """Test in and not_in rules."""

    def test_in_passes(self):
        v = Validator({"status": "active"}, {"status": "in:active,inactive"})
        assert v.passes() is True

    def test_in_fails(self):
        v = Validator({"status": "deleted"}, {"status": "in:active,inactive"})
        assert v.fails() is True

    def test_not_in_passes(self):
        v = Validator({"status": "active"}, {"status": "not_in:deleted,banned"})
        assert v.passes() is True

    def test_not_in_fails(self):
        v = Validator({"status": "banned"}, {"status": "not_in:deleted,banned"})
        assert v.fails() is True


class TestValidatorRegex:
    """Test regex rule."""

    def test_regex_passes(self):
        v = Validator({"code": "ABC123"}, {"code": r"regex:^[A-Z]+\d+$"})
        assert v.passes() is True

    def test_regex_fails(self):
        v = Validator({"code": "abc"}, {"code": r"regex:^[A-Z]+\d+$"})
        assert v.fails() is True


class TestValidatorAlpha:
    """Test alpha and alpha_num rules."""

    def test_alpha_passes(self):
        v = Validator({"name": "Alice"}, {"name": "alpha"})
        assert v.passes() is True

    def test_alpha_fails(self):
        v = Validator({"name": "Alice123"}, {"name": "alpha"})
        assert v.fails() is True

    def test_alpha_num_passes(self):
        v = Validator({"code": "ABC123"}, {"code": "alpha_num"})
        assert v.passes() is True

    def test_alpha_num_fails(self):
        v = Validator({"code": "ABC-123"}, {"code": "alpha_num"})
        assert v.fails() is True


class TestValidatorConfirmed:
    """Test confirmed rule."""

    def test_confirmed_passes(self):
        data = {"password": "secret", "password_confirmation": "secret"}
        v = Validator(data, {"password": "confirmed"})
        assert v.passes() is True

    def test_confirmed_fails(self):
        data = {"password": "secret", "password_confirmation": "other"}
        v = Validator(data, {"password": "confirmed"})
        assert v.fails() is True


class TestValidatorJson:
    """Test json rule."""

    def test_json_passes(self):
        v = Validator({"data": '{"key": "value"}'}, {"data": "json"})
        assert v.passes() is True

    def test_json_fails(self):
        v = Validator({"data": "not json"}, {"data": "json"})
        assert v.fails() is True


class TestValidatorUuid:
    """Test uuid rule."""

    def test_uuid_passes(self):
        v = Validator(
            {"id": "550e8400-e29b-41d4-a716-446655440000"},
            {"id": "uuid"}
        )
        assert v.passes() is True

    def test_uuid_fails(self):
        v = Validator({"id": "not-a-uuid"}, {"id": "uuid"})
        assert v.fails() is True


class TestValidatorDate:
    """Test date rule."""

    def test_date_passes(self):
        v = Validator({"created": "2024-01-15"}, {"created": "date"})
        assert v.passes() is True

    def test_date_fails(self):
        v = Validator({"created": "not-a-date"}, {"created": "date"})
        assert v.fails() is True


class TestValidatorUrl:
    """Test url rule."""

    def test_url_passes(self):
        v = Validator({"site": "https://example.com"}, {"site": "url"})
        assert v.passes() is True

    def test_url_fails(self):
        v = Validator({"site": "not a url"}, {"site": "url"})
        assert v.fails() is True


class TestValidatorNullable:
    """Test nullable rule stops validation chain on None."""

    def test_nullable_allows_none(self):
        v = Validator({"bio": None}, {"bio": "nullable|string|min:5"})
        assert v.passes() is True

    def test_nullable_still_validates_value(self):
        v = Validator({"bio": "Hi"}, {"bio": "nullable|string|min:5"})
        assert v.fails() is True


class TestValidatorSometimes:
    """Test the sometimes() method for conditional rule addition."""

    def test_sometimes_method_adds_rules_when_callback_passes(self):
        v = Validator({"email": "bad"}, {})
        v.sometimes("email", "required|email", lambda data: "email" in data)
        assert v.fails() is True

    def test_sometimes_method_skips_when_callback_false(self):
        v = Validator({"email": "bad"}, {})
        v.sometimes("email", "required|email", lambda data: False)
        assert v.passes() is True

    def test_sometimes_method_validates_present(self):
        v = Validator({"email": "bad"}, {})
        v.sometimes("email", "required|email")
        assert v.fails() is True


class TestValidatorValidateMethod:
    """Test validate() raises ValidationException on failure."""

    def test_validate_raises_on_failure(self):
        v = Validator({}, {"name": "required"})
        with pytest.raises(ValidationException) as exc_info:
            v.validate()
        assert "name" in exc_info.value.errors

    def test_validate_returns_data_on_success(self):
        v = Validator({"name": "Alice"}, {"name": "required|string"})
        result = v.validate()
        assert result == {"name": "Alice"}


class TestValidatorMultipleRules:
    """Test combining multiple rules."""

    def test_multiple_rules_all_pass(self):
        v = Validator(
            {"email": "test@test.com", "age": 25},
            {"email": "required|email", "age": "required|integer|min:18"}
        )
        assert v.passes() is True

    def test_multiple_fields_fail(self):
        v = Validator(
            {"email": "bad", "age": 10},
            {"email": "required|email", "age": "required|integer|min:18"}
        )
        assert v.fails() is True
        errors = v.errors()
        assert "email" in errors
        assert "age" in errors
