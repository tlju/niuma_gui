from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from models.base import Base
from enum import Enum

class UserStatus:
    ACTIVE = 1  # 启用
    INACTIVE = 0  # 禁用
    LOCKED = 2  # 锁定

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    email = Column(String(100))
    status = Column(Integer, default=UserStatus.ACTIVE)  # 0: 禁用, 1: 启用, 2: 锁定
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
