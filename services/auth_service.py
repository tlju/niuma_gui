from sqlalchemy.orm import Session
from models.user import User, UserStatus
from models.audit_log import AuditLog
from services.crypto import verify_password
from typing import Optional
from core.logger import get_logger
from core.utils import get_local_now

logger = get_logger(__name__)

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_username(username)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if user.status != UserStatus.ACTIVE:
            return None

        self._log_audit(user.id, "login", "user", user.id, f"用户登录: {username}")

        return user

    def logout(self, user_id: int, username: str = None):
        self._log_audit(user_id, "logout", "user", user_id, f"用户登出: {username or str(user_id)}")

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def _log_audit(
        self,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: int,
        details: Optional[str] = None
    ):
        audit = AuditLog(
            user_id=user_id,
            action_type=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            created_at=get_local_now()
        )
        self.db.add(audit)
        self.db.commit()
