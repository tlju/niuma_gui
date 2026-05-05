from __future__ import annotations

from enum import Enum
from typing import Optional, Any


class ErrorCode(int, Enum):
    SUCCESS = 0
    UNKNOWN_ERROR = 1000
    VALIDATION_ERROR = 1001
    AUTH_FAILED = 1002
    PERMISSION_DENIED = 1003
    NOT_FOUND = 1004
    ALREADY_EXISTS = 1005
    DB_ERROR = 1006
    CONNECTION_ERROR = 1007
    TIMEOUT_ERROR = 1008
    BUSINESS_ERROR = 1009


class AppError(Exception):
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details
        }

    def __repr__(self) -> str:
        return f"<AppError(code={self.code.value}, message='{self.message}')>"


class ValidationError(AppError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, ErrorCode.VALIDATION_ERROR, details)


class AuthError(AppError):
    def __init__(self, message: str = "认证失败", details: Optional[dict] = None):
        super().__init__(message, ErrorCode.AUTH_FAILED, details)


class PermissionError(AppError):
    def __init__(self, message: str = "权限不足", details: Optional[dict] = None):
        super().__init__(message, ErrorCode.PERMISSION_DENIED, details)


class NotFoundError(AppError):
    def __init__(self, resource: str = "资源", resource_id: Any = None):
        msg = f"{resource}不存在"
        if resource_id is not None:
            msg = f"{resource}(id={resource_id})不存在"
        super().__init__(msg, ErrorCode.NOT_FOUND, {"resource": resource, "id": resource_id})


class AlreadyExistsError(AppError):
    def __init__(self, resource: str = "资源", field: str = "", value: Any = None):
        msg = f"{resource}已存在"
        if field and value is not None:
            msg = f"{resource}的{field}='{value}'已存在"
        super().__init__(msg, ErrorCode.ALREADY_EXISTS, {"resource": resource, "field": field, "value": value})


class DatabaseError(AppError):
    def __init__(self, message: str = "数据库操作失败", details: Optional[dict] = None):
        super().__init__(message, ErrorCode.DB_ERROR, details)


class ConnectionError(AppError):
    def __init__(self, message: str = "连接失败", details: Optional[dict] = None):
        super().__init__(message, ErrorCode.CONNECTION_ERROR, details)


class TimeoutError(AppError):
    def __init__(self, message: str = "操作超时", details: Optional[dict] = None):
        super().__init__(message, ErrorCode.TIMEOUT_ERROR, details)


class BusinessError(AppError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, ErrorCode.BUSINESS_ERROR, details)
