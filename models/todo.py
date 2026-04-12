from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from models.base import Base

class TodoStatus(str):
    PENDING = "pending"
    IN_PROGRESS = "in"
    COMPLETED = "completed"

class RecurrenceType(str):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
