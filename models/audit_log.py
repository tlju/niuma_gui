from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from models.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    action_type = Column(String(50), nullable=False)  # login, create, update, delete, execute
    resource_type = Column(String(50))
    resource_id = Column(Integer)

    ip_address = Column(String(50))
    details = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
