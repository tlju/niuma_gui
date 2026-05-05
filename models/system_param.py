from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text
from models.base import Base


class SystemParam(Base):
    __tablename__ = "system_params"

    id = Column(Integer, primary_key=True)
    param_name = Column(String(100), nullable=False)
    param_code = Column(String(100), unique=True, nullable=False)
    param_value = Column(Text)
    status = Column(Integer, default=1)
    description = Column(Text)

    def __repr__(self) -> str:
        return f"<SystemParam(id={self.id}, code='{self.param_code}', name='{self.param_name}')>"
