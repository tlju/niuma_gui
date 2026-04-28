from sqlalchemy.orm import Session
from models.user import User, UserStatus
from services.crypto import verify_password
from services.audit_mixin import AuditMixin
from typing import Optional
from core.logger import get_logger

logger = get_logger(__name__)


class AuthService(AuditMixin):
    def __init__(self, db: Session):
        self.db = db

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_username(username)
        if not user:
            logger.warning(f"登录失败: 用户不存在 - {username}")
            return None

        if not verify_password(password, user.hashed_password):
            logger.warning(f"登录失败: 密码错误 - {username}")
            return None

        if user.status != UserStatus.ACTIVE:
            logger.warning(f"登录失败: 用户状态异常 - {username}, 状态: {user.status}")
            return None

        self.log_login(user.id, username)
        logger.info(f"用户登录成功: {username}")
        return user

    def logout(self, user_id: int, username: str = None):
        self.log_logout(user_id, username)
        logger.info(f"用户登出: {username or str(user_id)}")

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
