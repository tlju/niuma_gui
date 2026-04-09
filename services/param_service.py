from sqlalchemy.orm import Session
from models.system_param import SystemParam
from typing import List, Optional
from core.logger import get_logger

logger = get_logger(__name__)


class ParamService:
    def __init__(self, db: Session):
        self.db = db

    def create_param(self, param_name: str, param_code: str, param_value: str,
                     status: int = 1, description: str = None) -> SystemParam:
        existing = self.db.query(SystemParam).filter(
            SystemParam.param_code == param_code
        ).first()
        if existing:
            raise ValueError(f"参数代码 {param_code} 已存在")

        param = SystemParam(
            param_name=param_name,
            param_code=param_code,
            param_value=param_value,
            status=status,
            description=description
        )
        self.db.add(param)
        self.db.commit()
        self.db.refresh(param)
        logger.info(f"创建系统参数: {param_code}")
        return param

    def get_params(self, skip: int = 0, limit: int = 100) -> List[SystemParam]:
        return self.db.query(SystemParam).offset(skip).limit(limit).all()

    def get_param(self, param_id: int) -> Optional[SystemParam]:
        return self.db.query(SystemParam).filter(SystemParam.id == param_id).first()

    def get_param_by_code(self, param_code: str) -> Optional[SystemParam]:
        return self.db.query(SystemParam).filter(SystemParam.param_code == param_code).first()

    def update_param(self, param_id: int, **kwargs) -> Optional[SystemParam]:
        param = self.get_param(param_id)
        if not param:
            return None

        if 'param_code' in kwargs and kwargs['param_code'] != param.param_code:
            existing = self.db.query(SystemParam).filter(
                SystemParam.param_code == kwargs['param_code'],
                SystemParam.id != param_id
            ).first()
            if existing:
                raise ValueError(f"参数代码 {kwargs['param_code']} 已存在")

        for key, value in kwargs.items():
            if value is not None and hasattr(param, key):
                setattr(param, key, value)

        self.db.commit()
        self.db.refresh(param)
        logger.info(f"更新系统参数: {param.param_code}")
        return param

    def delete_param(self, param_id: int) -> bool:
        param = self.get_param(param_id)
        if param:
            self.db.delete(param)
            self.db.commit()
            logger.info(f"删除系统参数: {param.param_code}")
            return True
        return False

    def search_params(self, keyword: str) -> List[SystemParam]:
        return self.db.query(SystemParam).filter(
            SystemParam.param_name.like(f"%{keyword}%") |
            SystemParam.param_code.like(f"%{keyword}%") |
            SystemParam.description.like(f"%{keyword}%")
        ).all()
