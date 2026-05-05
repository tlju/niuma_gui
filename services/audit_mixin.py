from __future__ import annotations

from typing import Optional
from models.audit_log import AuditLog
from core.logger import get_logger
from core.utils import get_local_now
from core.database import get_db

logger = get_logger(__name__)


class AuditMixin:

    def log_audit(
        self,
        user_id: int,
        action_type: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Optional[AuditLog]:
        if user_id is None:
            logger.debug(f"跳过审计日志记录: user_id 为空, action={action_type}, resource={resource_type}")
            return None

        try:
            with get_db() as audit_db:
                audit = AuditLog(
                    user_id=user_id,
                    action_type=action_type,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    details=details,
                    ip_address=ip_address,
                    created_at=get_local_now()
                )
                audit_db.add(audit)
                audit_db.commit()
                audit_db.refresh(audit)

                logger.debug(
                    f"审计日志已记录: user={user_id}, action={action_type}, "
                    f"resource={resource_type}:{resource_id}, details={details}"
                )
                return audit

        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")
            return None

    def log_create(self, user_id: int, resource_type: str, resource_id: int,
                   resource_name: str = None, details: str = None) -> Optional[AuditLog]:
        if details is None and resource_name:
            details = f"创建{resource_type}: {resource_name}"
        return self.log_audit(
            user_id=user_id,
            action_type="create",
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )

    def log_update(self, user_id: int, resource_type: str, resource_id: int,
                   resource_name: str = None, details: str = None) -> Optional[AuditLog]:
        if details is None and resource_name:
            details = f"更新{resource_type}: {resource_name}"
        return self.log_audit(
            user_id=user_id,
            action_type="update",
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )

    def log_delete(self, user_id: int, resource_type: str, resource_id: int,
                   resource_name: str = None, details: str = None) -> Optional[AuditLog]:
        if details is None and resource_name:
            details = f"删除{resource_type}: {resource_name}"
        return self.log_audit(
            user_id=user_id,
            action_type="delete",
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )

    def log_execute(self, user_id: int, resource_type: str, resource_id: int,
                    resource_name: str = None, details: str = None) -> Optional[AuditLog]:
        if details is None and resource_name:
            details = f"执行{resource_type}: {resource_name}"
        return self.log_audit(
            user_id=user_id,
            action_type="execute",
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )

    def log_login(self, user_id: int, username: str = None,
                  ip_address: str = None) -> Optional[AuditLog]:
        details = f"用户登录: {username}" if username else f"用户登录: ID={user_id}"
        return self.log_audit(
            user_id=user_id,
            action_type="login",
            resource_type="user",
            resource_id=user_id,
            details=details,
            ip_address=ip_address
        )

    def log_logout(self, user_id: int, username: str = None,
                   ip_address: str = None) -> Optional[AuditLog]:
        details = f"用户登出: {username}" if username else f"用户登出: ID={user_id}"
        return self.log_audit(
            user_id=user_id,
            action_type="logout",
            resource_type="user",
            resource_id=user_id,
            details=details,
            ip_address=ip_address
        )
