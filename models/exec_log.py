from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base

class ExecStatus(str):
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"

class ExecLog(Base):
    __tablename__ = "exec_logs"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    server_id = Column(Integer, ForeignKey("server_assets.id"), nullable=False)

    status = Column(String(20), default=ExecStatus.RUNNING)
    output = Column(Text)
    error = Column(Text)

    executed_by = Column(Integer, ForeignKey("users.id"))
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    script = relationship("Script", back_populates="exec_logs")
    server = relationship("ServerAsset", back_populates="exec_logs")
