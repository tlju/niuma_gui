from sqlalchemy import Column, Integer, String, DateTime
from models.base import Base

class DataDictItem(Base):
    __tablename__ = "data_dict_items"

    id = Column(Integer, primary_key=True)
    dict_code = Column(String(50), nullable=False)
    item_code = Column(String(50), nullable=False)
    item_name = Column(String(100), nullable=False)
    sort_order = Column(Integer, default=0)
    is_active = Column(String(10), default="Y")
