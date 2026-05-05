from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from models.base import Base
from core.constants import TodoStatus, RecurrenceType


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(20), default=TodoStatus.PENDING)
    priority = Column(Integer, default=5)
    assigned_to = Column(Integer, ForeignKey("users.id"))
    due_date = Column(DateTime(timezone=True))
    recurrence_type = Column(String(20), default=RecurrenceType.NONE)
    recurrence_interval = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Todo(id={self.id}, title='{self.title}', status='{self.status}')>"
