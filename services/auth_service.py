from __future__ import annotations

from models.user import User, UserStatus
from services.crypto import verify_password
from services.audit_mixin import AuditMixin
from typing import Optional
from core.logger import get_logger
from core.database import get_db
from schemas.schemas import LoginRequest

logger = get_logger(__name__)


class AuthService(AuditMixin):
    def authenticate(self, username: str, password: str) -> Optional[User]:
        req = LoginRequest(username=username, password=password)

        user = self.get_user_by_username(req.username)
        if not user:
            logger.warning(f"登录失败: 用户不存在 - {req.username}")
            return None

        if not verify_password(req.password, user.hashed_password):
            logger.warning(f"登录失败: 密码错误 - {req.username}")
            return None

        if user.status != UserStatus.ACTIVE:
            logger.warning(f"登录失败: 用户状态异常 - {req.username}, 状态: {user.status}")
            return None

        logger.info(f"用户登录成功: {req.username}")
        return user

    def logout(self, user_id: int, username: str = None):
        logger.info(f"用户登出: {username or str(user_id)}")

    def get_user_by_username(self, username: str) -> Optional[User]:
        with get_db() as db:
            return db.query(User).filter(User.username == username).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        with get_db() as db:
            return db.query(User).filter(User.id == user_id).first()
