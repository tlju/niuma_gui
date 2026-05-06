#!/usr/bin/env python3
"""
数据库初始化脚本
创建所有表并添加初始管理员用户
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from core.database import engine, Base, SessionLocal
from core.logger import setup_logger, get_logger
from core.config import settings
from models.user import User, UserStatus
from services.crypto import hash_password

logger = get_logger(__name__)


def create_tables():
    """创建所有数据库表"""
    logger.info("正在创建数据库表...")
    from models import (
        User, ServerAsset, Script, AuditLog,
        DataDict, DataDictItem, SystemParam,
        Todo, Document, Workflow, WorkflowNode, WorkflowExecution, WorkflowNodeExecution
    )
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")


def create_admin_user(db: Session) -> bool:
    """创建默认管理员用户，使用 settings 中的统一配置"""
    # 统一使用 settings 中的配置，避免重复定义默认密码
    admin_username = settings.DEFAULT_ADMIN_USERNAME
    admin_password = settings.DEFAULT_ADMIN_PASSWORD
    admin_full_name = settings.DEFAULT_ADMIN_FULL_NAME

    existing = db.query(User).filter(User.username == admin_username).first()
    if existing:
        logger.info(f"管理员用户 '{admin_username}' 已存在")
        return False

    hashed_password = hash_password(admin_password)
    admin = User(
        username=admin_username,
        hashed_password=hashed_password,
        full_name=admin_full_name,
        status=UserStatus.ACTIVE,
        is_superuser=True
    )
    db.add(admin)
    db.commit()
    logger.info(f"管理员用户 '{admin_username}' 创建成功")
    # 不再打印明文密码到日志
    logger.info("请登录后立即修改默认密码！")
    return True


def init_database():
    """初始化数据库"""
    setup_logger()
    logger.info("开始初始化数据库...")

    create_tables()

    db = SessionLocal()
    try:
        created = create_admin_user(db)
        if created:
            logger.info(f"默认管理员账号: {settings.DEFAULT_ADMIN_USERNAME}")
            logger.info("请登录后立即修改默认密码！")
    finally:
        db.close()

    logger.info("数据库初始化完成")


if __name__ == "__main__":
    init_database()
