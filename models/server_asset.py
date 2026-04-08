from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base

class ServerAsset(Base):
    __tablename__ = "server_assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    hostname = Column(String(255))
    ip = Column(String(50), nullable=False)
    port = Column(Integer, default=22)
    os_type = Column(String(50))  # Linux, Windows, macOS
    description = Column(Text)

    # 认证信息
    username = Column(String(50))
    password_cipher = Column(String(500))  # 加密存储
    private_key_cipher = Column(String(2000))  # 加密存储
    auth_type = Column(String(20), default="password")  # password, key

    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系 - 待 Script 和 ExecLog 模型实现后再启用
    # scripts = relationship("Script", back_populates="server")
    # exec_logs = relationship("ExecLog", back_populates="server")
