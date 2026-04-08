from sqlalchemy.orm import Session
from models.script import Script
from models.exec_log import ExecLog
from models.audit_log import AuditLog
from models.server_asset import ServerAsset
from services.crypto import CryptoManager
from typing import List, Optional
from core.config import settings
from core.logger import get_logger
import paramiko

logger = get_logger(__name__)

class ScriptService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        name: str,
        content: str,
        description: Optional[str] = None,
        server_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> Optional[int]:
        script = Script(
            name=name,
            content=content,
            description=description,
            server_id=server_id,
            created_by=created_by
        )
        self.db.add(script)
        self.db.commit()
        self.db.refresh(script)

        # 记录审计日志
        if created_by:
            audit = AuditLog(
                user_id=created_by,
                action_type="create",
                resource_type="script",
                resource_id=script.id
            )
            self.db.add(audit)
            self.db.commit()

        return script.id

    def get_all(self) -> List[Script]:
        return self.db.query(Script).order_by(Script.id).all()

    def get_by_id(self, script_id: int) -> Optional[Script]:
        return self.db.query(Script).filter(Script.id == script_id).first()

    def execute(
        self,
        script: Script,
        server_id: int,
        executed_by: Optional[int] = None
    ) -> Optional[int]:
        server = self.db.query(ServerAsset).filter(
            ServerAsset.id == server_id
        ).first()
        if not server:
            return None

        # 获取服务器密码
        from services.asset_service import AssetService
        asset_service = AssetService(self.db)
        password = asset_service.get_password(server_id)

        # 创建执行日志
        exec_log = ExecLog(
            script_id=script.id,
            server_id=server_id,
            status="running",
            executed_by=executed_by
        )
        self.db.add(exec_log)
        self.db.commit()
        self.db.refresh(exec_log)

        # 执行脚本
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=server.ip,
                port=server.port,
                username=server.username,
                password=password,
                timeout=30
            )

            stdin, stdout, stderr = ssh.exec_command(script.content)
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')

            exec_log.status = "success" if not error else "failed"
            exec_log.output = output
            exec_log.error = error

            ssh.close()

        except Exception as e:
            exec_log.status = "failed"
            exec_log.error = str(e)

        self.db.commit()

        # 记录审计日志
        if executed_by:
            audit = AuditLog(
                user_id=executed_by,
                action_type="execute",
                resource_type="script",
                resource_id=script.id,
                details=f"Executed on server {server_id}"
            )
            self.db.add(audit)
            self.db.commit()

        return exec_log.id

    def delete(self, script_id: int, user_id: int) -> bool:
        script = self.get_by_id(script_id)
        if not script:
            return False

        audit = AuditLog(
            user_id=user_id,
            action_type="delete",
            resource_type="script",
            resource_id=script_id
        )
        self.db.add(audit)

        self.db.delete(script)
        self.db.commit()
        return True
