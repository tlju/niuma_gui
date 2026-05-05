from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text, DateTime
from models.base import Base


class DataDict(Base):
    __tablename__ = "data_dicts"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<DataDict(id={self.id}, code='{self.code}', name='{self.name}')>"
