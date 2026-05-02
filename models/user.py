from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from models.base import Base
from enum import IntEnum


class UserStatus(IntEnum):
    INACTIVE = 0
    ACTIVE = 1
    LOCKED = 2


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    email = Column(String(100))
    status = Column(Integer, default=UserStatus.ACTIVE)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
