from __future__ import annotations

from models.system_param import SystemParam
from typing import List, Optional
from core.logger import get_logger
from core.utils import escape_like_wildcards
from core.database import get_db

logger = get_logger(__name__)


class ParamService:
    UPDATABLE_FIELDS = frozenset({"param_name", "param_code", "param_value", "status", "description"})

    def create_param(self, param_name: str, param_code: str, param_value: str,
                     status: int = 1, description: str = None) -> SystemParam:
        with get_db() as db:
            existing = db.query(SystemParam).filter(
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
            db.add(param)
            db.commit()
            db.refresh(param)
            logger.info(f"创建系统参数: {param_code}")
            return param

    def get_params(self, skip: int = 0, limit: int = 100) -> List[SystemParam]:
        with get_db() as db:
            return db.query(SystemParam).offset(skip).limit(limit).all()

    def get_param(self, param_id: int) -> Optional[SystemParam]:
        with get_db() as db:
            return db.query(SystemParam).filter(SystemParam.id == param_id).first()

    def get_param_by_code(self, param_code: str) -> Optional[SystemParam]:
        with get_db() as db:
            return db.query(SystemParam).filter(SystemParam.param_code == param_code).first()

    def update_param(self, param_id: int, **kwargs) -> Optional[SystemParam]:
        with get_db() as db:
            param = db.query(SystemParam).filter(SystemParam.id == param_id).first()
            if not param:
                return None

            if 'param_code' in kwargs and kwargs['param_code'] != param.param_code:
                existing = db.query(SystemParam).filter(
                    SystemParam.param_code == kwargs['param_code'],
                    SystemParam.id != param_id
                ).first()
                if existing:
                    raise ValueError(f"参数代码 {kwargs['param_code']} 已存在")

            for key, value in kwargs.items():
                if key in self.UPDATABLE_FIELDS and value is not None:
                    setattr(param, key, value)

            db.commit()
            db.refresh(param)
            logger.info(f"更新系统参数: {param.param_code}")
            return param

    def delete_param(self, param_id: int) -> bool:
        with get_db() as db:
            param = db.query(SystemParam).filter(SystemParam.id == param_id).first()
            if param:
                db.delete(param)
                db.commit()
                logger.info(f"删除系统参数: {param.param_code}")
                return True
            return False

    def search_params(self, keyword: str) -> List[SystemParam]:
        escaped = escape_like_wildcards(keyword)
        with get_db() as db:
            return db.query(SystemParam).filter(
                SystemParam.param_name.like(f"%{escaped}%", escape='\\') |
                SystemParam.param_code.like(f"%{escaped}%", escape='\\') |
                SystemParam.description.like(f"%{escaped}%", escape='\\')
            ).all()
