import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from core.config import settings
from core.logger import get_logger
from models.base import Base

logger = get_logger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.is_sqlite else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_FULL_NAME = "系统管理员"


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    """创建默认管理员用户"""
    from models.user import User, UserStatus
    from services.crypto import hash_password

    existing = db.query(User).filter(User.username == DEFAULT_ADMIN_USERNAME).first()
    if existing:
        logger.info(f"管理员用户 '{DEFAULT_ADMIN_USERNAME}' 已存在")
        return False

    hashed_password = hash_password(DEFAULT_ADMIN_PASSWORD)
    admin = User(
        username=DEFAULT_ADMIN_USERNAME,
        hashed_password=hashed_password,
        full_name=DEFAULT_ADMIN_FULL_NAME,
        status=UserStatus.ACTIVE,
        is_superuser=True
    )
    db.add(admin)
    db.commit()
    logger.info(f"管理员用户 '{DEFAULT_ADMIN_USERNAME}' 创建成功")
    return True


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
        db = SessionLocal()
        try:
            created = _create_admin_user(db)
            if created:
                logger.info("初始化完成！")
        finally:
            db.close()


def get_db_session() -> Session:
    """获取数据库会话（同步）"""
    return SessionLocal()
