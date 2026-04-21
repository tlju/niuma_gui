from sqlalchemy.orm import Session
from models.script import Script
from models.audit_log import AuditLog
from typing import List, Optional
from core.logger import get_logger
from core.utils import get_local_now

logger = get_logger(__name__)

class ScriptService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        name: str,
        content: str,
        description: Optional[str] = None,
        language: Optional[str] = None,
        server_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> Optional[int]:
        script = Script(
            name=name,
            content=content,
            description=description,
            language=language,
            server_id=server_id,
            created_by=created_by,
            created_at=get_local_now()
        )
        self.db.add(script)
        self.db.commit()
        self.db.refresh(script)
        logger.info(f"创建脚本: {name}, ID: {script.id}")

        if created_by:
            audit = AuditLog(
                user_id=created_by,
                action_type="create",
                resource_type="script",
                resource_id=script.id,
                details=f"创建脚本: {name}",
                created_at=get_local_now()
            )
            self.db.add(audit)
            self.db.commit()

        return script.id

    def get_all(self) -> List[Script]:
        return self.db.query(Script).order_by(Script.id).all()

    def get_by_id(self, script_id: int) -> Optional[Script]:
        return self.db.query(Script).filter(Script.id == script_id).first()

    def update(
        self,
        script_id: int,
        name: Optional[str] = None,
        content: Optional[str] = None,
        description: Optional[str] = None,
        language: Optional[str] = None,
        updated_by: Optional[int] = None
    ) -> bool:
        script = self.get_by_id(script_id)
        if not script:
            return False

        if name is not None:
            script.name = name
        if content is not None:
            script.content = content
        if description is not None:
            script.description = description
        if language is not None:
            script.language = language

        script.updated_at = get_local_now()
        self.db.commit()
        logger.info(f"更新脚本: {script.name}, ID: {script_id}")

        if updated_by:
            audit = AuditLog(
                user_id=updated_by,
                action_type="update",
                resource_type="script",
                resource_id=script_id,
                details=f"更新脚本: {script.name}",
                created_at=get_local_now()
            )
            self.db.add(audit)
            self.db.commit()

        return True

    def delete(self, script_id: int, user_id: int) -> bool:
        script = self.get_by_id(script_id)
        if not script:
            logger.warning(f"删除脚本失败: 脚本不存在, ID: {script_id}")
            return False

        script_name = script.name
        audit = AuditLog(
            user_id=user_id,
            action_type="delete",
            resource_type="script",
            resource_id=script_id,
            details=f"删除脚本: {script.name}",
            created_at=get_local_now()
        )
        self.db.add(audit)

        self.db.delete(script)
        self.db.commit()
        logger.info(f"删除脚本: {script_name}, ID: {script_id}")
        return True
