from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from core.config import settings
from core.logger import get_logger
from core.utils import get_local_now, get_base_path
from models.base import Base

logger = get_logger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.is_sqlite else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    """获取数据库会话的上下文管理器，自动管理生命周期，线程安全"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# get_thread_db 已合并到 get_db，保留别名以兼容现有调用
get_thread_db = get_db


def _create_tables():
    """创建所有数据库表"""
    logger.info("正在创建数据库表...")
    from models import (
        User, ServerAsset, Script, AuditLog,
        DataDict, DataDictItem, SystemParam,
        Todo, Document, Workflow, WorkflowNode, WorkflowExecution, WorkflowNodeExecution
    )
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建完成")


def _create_admin_user(db: Session) -> bool:
    from models.user import User, UserStatus
    from services.crypto import hash_password

    existing = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()
    if existing:
        logger.info(f"管理员用户 '{settings.DEFAULT_ADMIN_USERNAME}' 已存在")
        return False

    hashed_password = hash_password(settings.DEFAULT_ADMIN_PASSWORD)
    admin = User(
        username=settings.DEFAULT_ADMIN_USERNAME,
        hashed_password=hashed_password,
        full_name=settings.DEFAULT_ADMIN_FULL_NAME,
        status=UserStatus.ACTIVE,
        is_superuser=True,
        created_at=get_local_now()
    )
    db.add(admin)
    db.commit()
    # 不再打印明文密码到日志
    logger.info(f"管理员用户 '{settings.DEFAULT_ADMIN_USERNAME}' 创建成功，请登录后立即修改默认密码")
    return True


def _import_input_sql():
    """如果存在 input.sql 则导入数据"""
    base_path = get_base_path()
    input_sql_path = os.path.join(base_path, "input.sql")
    
    if not os.path.exists(input_sql_path):
        logger.info("未找到 input.sql，跳过数据导入")
        return False
    
    db_path = settings.db_path
    
    logger.info("正在导入 input.sql 到数据库...")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        with open(input_sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        cursor.executescript(sql_content)
        conn.commit()
        conn.close()
        
        logger.info("input.sql 导入成功")
        return True
    except sqlite3.Error as e:
        logger.error(f"导入 input.sql 失败: {e}")
        return False
    except Exception as e:
        logger.error(f"导入 input.sql 时发生错误: {e}")
        return False


def init_db():
    """初始化数据库表"""
    db_exists = False
    if settings.is_sqlite:
        db_path = settings.db_path
        db_exists = os.path.exists(db_path)
        if not db_exists:
            logger.info(f"数据库文件不存在，将自动创建: {db_path}")

    _create_tables()

    if not db_exists:
        with get_db() as db:
            created = _create_admin_user(db)
            if created:
                logger.info("初始化完成！")
        
        _import_input_sql()


def get_db_session() -> Session:
    """获取数据库会话（同步），建议优先使用 get_db() 上下文管理器模式"""
    import warnings
    warnings.warn(
        "get_db_session() 已弃用，请使用 get_db() 上下文管理器以自动管理会话生命周期",
        DeprecationWarning,
        stacklevel=2
    )
    return SessionLocal()
