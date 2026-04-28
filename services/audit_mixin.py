"""
审计日志 Mixin 模块
提供统一的审计日志记录功能，供各服务类继承使用
"""
from typing import Optional
from models.audit_log import AuditLog
from core.logger import get_logger
from core.utils import get_local_now

logger = get_logger(__name__)


class AuditMixin:
    """
    审计日志 Mixin 类
    提供统一的审计日志记录方法，减少代码重复
    
    使用方式：
        class MyService(AuditMixin):
            def __init__(self, db: Session):
                self.db = db
            
            def create_something(self, ...):
                # 业务逻辑
                self.log_audit(
                    user_id=1,
                    action_type="create",
                    resource_type="something",
                    resource_id=obj.id,
                    details="创建资源"
                )
    """
    
    def log_audit(
        self,
        user_id: int,
        action_type: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Optional[AuditLog]:
        """
        记录审计日志
        
        Args:
            user_id: 操作用户ID
            action_type: 操作类型 (login, logout, create, update, delete, execute 等)
            resource_type: 资源类型 (user, script, asset, workflow, todo 等)
            resource_id: 资源ID (可选)
            details: 操作详情 (可选)
            ip_address: IP地址 (可选)
            
        Returns:
            创建的 AuditLog 对象，如果 user_id 为 None 则返回 None
        """
        if user_id is None:
            logger.debug(f"跳过审计日志记录: user_id 为空, action={action_type}, resource={resource_type}")
            return None
        
        if not hasattr(self, 'db'):
            logger.error("AuditMixin 使用错误: 类缺少 'db' 属性")
            return None
        
        try:
            audit = AuditLog(
                user_id=user_id,
                action_type=action_type,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
                created_at=get_local_now()
            )
            self.db.add(audit)
            self.db.commit()
            self.db.refresh(audit)
            
            logger.debug(
                f"审计日志已记录: user={user_id}, action={action_type}, "
                f"resource={resource_type}:{resource_id}, details={details}"
            )
            return audit
            
        except Exception as e:
            logger.error(f"记录审计日志失败: {e}")
            self.db.rollback()
            return None
    
    def log_create(self, user_id: int, resource_type: str, resource_id: int, 
                   resource_name: str = None, details: str = None) -> Optional[AuditLog]:
        """
        记录创建操作的审计日志
        
        Args:
            user_id: 操作用户ID
            resource_type: 资源类型
            resource_id: 资源ID
            resource_name: 资源名称 (可选，用于生成详情)
            details: 自定义详情 (可选，优先使用)
            
        Returns:
            创建的 AuditLog 对象
        """
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
        """
        记录更新操作的审计日志
        
        Args:
            user_id: 操作用户ID
            resource_type: 资源类型
            resource_id: 资源ID
            resource_name: 资源名称 (可选，用于生成详情)
            details: 自定义详情 (可选，优先使用)
            
        Returns:
            创建的 AuditLog 对象
        """
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
        """
        记录删除操作的审计日志
        
        Args:
            user_id: 操作用户ID
            resource_type: 资源类型
            resource_id: 资源ID
            resource_name: 资源名称 (可选，用于生成详情)
            details: 自定义详情 (可选，优先使用)
            
        Returns:
            创建的 AuditLog 对象
        """
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
        """
        记录执行操作的审计日志
        
        Args:
            user_id: 操作用户ID
            resource_type: 资源类型
            resource_id: 资源ID
            resource_name: 资源名称 (可选，用于生成详情)
            details: 自定义详情 (可选，优先使用)
            
        Returns:
            创建的 AuditLog 对象
        """
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
        """
        记录登录操作的审计日志
        
        Args:
            user_id: 用户ID
            username: 用户名 (可选)
            ip_address: IP地址 (可选)
            
        Returns:
            创建的 AuditLog 对象
        """
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
        """
        记录登出操作的审计日志
        
        Args:
            user_id: 用户ID
            username: 用户名 (可选)
            ip_address: IP地址 (可选)
            
        Returns:
            创建的 AuditLog 对象
        """
        details = f"用户登出: {username}" if username else f"用户登出: ID={user_id}"
        return self.log_audit(
            user_id=user_id,
            action_type="logout",
            resource_type="user",
            resource_id=user_id,
            details=details,
            ip_address=ip_address
        )
