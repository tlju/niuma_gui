from sqlalchemy.orm import Session
from models.script import Script
from services.audit_mixin import AuditMixin
from typing import List, Optional
from core.logger import get_logger
from core.utils import get_local_now

logger = get_logger(__name__)


class ScriptService(AuditMixin):
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

        self.log_create(
            user_id=created_by,
            resource_type="script",
            resource_id=script.id,
            resource_name=name
        )

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

        self.log_update(
            user_id=updated_by,
            resource_type="script",
            resource_id=script_id,
            resource_name=script.name
        )

        return True

    def delete(self, script_id: int, user_id: int) -> bool:
        script = self.get_by_id(script_id)
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

        self.db.delete(script)
        self.db.commit()
        logger.info(f"删除脚本: {script_name}, ID: {script_id}")
        return True
