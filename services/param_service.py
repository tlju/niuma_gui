from sqlalchemy.orm import Session
from models.system_param import SystemParam
from typing import List, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class ParamService:
    def __init__(self, db: Session):
        self.db = db

    def create_param(self, param_key: str, param_value: str, param_type: str = "string",
                     description: str = None) -> SystemParam:
        existing = self.db.query(SystemParam).filter(
            SystemParam.param_key == param_key
        ).first()
        if existing:
            raise ValueError(f"参数键 {param_key} 已存在")

        param = SystemParam(
            param_key=param_key,
            param_value=param_value,
            param_type=param_type,
            description=description
        )
        self.db.add(param)
        self.db.commit()
        self.db.refresh(param)
        logger.info(f"创建系统参数: {param_key}")
        return param

    def get_params(self, skip: int = 0, limit: int = 100) -> List[SystemParam]:
        return self.db.query(SystemParam).offset(skip).limit(limit).all()

    def get_param(self, param_id: int) -> Optional[SystemParam]:
        return self.db.query(SystemParam).filter(SystemParam.id == param_id).first()

    def get_param_by_key(self, param_key: str) -> Optional[SystemParam]:
        return self.db.query(SystemParam).filter(SystemParam.param_key == param_key).first()

    def update_param(self, param_id: int, **kwargs) -> Optional[SystemParam]:
        param = self.get_param(param_id)
        if not param:
            return None

        if 'param_key' in kwargs and kwargs['param_key'] != param.param_key:
            existing = self.db.query(SystemParam).filter(
                SystemParam.param_key == kwargs['param_key'],
                SystemParam.id != param_id
            ).first()
            if existing:
                raise ValueError(f"参数键 {kwargs['param_key']} 已存在")

        for key, value in kwargs.items():
            if value is not None and hasattr(param, key):
                setattr(param, key, value)

        self.db.commit()
        self.db.refresh(param)
        logger.info(f"更新系统参数: {param.param_key}")
        return param

    def delete_param(self, param_id: int) -> bool:
        param = self.get_param(param_id)
        if param:
            self.db.delete(param)
            self.db.commit()
            logger.info(f"删除系统参数: {param.param_key}")
            return True
        return False

    def search_params(self, keyword: str) -> List[SystemParam]:
        return self.db.query(SystemParam).filter(
            SystemParam.param_key.like(f"%{keyword}%") |
            SystemParam.description.like(f"%{keyword}%")
        ).all()
