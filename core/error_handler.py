from __future__ import annotations

import functools
import traceback
from typing import Callable, Any, Optional, TypeVar
from core.logger import get_logger
from core.exceptions import AppError, DatabaseError, ValidationError

logger = get_logger(__name__)

T = TypeVar("T")


def handle_service_errors(func: Callable[..., T]) -> Callable[..., T]:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except AppError:
            raise
        except ValueError as e:
            raise ValidationError(str(e)) from e
        except Exception as e:
            logger.error(f"服务层异常 [{func.__qualname__}]: {e}\n{traceback.format_exc()}")
            raise DatabaseError(f"操作失败: {str(e)}") from e

    return wrapper


def safe_execute(func: Callable[..., T], default: Any = None, log_error: bool = True) -> T | Any:
    try:
        return func()
    except AppError as e:
        if log_error:
            logger.error(f"业务异常: {e.message}")
        return default
    except Exception as e:
        if log_error:
            logger.error(f"未知异常: {e}\n{traceback.format_exc()}")
        return default
