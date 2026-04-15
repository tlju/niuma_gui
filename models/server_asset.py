from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base

class ServerAsset(Base):
    __tablename__ = "server_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    unit_name = Column(String(100), nullable=False)
    system_name = Column(String(100), nullable=False)
    ip = Column(String(45), nullable=True)
    ipv6 = Column(String(45), nullable=True)
    port = Column(Integer, nullable=True)
    host_name = Column(String(100), nullable=True)
    username = Column(String(100), nullable=False)
    password_cipher = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    business_service = Column(String(200), nullable=True)
    location = Column(String(100), nullable=True)
    server_type = Column(String(100), nullable=True)
    vip = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=func.now())

    scripts = relationship("Script", back_populates="server")
