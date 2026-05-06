from __future__ import annotations

from enum import Enum


class AuditActionType(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    IMPORT = "import"
    EXPORT = "export"


class ResourceType(str, Enum):
    USER = "user"
    SCRIPT = "script"
    ASSET = "asset"
    WORKFLOW = "workflow"
    WORKFLOW_EXECUTION = "workflow_execution"
    TODO = "todo"
    DOCUMENT = "document"
    DATA_DICT = "data_dict"
    SYSTEM_PARAM = "system_param"


class UserStatus(int, Enum):
    INACTIVE = 0
    ACTIVE = 1
    LOCKED = 2


class TodoStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in"
    COMPLETED = "completed"


class RecurrenceType(str, Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


LIKE_ESCAPE_CHAR = "\\"
DEFAULT_PAGE_SIZE = 100
