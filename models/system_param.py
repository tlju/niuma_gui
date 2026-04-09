from sqlalchemy import Column, Integer, String, Text
from models.base import Base

class SystemParam(Base):
    __tablename__ = "system_params"

    id = Column(Integer, primary_key=True)
    param_name = Column(String(100), nullable=False)
    param_code = Column(String(100), unique=True, nullable=False)
    param_value = Column(Text)
    status = Column(Integer, default=1)  # 0: 禁用, 1: 启用
    description = Column(Text)
