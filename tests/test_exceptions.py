from __future__ import annotations

import pytest
from core.exceptions import (
    AppError, ValidationError, AuthError,
    NotFoundError, AlreadyExistsError, DatabaseError, ErrorCode
)
from core.error_handler import handle_service_errors, safe_execute


class TestExceptions:
    def test_app_error_basic(self):
        err = AppError("测试错误")
        assert err.message == "测试错误"
        assert err.code == ErrorCode.UNKNOWN_ERROR
        assert err.details == {}

    def test_app_error_to_dict(self):
        err = AppError("测试", ErrorCode.VALIDATION_ERROR, {"field": "name"})
        d = err.to_dict()
        assert d["code"] == ErrorCode.VALIDATION_ERROR.value
        assert d["message"] == "测试"
        assert d["details"]["field"] == "name"

    def test_validation_error(self):
        err = ValidationError("字段不能为空")
        assert err.code == ErrorCode.VALIDATION_ERROR
        assert "字段不能为空" in str(err)

    def test_auth_error(self):
        err = AuthError()
        assert err.code == ErrorCode.AUTH_FAILED

    def test_not_found_error(self):
        err = NotFoundError("用户", 42)
        assert err.code == ErrorCode.NOT_FOUND
        assert "用户" in err.message
        assert "42" in err.message

    def test_already_exists_error(self):
        err = AlreadyExistsError("用户", "username", "admin")
        assert err.code == ErrorCode.ALREADY_EXISTS
        assert "admin" in err.message

    def test_database_error(self):
        err = DatabaseError("连接失败")
        assert err.code == ErrorCode.DB_ERROR


class TestErrorHandler:
    def test_handle_service_errors_success(self):
        @handle_service_errors
        def my_func():
            return 42

        assert my_func() == 42

    def test_handle_service_errors_value_error(self):
        @handle_service_errors
        def my_func():
            raise ValueError("参数错误")

        with pytest.raises(ValidationError) as exc_info:
            my_func()
        assert "参数错误" in str(exc_info.value)

    def test_handle_service_errors_app_error_passthrough(self):
        @handle_service_errors
        def my_func():
            raise NotFoundError("资源", 1)

        with pytest.raises(NotFoundError):
            my_func()

    def test_handle_service_errors_generic_error(self):
        @handle_service_errors
        def my_func():
            raise RuntimeError("未知错误")

        with pytest.raises(DatabaseError):
            my_func()

    def test_safe_execute_success(self):
        result = safe_execute(lambda: 42)
        assert result == 42

    def test_safe_execute_error_default(self):
        result = safe_execute(lambda: 1 / 0, default=-1, log_error=False)
        assert result == -1

    def test_safe_execute_app_error(self):
        result = safe_execute(
            lambda: (_ for _ in ()).throw(AppError("业务错误")),
            default=None,
            log_error=False
        )
        assert result is None
