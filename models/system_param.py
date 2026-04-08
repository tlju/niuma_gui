from sqlalchemy import Column, Integer, String, Text
from models.base import Base

class SystemParam(Base):
    __tablename__ = "system_params"

    id = Column(Integer, primary_key=True)
    param_key = Column(String(100), unique=True, nullable=False)
    param_value = Column(Text)
    param_type = Column(String(20), default="string")  # string, int, bool, json
    description = Column(Text)
