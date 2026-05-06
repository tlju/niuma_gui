from __future__ import annotations

from models.script import Script
from services.audit_mixin import AuditMixin
from typing import List, Optional
from core.logger import get_logger
from core.utils import get_local_now
from core.database import get_db

logger = get_logger(__name__)


class ScriptService(AuditMixin):
    UPDATABLE_FIELDS = frozenset({"name", "content", "description", "language"})

    def create(
        self,
        name: str,
        content: str,
        description: Optional[str] = None,
        language: Optional[str] = None,
        server_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> Optional[int]:
        with get_db() as db:
            script = Script(
                name=name,
                content=content,
                description=description,
                language=language,
                server_id=server_id,
                created_by=created_by,
                created_at=get_local_now()
            )
            db.add(script)
            db.commit()
            db.refresh(script)
            logger.info(f"创建脚本: {name}, ID: {script.id}")

        self.log_create(
            user_id=created_by,
            resource_type="script",
            resource_id=script.id,
            resource_name=name
        )

        return script.id

    def get_all(self) -> List[Script]:
        with get_db() as db:
            return db.query(Script).order_by(Script.id).all()

    def get_by_id(self, script_id: int) -> Optional[Script]:
        with get_db() as db:
            return db.query(Script).filter(Script.id == script_id).first()

    def update(
        self,
        script_id: int,
        user_id: Optional[int] = None,
        **kwargs
    ) -> bool:
        with get_db() as db:
            script = db.query(Script).filter(Script.id == script_id).first()
            if not script:
                return False

            for key, value in kwargs.items():
                if key in self.UPDATABLE_FIELDS and value is not None:
                    setattr(script, key, value)

            script.updated_at = get_local_now()
            db.commit()
            logger.info(f"更新脚本: {script.name}, ID: {script_id}")

        self.log_update(
            user_id=user_id,
            resource_type="script",
            resource_id=script_id,
            resource_name=script.name
        )

        return True

    def delete(self, script_id: int, user_id: int) -> bool:
        with get_db() as db:
            script = db.query(Script).filter(Script.id == script_id).first()
            if not script:
                logger.warning(f"删除脚本失败: 脚本不存在, ID: {script_id}")
                return False

            script_name = script.name

            self.log_delete(
                user_id=user_id,
                resource_type="script",
                resource_id=script_id,
                resource_name=script_name
            )

            db.delete(script)
            db.commit()
            logger.info(f"删除脚本: {script_name}, ID: {script_id}")
        return True
