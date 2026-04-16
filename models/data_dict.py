from sqlalchemy import Column, Integer, String, Text, DateTime
from models.base import Base

class DataDict(Base):
    __tablename__ = "data_dicts"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(String(10), default="Y")
    created_at = Column(DateTime(timezone=True))
