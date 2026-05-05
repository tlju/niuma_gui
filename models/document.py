from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from models.base import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    category = Column(String(50))
    tags = Column(String(200))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}', category='{self.category}')>"
