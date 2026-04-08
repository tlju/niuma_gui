from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.is_sqlite else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库表"""
    from models import (
        User, ServerAsset, Script, ExecLog, AuditLog,
        SystemConfig, DataDict, DataDictItem, SystemParam,
        WorkflowTemplate, WorkflowInstance, WorkflowExecution,
        Todo, Document
    )
    Base.metadata.create_all(bind=engine)

def get_db_session() -> Session:
    """获取数据库会话（同步）"""
    return SessionLocal()
