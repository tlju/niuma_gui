from __future__ import annotations

from sqlalchemy import Column, Integer, String, ForeignKey
from models.base import Base


class DataDictItem(Base):
    __tablename__ = "data_dict_items"

    id = Column(Integer, primary_key=True)
    dict_code = Column(String(50), ForeignKey("data_dicts.code"), nullable=False)
    item_code = Column(String(50), nullable=False)
    item_name = Column(String(100), nullable=False)
    sort_order = Column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<DataDictItem(id={self.id}, dict='{self.dict_code}', code='{self.item_code}', name='{self.item_name}')>"
