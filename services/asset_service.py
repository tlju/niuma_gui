from sqlalchemy.orm import Session
from models.server_asset import ServerAsset
from models.audit_log import AuditLog
from services.crypto import CryptoManager
from typing import List, Optional
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

class AssetService:
    def __init__(self, db: Session):
        self.db = db
        self.crypto = CryptoManager(settings.CRYPTO_KEY)

    def create(
        self,
        name: str,
        ip: str,
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        hostname: Optional[str] = None,
        os_type: str = "Linux",
        description: Optional[str] = None
    ) -> Optional[int]:
        password_cipher = self.crypto.encrypt(password) if password else None

        asset = ServerAsset(
            name=name,
            hostname=hostname,
            ip=ip,
            port=port,
            os_type=os_type,
            description=description,
            username=username,
            password_cipher=password_cipher
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)

        return asset.id

    def get_all(self) -> List[ServerAsset]:
        return self.db.query(ServerAsset).order_by(ServerAsset.id).all()

    def get_by_id(self, asset_id: int) -> Optional[ServerAsset]:
        return self.db.query(ServerAsset).filter(ServerAsset.id == asset_id).first()

    def update(self, asset_id: int, **kwargs) -> bool:
        asset = self.get_by_id(asset_id)
        if not asset:
            return False

        for key, value in kwargs.items():
            if hasattr(asset, key) and value is not None:
                if key == "password":
                    setattr(asset, f"{key}_cipher", self.crypto.encrypt(value))
                else:
                    setattr(asset, key, value)

        self.db.commit()
        return True

    def delete(self, asset_id: int, user_id: int) -> bool:
        asset = self.get_by_id(asset_id)
        if not asset:
            return False

        # 记录审计日志
        audit = AuditLog(
            user_id=user_id,
            action_type="delete",
            resource_type="asset",
            resource_id=asset_id
        )
        self.db.add(audit)

        self.db.delete(asset)
        self.db.commit()
        return True

    def get_password(self, asset_id: int) -> Optional[str]:
        asset = self.get_by_id(asset_id)
        if not asset or not asset.password_cipher:
            return None
        return self.crypto.decrypt(asset.password_cipher)
