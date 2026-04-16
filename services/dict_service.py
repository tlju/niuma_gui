from sqlalchemy.orm import Session
from models.data_dict import DataDict
from models.data_dict_item import DataDictItem
from typing import List, Optional
from core.logger import get_logger
from core.utils import get_local_now

logger = get_logger(__name__)


class DictService:
    def __init__(self, db: Session):
        self.db = db

    def create_dict(self, code: str, name: str, description: str = None) -> DataDict:
        existing = self.db.query(DataDict).filter(DataDict.code == code).first()
        if existing:
            raise ValueError(f"字典代码 {code} 已存在")

        dict_obj = DataDict(
            code=code,
            name=name,
            description=description,
            created_at=get_local_now()
        )
        self.db.add(dict_obj)
        self.db.commit()
        self.db.refresh(dict_obj)
        logger.info(f"创建数据字典: {code}")
        return dict_obj

    def get_dicts(self, skip: int = 0, limit: int = 100) -> List[DataDict]:
        return self.db.query(DataDict).offset(skip).limit(limit).all()

    def get_dict(self, dict_id: int) -> Optional[DataDict]:
        return self.db.query(DataDict).filter(DataDict.id == dict_id).first()

    def get_dict_by_code(self, code: str) -> Optional[DataDict]:
        return self.db.query(DataDict).filter(DataDict.code == code).first()

    def update_dict(self, dict_id: int, **kwargs) -> Optional[DataDict]:
        dict_obj = self.get_dict(dict_id)
        if not dict_obj:
            return None

        if 'code' in kwargs and kwargs['code'] != dict_obj.code:
            existing = self.db.query(DataDict).filter(
                DataDict.code == kwargs['code'],
                DataDict.id != dict_id
            ).first()
            if existing:
                raise ValueError(f"字典代码 {kwargs['code']} 已存在")

        for key, value in kwargs.items():
            if value is not None and hasattr(dict_obj, key):
                setattr(dict_obj, key, value)

        self.db.commit()
        self.db.refresh(dict_obj)
        logger.info(f"更新数据字典: {dict_obj.code}")
        return dict_obj

    def delete_dict(self, dict_id: int) -> bool:
        dict_obj = self.get_dict(dict_id)
        if dict_obj:
            self.db.query(DataDictItem).filter(DataDictItem.dict_code == dict_obj.code).delete()
            self.db.delete(dict_obj)
            self.db.commit()
            logger.info(f"删除数据字典: {dict_obj.code}")
            return True
        return False

    def create_dict_item(self, dict_code: str, item_code: str, item_name: str,
                         sort_order: int = 0) -> DataDictItem:
        dict_obj = self.get_dict_by_code(dict_code)
        if not dict_obj:
            raise ValueError(f"字典 {dict_code} 不存在")

        existing = self.db.query(DataDictItem).filter(
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
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        logger.info(f"创建字典项: {dict_code}.{item_code}")
        return item

    def get_dict_items(self, dict_code: str) -> List[DataDictItem]:
        return self.db.query(DataDictItem).filter(
            DataDictItem.dict_code == dict_code
        ).order_by(DataDictItem.sort_order).all()

    def get_dict_item(self, item_id: int) -> Optional[DataDictItem]:
        return self.db.query(DataDictItem).filter(DataDictItem.id == item_id).first()

    def update_dict_item(self, item_id: int, **kwargs) -> Optional[DataDictItem]:
        item = self.get_dict_item(item_id)
        if not item:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(item, key):
                setattr(item, key, value)

        self.db.commit()
        self.db.refresh(item)
        logger.info(f"更新字典项: {item.dict_code}.{item.item_code}")
        return item

    def delete_dict_item(self, item_id: int) -> bool:
        item = self.get_dict_item(item_id)
        if item:
            self.db.delete(item)
            self.db.commit()
            logger.info(f"删除字典项: {item.dict_code}.{item.item_code}")
            return True
        return False

    def search_dicts(self, keyword: str) -> List[DataDict]:
        return self.db.query(DataDict).filter(
            DataDict.name.like(f"%{keyword}%") |
            DataDict.code.like(f"%{keyword}%")
        ).all()

    def get_item_name_by_code(self, dict_code: str, item_code: str) -> Optional[str]:
        """
        通过字典代码和项代码获取项名称
        
        Args:
            dict_code: 字典代码
            item_code: 字典项代码
            
        Returns:
            字典项名称，如果不存在则返回 None
        """
        if not dict_code or not item_code:
            return None
        item = self.db.query(DataDictItem).filter(
            DataDictItem.dict_code == dict_code,
            DataDictItem.item_code == item_code
        ).first()
        return item.item_name if item else None

    def get_item_code_by_name(self, dict_code: str, item_name: str) -> Optional[str]:
        """
        通过字典代码和项名称获取项代码
        
        Args:
            dict_code: 字典代码
            item_name: 字典项名称
            
        Returns:
            字典项代码，如果不存在则返回 None
        """
        if not dict_code or not item_name:
            return None
        item = self.db.query(DataDictItem).filter(
            DataDictItem.dict_code == dict_code,
            DataDictItem.item_name == item_name
        ).first()
        return item.item_code if item else None
