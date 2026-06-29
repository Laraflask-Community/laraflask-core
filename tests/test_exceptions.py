"""Tests for laraflask.core.exceptions - hierarchy and behavior."""

import pytest

from laraflask.core.exceptions import (
    LaraflaskException,
    ApplicationException,
    ModelNotFoundException,
    AuthorizationException,
    AuthenticationException,
    ValidationException,
    HttpException,
    NotFoundHttpException,
    UnauthorizedHttpException,
    ForbiddenHttpException,
    MethodNotAllowedHttpException,
    TooManyRequestsException,
    MaintenanceModeException,
    TokenMismatchException,
    EncryptException,
    QueueException,
    CacheException,
    StorageException,
    NotificationException,
)


class TestExceptionInheritance:
    """All exceptions should derive from LaraflaskException -> Exception."""

    def test_laraflask_exception_is_base(self):
        assert issubclass(LaraflaskException, Exception)

    @pytest.mark.parametrize("exc_class", [
        ApplicationException,
        ModelNotFoundException,
        AuthorizationException,
        AuthenticationException,
        ValidationException,
        HttpException,
        TokenMismatchException,
        EncryptException,
        QueueException,
        CacheException,
        StorageException,
        NotificationException,
    ])
    def test_direct_subclass_of_laraflask_exception(self, exc_class):
        assert issubclass(exc_class, LaraflaskException)

    @pytest.mark.parametrize("exc_class", [
        NotFoundHttpException,
        UnauthorizedHttpException,
        ForbiddenHttpException,
        MethodNotAllowedHttpException,
        TooManyRequestsException,
        MaintenanceModeException,
    ])
    def test_http_subclasses(self, exc_class):
        assert issubclass(exc_class, HttpException)
        assert issubclass(exc_class, LaraflaskException)


class TestHttpException:
    """Test HttpException status codes and messages."""

    def test_custom_status_and_message(self):
        exc = HttpException(418, "I'm a teapot")
        assert exc.status_code == 418
        assert "teapot" in str(exc)

    def test_default_message(self):
        exc = HttpException(500)
        assert exc.status_code == 500
        assert "500" in str(exc)

    def test_not_found(self):
        exc = NotFoundHttpException()
        assert exc.status_code == 404

    def test_unauthorized(self):
        exc = UnauthorizedHttpException()
        assert exc.status_code == 401

    def test_forbidden(self):
        exc = ForbiddenHttpException()
        assert exc.status_code == 403

    def test_method_not_allowed(self):
        exc = MethodNotAllowedHttpException(allowed=["GET", "POST"])
        assert exc.status_code == 405
        assert exc.allowed == ["GET", "POST"]

    def test_too_many_requests(self):
        exc = TooManyRequestsException(retry_after=120)
        assert exc.status_code == 429
        assert exc.retry_after == 120

    def test_maintenance_mode(self):
        exc = MaintenanceModeException()
        assert exc.status_code == 503


class TestValidationException:
    """Test ValidationException stores errors dict."""

    def test_stores_errors(self):
        errors = {"email": ["The email field is required."]}
        exc = ValidationException(errors)
        assert exc.errors == errors
        assert exc.get_errors() == errors

    def test_message_contains_errors(self):
        errors = {"name": ["required"]}
        exc = ValidationException(errors)
        assert "name" in str(exc)


class TestModelNotFoundException:
    """Test ModelNotFoundException stores model and id."""

    def test_with_model_and_id(self):
        exc = ModelNotFoundException(model="User", id=42)
        assert exc.model == "User"
        assert exc.id == 42
        assert "User" in str(exc)
        assert "42" in str(exc)

    def test_with_model_only(self):
        exc = ModelNotFoundException(model="Post")
        assert exc.model == "Post"
        assert exc.id is None

    def test_empty(self):
        exc = ModelNotFoundException()
        assert exc.model == ""
        assert exc.id is None


class TestExceptionInstantiation:
    """All exception classes should be instantiable without crashing."""

    def test_laraflask_exception(self):
        exc = LaraflaskException("test")
        assert str(exc) == "test"

    def test_application_exception(self):
        exc = ApplicationException("app error")
        assert isinstance(exc, LaraflaskException)

    def test_authorization_exception(self):
        exc = AuthorizationException("not allowed")
        assert isinstance(exc, LaraflaskException)

    def test_authentication_exception(self):
        exc = AuthenticationException("unauthenticated")
        assert isinstance(exc, LaraflaskException)

    def test_token_mismatch_exception(self):
        exc = TokenMismatchException()
        assert isinstance(exc, LaraflaskException)
        assert "CSRF" in str(exc)

    def test_encrypt_exception(self):
        exc = EncryptException("encrypt error")
        assert isinstance(exc, LaraflaskException)

    def test_queue_exception(self):
        exc = QueueException("queue error")
        assert isinstance(exc, LaraflaskException)

    def test_cache_exception(self):
        exc = CacheException("cache error")
        assert isinstance(exc, LaraflaskException)

    def test_storage_exception(self):
        exc = StorageException("storage error")
        assert isinstance(exc, LaraflaskException)

    def test_notification_exception(self):
        exc = NotificationException("notification error")
        assert isinstance(exc, LaraflaskException)
