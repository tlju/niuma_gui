from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base

class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    description = Column(Text)
    language = Column(String(20), default="bash")

    server_id = Column(Integer, ForeignKey("server_assets.id"), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    server = relationship("ServerAsset", back_populates="scripts")
    exec_logs = relationship("ExecLog", back_populates="script")
