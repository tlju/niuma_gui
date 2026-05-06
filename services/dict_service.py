from __future__ import annotations

from models.data_dict import DataDict
from models.data_dict_item import DataDictItem
from typing import List, Optional
from core.logger import get_logger
from core.utils import get_local_now, escape_like_wildcards
from core.database import get_db

logger = get_logger(__name__)


class DictService:
    UPDATABLE_FIELDS = frozenset({"code", "name", "description"})
    UPDATABLE_ITEM_FIELDS = frozenset({"item_code", "item_name", "sort_order"})

    def create_dict(self, code: str, name: str, description: str = None) -> DataDict:
        with get_db() as db:
            existing = db.query(DataDict).filter(DataDict.code == code).first()
            if existing:
                raise ValueError(f"字典代码 {code} 已存在")

            dict_obj = DataDict(
                code=code,
                name=name,
                description=description,
                created_at=get_local_now()
            )
            db.add(dict_obj)
            db.commit()
            db.refresh(dict_obj)
            logger.info(f"创建数据字典: {code}")
            return dict_obj

    def get_dicts(self, skip: int = 0, limit: int = 100) -> List[DataDict]:
        with get_db() as db:
            return db.query(DataDict).offset(skip).limit(limit).all()

    def get_dict(self, dict_id: int) -> Optional[DataDict]:
        with get_db() as db:
            return db.query(DataDict).filter(DataDict.id == dict_id).first()

    def get_dict_by_code(self, code: str) -> Optional[DataDict]:
        with get_db() as db:
            return db.query(DataDict).filter(DataDict.code == code).first()

    def update_dict(self, dict_id: int, **kwargs) -> Optional[DataDict]:
        with get_db() as db:
            dict_obj = db.query(DataDict).filter(DataDict.id == dict_id).first()
            if not dict_obj:
                return None

            if 'code' in kwargs and kwargs['code'] != dict_obj.code:
                existing = db.query(DataDict).filter(
                    DataDict.code == kwargs['code'],
                    DataDict.id != dict_id
                ).first()
                if existing:
                    raise ValueError(f"字典代码 {kwargs['code']} 已存在")

            for key, value in kwargs.items():
                if key in self.UPDATABLE_FIELDS and value is not None:
                    setattr(dict_obj, key, value)

            db.commit()
            db.refresh(dict_obj)
            logger.info(f"更新数据字典: {dict_obj.code}")
            return dict_obj

    def delete_dict(self, dict_id: int) -> bool:
        with get_db() as db:
            dict_obj = db.query(DataDict).filter(DataDict.id == dict_id).first()
            if dict_obj:
                db.query(DataDictItem).filter(DataDictItem.dict_code == dict_obj.code).delete()
                db.delete(dict_obj)
                db.commit()
                logger.info(f"删除数据字典: {dict_obj.code}")
                return True
            return False

    def create_dict_item(self, dict_code: str, item_code: str, item_name: str,
                         sort_order: int = 0) -> DataDictItem:
        with get_db() as db:
            dict_obj = db.query(DataDict).filter(DataDict.code == dict_code).first()
            if not dict_obj:
                raise ValueError(f"字典 {dict_code} 不存在")

            existing = db.query(DataDictItem).filter(
                DataDictItem.dict_code == dict_code,
                DataDictItem.item_code == item_code
            ).first()
            if existing:
                raise ValueError(f"字典项代码 {item_code} 已存在")

            item = DataDictItem(
                dict_code=dict_code,
                item_code=item_code,
                item_name=item_name,
                sort_order=sort_order
            )
            db.add(item)
            db.commit()
            db.refresh(item)
            logger.info(f"创建字典项: {dict_code}.{item_code}")
            return item

    def get_dict_items(self, dict_code: str) -> List[DataDictItem]:
        with get_db() as db:
            return db.query(DataDictItem).filter(
                DataDictItem.dict_code == dict_code
            ).order_by(DataDictItem.sort_order).all()

    def get_dict_item(self, item_id: int) -> Optional[DataDictItem]:
        with get_db() as db:
            return db.query(DataDictItem).filter(DataDictItem.id == item_id).first()

    def update_dict_item(self, item_id: int, **kwargs) -> Optional[DataDictItem]:
        with get_db() as db:
            item = db.query(DataDictItem).filter(DataDictItem.id == item_id).first()
            if not item:
                return None

            for key, value in kwargs.items():
                if key in self.UPDATABLE_ITEM_FIELDS and value is not None:
                    setattr(item, key, value)

            db.commit()
            db.refresh(item)
            logger.info(f"更新字典项: {item.dict_code}.{item.item_code}")
            return item

    def delete_dict_item(self, item_id: int) -> bool:
        with get_db() as db:
            item = db.query(DataDictItem).filter(DataDictItem.id == item_id).first()
            if item:
                db.delete(item)
                db.commit()
                logger.info(f"删除字典项: {item.dict_code}.{item.item_code}")
                return True
            return False

    def search_dicts(self, keyword: str) -> List[DataDict]:
        escaped = escape_like_wildcards(keyword)
        with get_db() as db:
            return db.query(DataDict).filter(
                DataDict.name.like(f"%{escaped}%", escape='\\') |
                DataDict.code.like(f"%{escaped}%", escape='\\')
            ).all()

    def get_item_name_by_code(self, dict_code: str, item_code: str) -> Optional[str]:
        if not dict_code or not item_code:
            return None
        with get_db() as db:
            item = db.query(DataDictItem).filter(
                DataDictItem.dict_code == dict_code,
                DataDictItem.item_code == item_code
            ).first()
            return item.item_name if item else None

    def get_item_code_by_name(self, dict_code: str, item_name: str) -> Optional[str]:
        if not dict_code or not item_name:
            return None
        with get_db() as db:
            item = db.query(DataDictItem).filter(
                DataDictItem.dict_code == dict_code,
                DataDictItem.item_name == item_name
            ).first()
            return item.item_code if item else None
