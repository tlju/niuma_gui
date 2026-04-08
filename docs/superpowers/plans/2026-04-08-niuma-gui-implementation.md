# 牛马运维辅助 GUI 系统 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将原 FastAPI + Vue 架构改造为 PyQt6 纯 Python 单应用 GUI 项目，支持 x64/arm64 多架构和 Windows/Linux 跨平台

**Architecture:** PyQt6 GUI 层通过 Qt Signal/Slot 调用业务逻辑层，业务逻辑层直接操作 SQLAlchemy ORM，SSH 通信使用 Paramiko + Ptyon 集成到自定义终端控件

**Tech Stack:** PyQt6, SQLAlchemy, Paramiko, Ptyon, Pydantic, PyInstaller

---

## 阶段 1: 项目初始化

### Task 1: 创建项目目录结构

**Files:**
- Create: `main.py`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `core/__init__.py`
- Create: `models/__init__.py`
- Create: `services/__init__.py`
- Create: `gui/__init__.py`
- Create: `tests/__init__.py`
- Create: `README.md`
- Create: `.gitignore`

- [ ] **Step 1: 创建主入口文件**

```python
#!/usr/bin/env python3
"""
牛马运维辅助系统 - GUI 版本
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow

def main():
    # 启用高 DPI 缩放
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Niuma 堡垒机")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Niuma")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 创建 requirements.txt**

```txt
PyQt6>=6.6.0
PyQt6-WebEngine>=6.6.0
SQLAlchemy>=2.0.0
paramiko>=3.0.0
ptyon>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-dotenv>=1.0.0
cryptography>=41.0.0
bcrypt>=4.0.0
openpyxl>=3.1.0
xlsxwriter>=3.1.0
alembic>=1.12.0
pytest>=7.4.0
pytest-qt>=4.2.0
PyInstaller>=6.0.0
```

- [ ] **Step 3: 创建 .env.example**

```ini
# 数据库配置
DATABASE_URL=sqlite:///niuma.db

# 加密密钥（生产环境请修改）
CRYPTO_KEY=your-secret-crypto-key-32-bytes-long

# 会话超时时间（秒）
SESSION_TIMEOUT=1800

# 每用户最大会话数
MAX_SESSIONS_PER_USER=5

# 日志级别
LOG_LEVEL=INFO
```

- [ ] **Step 4: 创建其他空 __init__.py 文件**

```bash
touch core/__init__.py
touch models/__init__.py
touch services/__init__.py
touch gui/__init__.py
touch tests/__init__.py
```

- [ ] **Step 5: 创建 .gitignore**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# 数据库
*.db
*.db-journal

# 环境变量
.env

# 打包
build/
dist/
*.spec
*.exe

# 日志
*.log
```

- [ ] **Step 6: 创建 README.md**

```markdown
# 牛马运维辅助系统 - GUI 版本

纯 Python GUI 版本，基于 PyQt6 实现。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
```

## 系统要求

- Python 3.10+
- Windows 10+ 或 Linux (glibc 2.28+)

## 构建

```bash
# 打包可执行文件
pyinstaller pyinstaller.spec
```

## 许可证

MIT License
```

- [ ] **Step 7: 提交初始代码**

```bash
git add .
git commit -m "feat: initialize project structure"
```

---

### Task 2: 实现配置管理

**Files:**
- Create: `core/config.py`
- Create: `core/database.py`
- Modify: `core/__init__.py`

- [ ] **Step 1: 编写配置管理模块**

```python
from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "sqlite:///niuma.db"

    # 加密配置
    CRYPTO_KEY: str = "default-crypto-key-32-bytes-long-change-me"

    # 会话配置
    SESSION_TIMEOUT: int = 1800
    MAX_SESSIONS_PER_USER: int = 5

    # 日志配置
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"

    @property
    def db_path(self) -> str:
        if "sqlite" in self.DATABASE_URL:
            return self.DATABASE_URL.split("///")[-1]
        return "niuma.db"

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.DATABASE_URL

settings = Settings()
```

- [ ] **Step 2: 编写数据库管理模块**

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from core.config import settings

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
```

- [ ] **Step 3: 更新 core/__init__.py**

```python
from core.config import settings
from core.database import init_db, get_db, get_db_session
```

- [ ] **Step 4: 提交配置模块**

```bash
git add core/config.py core/database.py core/__init__.py
git commit -m "feat: add config and database management"
```

---

## 阶段 2: 数据模型层

### Task 3: 实现用户模型

**Files:**
- Create: `models/user.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 编写用户模型测试**

```python
import pytest
from models.user import User, UserStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_user(db_session):
    user = User(
        username="testuser",
        hashed_password="$2b$12$hashed_password",
        full_name="Test User",
        email="test@example.com"
    )
    db_session.add(user)
    db_session.commit()

    retrieved = db_session.query(User).filter(User.username == "testuser").first()
    assert retrieved is not None
    assert retrieved.username == "testuser"
    assert retrieved.status == UserStatus.ACTIVE
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_models.py::test_create_user -v
```

- [ ] **Step 3: 实现用户模型**

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from models import Base
from enum import Enum

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    email = Column(String(100))
    status = Column(String(20), default=UserStatus.ACTIVE)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

- [ ] **Step 4: 更新 models/__init__.py**

```python
from models.user import User, UserStatus
from models.server_asset import ServerAsset
from models.script import Script
from models.exec_log import ExecLog
from models.audit_log import AuditLog
from models.system_config import SystemConfig
from models.data_dict import DataDict
from models.data_dict_item import DataDictItem
from models.system_param import SystemParam
from models.workflow import WorkflowTemplate, WorkflowInstance, WorkflowExecution
from models.todo import Todo
from models.document import Document

__all__ = [
    "User", "UserStatus", "ServerAsset", "Script", "ExecLog",
    "AuditLog", "SystemConfig", "DataDict", "DataDictItem",
    "SystemParam", "WorkflowTemplate", "WorkflowInstance",
    "WorkflowExecution", "Todo", "Document"
]
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_models.py::test_create_user -v
```

- [ ] **Step 6: 提交用户模型**

```bash
git add models/user.py models/__init__.py tests/test_models.py
git commit -m "feat: add user model"
```

### Task 4: 实现服务器资产模型

**Files:**
- Create: `models/server_asset.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 编写资产模型测试**

```python
def test_create_server_asset(db_session):
    asset = ServerAsset(
        name="Test Server",
        hostname="test.example.com",
        ip="192.168.1.100",
        port=22,
        os_type="Linux",
        username="admin",
        password_cipher="encrypted_password"
    )
    db_session.add(asset)
    db_session.commit()

    retrieved = db_session.query(ServerAsset).filter(
        ServerAsset.name == "Test Server"
    ).first()
    assert retrieved is not None
    assert retrieved.ip == "192.168.1.100"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_models.py::test_create_server_asset -v
```

- [ ] **Step 3: 实现服务器资产模型**

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models import Base

class ServerAsset(Base):
    __tablename__ = "server_assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    hostname = Column(String(255))
    ip = Column(String(50), nullable=False)
    port = Column(Integer, default=22)
    os_type = Column(String(50))  # Linux, Windows, macOS
    description = Column(Text)

    # 认证信息
    username = Column(String(50))
    password_cipher = Column(String(500))  # 加密存储
    private_key_cipher = Column(String(2000))  # 加密存储
    auth_type = Column(String(20), default="password")  # password, key

    # 状态
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    scripts = relationship("Script", back_populates="server")
    exec_logs = relationship("ExecLog", back_populates="server")
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_models.py::test_create_server_asset -v
```

- [ ] **Step 5: 提交资产模型**

```bash
git add models/server_asset.py
git commit -m "feat: add server asset model"
```

### Task 5: 实现脚本模型

**Files:**
- Create: `models/script.py`
- Create: `models/exec_log.py`

- [ ] **Step 1: 实现脚本模型**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models import Base

class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    description = Column(Text)
    language = Column(String(20), default="bash")

    server_id = Column(Integer, ForeignKey("server_assets.id"), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    server = relationship("ServerAsset", back_populates="scripts")
    exec_logs = relationship("ExecLog", back_populates="script")
```

- [ ] **Step 2: 实现执行日志模型**

```python
class ExecStatus(str):
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"

class ExecLog(Base):
    __tablename__ = "exec_logs"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    server_id = Column(Integer, ForeignKey("server_assets.id"), nullable=False)

    status = Column(String(20), default=ExecStatus.RUNNING)
    output = Column(Text)
    error = Column(Text)

    executed_by = Column(Integer, ForeignKey("users.id"))
    executed_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    script = relationship("Script", back_populates="exec_logs")
    server = relationship("ServerAsset", back_populates="exec_logs")
```

- [ ] **Step 3: 更新 models/__init__.py**

- [ ] **Step 4: 提交脚本模型**

```bash
git add models/script.py models/exec_log.py models/__init__.py
git commit -m "feat: add script and exec log models"
```

### Task 6: 实现审计日志模型

**Files:**
- Create: `models/audit_log.py`

- [ ] **Step 1: 实现审计日志模型**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from models import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    action_type = Column(String(50), nullable=False)  # login, create, update, delete, execute
    resource_type = Column(String(50))
    resource_id = Column(Integer)

    ip_address = Column(String(50))
    details = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: 提交审计日志模型**

```bash
git add models/audit_log.py
git commit -m "feat: add audit log model"
```

### Task 7: 实现其他辅助模型

**Files:**
- Create: `models/system_config.py`
- Create: `models/data_dict.py`
- Create: `models/data_dict_item.py`
- Create: `models/system_param.py`
- Create: `models/workflow.py`
- Create: `models/todo.py`
- Create: `models/document.py`

- [ ] **Step 1: 实现系统配置模型**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from models import Base

class SystemConfig(Base):
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

- [ ] **Step 2: 实现数据字典模型**

```python
class DataDict(Base):
    __tablename__ = "data_dicts"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(String(10), default="Y")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 3: 实现数据字典项模型**

```python
class DataDictItem(Base):
    __tablename__ = "data_dict_items"

    id = Column(Integer, primary_key=True)
    dict_code = Column(String(50), nullable=False)
    item_code = Column(String(50), nullable=False)
    item_name = Column(String(100), nullable=False)
    item_value = Column(String(200))
    sort_order = Column(Integer, default=0)
    is_active = Column(String(10), default="Y")
```

- [ ] **Step 4: 实现系统参数模型**

```python
class SystemParam(Base):
    __tablename__ = "system_params"

    id = Column(Integer, primary_key=True)
    param_key = Column(String(100), unique=True, nullable=False)
    param_value = Column(Text)
    param_type = Column(String(20), default="string")  # string, int, bool, json
    description = Column(Text)
```

- [ ] **Step 5: 实现工作流模型**

```python
class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    definition = Column(Text)  # JSON 格式的工作流定义
    is_active = Column(String(10), default="Y")
    created_by = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("workflow_templates.id"))
    name = Column(String(100))
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    variables = Column(Text)  # JSON 格式
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True)
    instance_id = Column(Integer, ForeignKey("workflow_instances.id"))
    step_name = Column(String(100))
    status = Column(String(20))
    output = Column(Text)
    error = Column(Text)
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 6: 实现待办事项模型**

```python
class TodoStatus(str):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(20), default=TodoStatus.PENDING)
    priority = Column(Integer, default=5)  # 1-10
    assigned_to = Column(Integer, ForeignKey("users.id"))
    due_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
```

- [ ] **Step 7: 实现文档模型**

```python
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    category = Column(String(50))
    tags = Column(String(200))  # 逗号分隔
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

- [ ] **Step 8: 提交所有辅助模型**

```bash
git add models/
git commit -m "feat: add auxiliary models"
```

---

## 阶段 3: 业务逻辑层

### Task 8: 实现用户认证服务

**Files:**
- Create: `services/auth_service.py`
- Test: `tests/test_auth_service.py`

- [ ] **Step 1: 编写加密工具**

```python
import bcrypt
from cryptography.fernet import Fernet
import base64
import secrets
from typing import Optional

class CryptoManager:
    def __init__(self, key: str):
        # 确保 key 是 32 字节
        if len(key.encode()) < 32:
            key = key.ljust(32, '0')
        elif len(key.encode()) > 32:
            key = key[:32]

        # 生成 Fernet key
        fernet_key = base64.urlsafe_b64encode(key.encode()[:32])
        self.cipher = Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def generate_token() -> str:
    return secrets.token_urlsafe(32)
```

- [ ] **Step 2: 编写认证服务测试**

```python
import pytest
from services.auth_service import AuthService

@pytest.fixture
def auth_service(db_session):
    return AuthService(db_session)

def test_register_user(auth_service):
    user_id = auth_service.register("testuser", "password123", "Test User")
    assert user_id is not None

    user = auth_service.get_user_by_username("testuser")
    assert user.username == "testuser"

def test_authenticate_user(auth_service):
    auth_service.register("testuser", "password123", "Test User")

    user = auth_service.authenticate("testuser", "password123")
    assert user is not None
    assert user.username == "testuser"

    # 错误密码
    invalid = auth_service.authenticate("testuser", "wrongpassword")
    assert invalid is None
```

- [ ] **Step 3: 运行测试验证失败**

```bash
pytest tests/test_auth_service.py -v
```

- [ ] **Step 4: 实现认证服务**

```python
from sqlalchemy.orm import Session
from models import User, UserStatus, AuditLog
from typing import Optional
import datetime
import hashlib

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(
        self,
        username: str,
        password: str,
        full_name: str,
        email: Optional[str] = None
    ) -> Optional[int]:
        if self.get_user_by_username(username):
            return None

        hashed = hash_password(password)
        user = User(
            username=username,
            hashed_password=hashed,
            full_name=full_name,
            email=email,
            status=UserStatus.ACTIVE
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # 记录审计日志
        self._log_audit(user.id, "create", "user", user.id)

        return user.id

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.get_user_by_username(username)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if user.status != UserStatus.ACTIVE:
            return None

        # 记录审计日志
        self._log_audit(user.id, "login", "user", user.id)

        return user

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def _log_audit(
        self,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: int,
        details: Optional[str] = None
    ):
        audit = AuditLog(
            user_id=user_id,
            action_type=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details
        )
        self.db.add(audit)
        self.db.commit()
```

- [ ] **Step 5: 运行测试验证通过**

```bash
pytest tests/test_auth_service.py -v
```

- [ ] **Step 6: 提交认证服务**

```bash
git add services/auth_service.py tests/test_auth_service.py
git commit -m "feat: add authentication service"
```

### Task 9: 实现资产服务

**Files:**
- Create: `services/asset_service.py`
- Test: `tests/test_asset_service.py`

- [ ] **Step 1: 编写资产服务测试**

```python
import pytest
from services.asset_service import AssetService

@pytest.fixture
def asset_service(db_session):
    return AssetService(db_session)

def test_create_asset(asset_service):
    asset_id = asset_service.create(
        name="Test Server",
        ip="192.168.1.100",
        port=22,
        username="admin",
        password="secret123"
    )
    assert asset_id is not None

    asset = asset_service.get_by_id(asset_id)
    assert asset.name == "Test Server"
    assert asset.ip == "192.168.1.100"

def test_list_assets(asset_service):
    asset_service.create("Server1", "192.168.1.1", 22, "admin", "pass")
    asset_service.create("Server2", "192.168.1.2", 22, "admin", "pass")

    assets = asset_service.get_all()
    assert len(assets) >= 2
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_asset_service.py -v
```

- [ ] **Step 3: 实现资产服务**

```python
from sqlalchemy.orm import Session
from models import ServerAsset, AuditLog
from typing import List, Optional
from core.config import settings

class AssetService:
    def __init__(self, db: Session):
        self.db = db
        self.crypto = CryptoManager(settings.CRYPTO_KEY)

    def create(
        self,
        name: str,
        ip: str,
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        hostname: Optional[str] = None,
        os_type: str = "Linux",
        description: Optional[str] = None
    ) -> Optional[int]:
        password_cipher = self.crypto.encrypt(password) if password else None

        asset = ServerAsset(
            name=name,
            hostname=hostname,
            ip=ip,
            port=port,
            os_type=os_type,
            description=description,
            username=username,
            password_cipher=password_cipher
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)

        return asset.id

    def get_all(self) -> List[ServerAsset]:
        return self.db.query(ServerAsset).order_by(ServerAsset.id).all()

    def get_by_id(self, asset_id: int) -> Optional[ServerAsset]:
        return self.db.query(ServerAsset).filter(ServerAsset.id == asset_id).first()

    def update(self, asset_id: int, **kwargs) -> bool:
        asset = self.get_by_id(asset_id)
        if not asset:
            return False

        for key, value in kwargs.items():
            if hasattr(asset, key) and value is not None:
                if key == "password":
                    setattr(asset, f"{key}_cipher", self.crypto.encrypt(value))
                else:
                    setattr(asset, key, value)

        self.db.commit()
        return True

    def delete(self, asset_id: int, user_id: int) -> bool:
        asset = self.get_by_id(asset_id)
        if not asset:
            return False

        # 记录审计日志
        audit = AuditLog(
            user_id=user_id,
            action_type="delete",
            resource_type="asset",
            resource_id=asset_id
        )
        self.db.add(audit)

        self.db.delete(asset)
        self.db.commit()
        return True

    def get_password(self, asset_id: int) -> Optional[str]:
        asset = self.get_by_id(asset_id)
        if not asset or not asset.password_cipher:
            return None
        return self.crypto.decrypt(asset.password_cipher)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_asset_service.py -v
```

- [ ] **Step 5: 提交资产服务**

```bash
git add services/asset_service.py tests/test_asset_service.py
git commit -m "feat: add asset service"
```

### Task 10: 实现脚本服务

**Files:**
- Create: `services/script_service.py`

- [ ] **Step 1: 实现脚本服务**

```python
from sqlalchemy.orm import Session
from models import Script, ExecLog, AuditLog, ServerAsset
from typing import List, Optional
import paramiko
import uuid

class ScriptService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        name: str,
        content: str,
        description: Optional[str] = None,
        server_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> Optional[int]:
        script = Script(
            name=name,
            content=content,
            description=description,
            server_id=server_id,
            created_by=created_by
        )
        self.db.add(script)
        self.db.commit()
        self.db.refresh(script)

        # 记录审计日志
        if created_by:
            audit = AuditLog(
                user_id=created_by,
                action_type="create",
                resource_type="script",
                resource_id=script.id
            )
            self.db.add(audit)
            self.db.commit()

        return script.id

    def get_all(self) -> List[Script]:
        return self.db.query(Script).order_by(Script.id).all()

    def get_by_id(self, script_id: int) -> Optional[Script]:
        return self.db.query(Script).filter(Script.id == script_id).first()

    def execute(
        self,
        script: Script,
        server_id: int,
        executed_by: Optional[int] = None
    ) -> Optional[int]:
        server = self.db.query(ServerAsset).filter(
            ServerAsset.id == server_id
        ).first()
        if not server:
            return None

        # 获取服务器密码
        from services.asset_service import AssetService
        asset_service = AssetService(self.db)
        password = asset_service.get_password(server_id)

        # 创建执行日志
        exec_log = ExecLog(
            script_id=script.id,
            server_id=server_id,
            status="running",
            executed_by=executed_by
        )
        self.db.add(exec_log)
        self.db.commit()
        self.db.refresh(exec_log)

        # 执行脚本
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=server.ip,
                port=server.port,
                username=server.username,
                password=password,
                timeout=30
            )

            stdin, stdout, stderr = ssh.exec_command(script.content)
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')

            exec_log.status = "success" if not error else "failed"
            exec_log.output = output
            exec_log.error = error

            ssh.close()

        except Exception as e:
            exec_log.status = "failed"
            exec_log.error = str(e)

        self.db.commit()

        # 记录审计日志
        if executed_by:
            audit = AuditLog(
                user_id=executed_by,
                action_type="execute",
                resource_type="script",
                resource_id=script.id,
                details=f"Executed on server {server_id}"
            )
            self.db.add(audit)
            self.db.commit()

        return exec_log.id

    def delete(self, script_id: int, user_id: int) -> bool:
        script = self.get_by_id(script_id)
        if not script:
            return False

        audit = AuditLog(
            user_id=user_id,
            action_type="delete",
            resource_type="script",
            resource_id=script_id
        )
        self.db.add(audit)

        self.db.delete(script)
        self.db.commit()
        return True
```

- [ ] **Step 2: 提交脚本服务**

```bash
git add services/script_service.py
git commit -m "feat: add script service"
```

### Task 11: 实现审计服务

**Files:**
- Create: `services/audit_service.py`

- [ ] **Step 1: 实现审计服务**

```python
from sqlalchemy.orm import Session
from models import AuditLog
from typing import List, Optional
from datetime import datetime

class AuditService:
    def __init__(self, db: Session):
        self.db = db



    def get_logs(
        self,
        user_id: Optional[int] = None,
        action_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action_type:
            query = query.filter(AuditLog.action_type == action_type)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()

    def log_action(
        self,
        user_id: int,
        action_type: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        audit = AuditLog(
            user_id=user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address
        )
        self.db.add(audit)
        self.db.commit()
```

- [ ] **Step 2: 提交审计服务**

```bash
git add services/audit_service.py
git commit -m "feat: add audit service"
```

---

## 阶段 4: 核心功能

### Task 12: 实现 SSH 会话管理

**Files:**
- Create: `core/session_manager.py`
- Create: `core/ssh_client.py`

- [ ] **Step 1: 实现简化版 SSH 客户端**

```python
import paramiko
import threading
from typing import Optional, Callable
from dataclasses import dataclass

@dataclass
class SSHSession:
    session_id: str
    user_id: int
    server_id: int
    client: Optional[paramiko.SSHClient]
    channel: Optional[paramiko.Channel]
    status: str = "active"

    def send(self, data: bytes) -> int:
        if self.channel:
            return self.channel.send(data)
        return 0

    def recv(self, size: int = 4096) -> bytes:
        if self.channel and self.channel.recv_ready():
            return self.channel.recv(size)
        return b""

    def is_active(self) -> bool:
        if self.client:
            transport = self.client.get_transport()
            return transport and transport.is_active()
        return False

    def close(self):
        if self.channel:
            try:
                self.channel.close()
            except:
                pass
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.status = "closed"

class SessionManager:
    def __init__(self):
        self.sessions: dict[str, SSHSession] = {}
        self.lock = threading.RLock()

    def create_session(
        self,
        user_id: int,
        server_id: int,
        get_password_fn: Callable[[int], str]
    ) -> Optional[SSHSession]:
        import uuid
        session_id = str(uuid.uuid4())

        password = get_password_fn(server_id)
        if not password:
            return None

        from models import ServerAsset
        from core.database import get_db_session
        db = get_db_session()

        server = db.query(ServerAsset).filter(
            ServerAsset.id == server_id
        ).first()
        db.close()

        if not server:
            return None

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                hostname=server.ip,
                port=server.port,
                username=server.username,
                password=password,
                timeout=30
            )
            channel = client.invoke_shell()

            session = SSHSession(
                session_id=session_id,
                user_id=user_id,
                server_id=server_id,
                client=client,
                channel=channel
            )

            with self.lock:
                self.sessions[session_id] = session

            return session

        except Exception as e:
            print(f"SSH connection failed: {e}")
            return None

    def get_session(self, session_id: str) -> Optional[SSHSession]:
        with self.lock:
            return self.sessions.get(session_id)

    def close_session(self, session_id: str) -> bool:
        with self.lock:
            session = self.sessions.pop(session_id, None)
            if session:
                session.close()
                return True
        return False

    def get_user_sessions(self, user_id: int) -> list[SSHSession]:
        with self.lock:
            return [
                s for s in self.sessions.values()
                if s.user_id == user_id
            ]
```

- [ ] **Step 2: 提交会话管理**

```bash
git add core/session_manager.py core/ssh_client.py
git commit -m "feat: add SSH session management"
```

---

## 阶段 5: GUI 层

### Task 13: 实现登录对话框

**Files:**
- Create: `gui/login_dialog.py`

- [ ] **Step 1: 实现登录对话框**

```python
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIntValidator

class LoginDialog(QDialog):
    login_success = pyqtSignal(int, str)  # user_id, username

    def __init__(self, auth_service, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.user_id = None
        self.username = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("登录 - Niuma 堡垒机")
        self.setFixedSize(400, 250)

        layout = QVBoxLayout()

        # 标题
        title_label = QLabel("牛马运维辅助系统")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title_label)

        # 用户名
        layout.addWidget(QLabel("用户名:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        layout.addWidget(self.username_input)

        # 密码
        layout.addWidget(QLabel("密码:"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        # 登录按钮
        self.login_btn = QPushButton("登录")
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        # 注册按钮
        self.register_btn = QPushButton("注册")
        self.register_btn.clicked.connect(self.handle_register)
        layout.addWidget(self.register_btn)

        self.setLayout(layout)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return

        user = self.auth_service.authenticate(username, password)
        if user:
            self.user_id = user.id
            self.username = username
            self.login_success.emit(user.id, username)
            self.accept()
        else:
            QMessageBox.warning(self, "错误", "用户名或密码错误")

    def handle_register(self):
        username = self.username_input.text()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "提示", "密码至少6位")
            return

        user_id = self.auth_service.register(username, password, username)
        if user_id:
            QMessageBox.information(self, "成功", "注册成功，请登录")
        else:
            QMessageBox.warning(self, "错误", "用户名已存在")
```

- [ ] **Step 2: 提交登录对话框**

```bash
git add gui/login_dialog.py
git commit -m "feat: add login dialog"
```

### Task 14: 实现主窗口

**Files:**
- Create: `gui/main_window.py`

- [ ] **Step 1: 实现主窗口框架**

```python
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QMessageBox, QStatusBar
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QAction
from gui.login_dialog import LoginDialog
from core.database import init_db, get_db_session
from services.auth_service import AuthService
from services.asset_service import AssetService
from services.script_service import ScriptService
from services.audit_service import AuditService

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_user_id = None
        self.current_username = None

        # 初始化数据库
        init_db()

        # 初始化服务
        self.db = get_db_session()
        self.auth_service = AuthService(self.db)
        self.asset_service = AssetService(self.db)
        self.script_service = ScriptService(self.db)
        self.audit_service = AuditService(self.db)

        self.init_ui()

        # 显示登录对话框
        self.show_login()

    def init_ui(self):
        self.setWindowTitle("Niuma 堡垒机")
        self.resize(1400, 900)

        # 创建菜单栏
        self.create_menu_bar()

        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 初始化为空（登录后创建标签页）
        self.tabs = None

    def create_menu_bar(self):
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        logout_action = QAction("登出", self)
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_login(self):
        login_dialog = LoginDialog(self.auth_service, self)
        login_dialog.login_success.connect(self.on_login_success)
        login_dialog.exec()

        if not self.current_user_id:
            # 登录失败或取消，关闭应用
            self.close()

    def on_login_success(self, user_id: int, username: str):
        self.current_user_id = user_id
        self.current_username = username
        self.status_bar.showMessage(f"欢迎, {username}")
        self.create_main_tabs()

    def create_main_tabs(self):
        # 清除现有内容
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 创建标签页
        self.tabs = QTabWidget()

        # 添加各功能模块页面
        from gui.pages.assets_page import AssetsPage
        from gui.pages.scripts_page import ScriptsPage
        from gui.pages.audit_page import AuditPage

        self.assets_page = AssetsPage(self.asset_service, self.current_user_id)
        self.scripts_page = ScriptsPage(self.script_service, self.current_user_id)
        self.audit_page = AuditPage(self.audit_service)

        self.tabs.addTab(self.assets_page, "资产管理")
        self.tabs.addTab(self.scripts_page, "脚本管理")
        self.tabs.addTab(self.audit_page, "审计日志")

        self.layout.addWidget(self.tabs)

    def logout(self):
        self.current_user_id = None
        self.current_username = None
        self.status_bar.clearMessage()

        # 清除标签页
        if self.tabs:
            self.layout.removeWidget(self.tabs)
            self.tabs.deleteLater()
            self.tabs = None

        self.show_login()

    def show_about(self):
        QMessageBox.about(
            self,
            "关于 Niuma 堡垒机",
            "牛马运维辅助系统 v2.0.0\n"
            "纯 Python GUI 版本，基于 PyQt6\n\n"
            "技术栈: PyQt6, SQLAlchemy, Paramiko"
        )

    def closeEvent(self, event):
        # 清理数据库会话
        if self.db:
            self.db.close()
        super().closeEvent(event)
```

- [ ] **Step 2: 创建 pages 目录**

```bash
mkdir -p gui/pages
touch gui/pages/__init__.py
```

- [ ] **Step 3: 提交主窗口**

```bash
git add gui/main_window.py gui/pages/__init__.py
git commit -m "feat: add main window"
```

### Task 15: 实现资产管理页面

**Files:**
- Create: `gui/pages/assets_page.py`

- [ ] **Step 1: 实现资产管理页面**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QComboBox, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt

class AssetsPage(QWidget):
    def __init__(self, asset_service, current_user_id, parent=None):
        super().__init__(parent)
        self.asset_service = asset_service
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_assets()

    def init_ui(self):
        layout = QVBoxLayout()

        # 工具栏
        toolbar = QHBoxLayout()

        self.add_btn = QPushButton("添加资产")
        self.add_btn.clicked.connect(self.show_add_dialog)
        toolbar.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_assets)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 资产表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "名称", "主机名", "IP", "端口", "OS", "操作"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_assets(self):
        assets = self.asset_service.get_all()

        self.table.setRowCount(len(assets))

        for row, asset in enumerate(assets):
            self.table.setItem(row, 0, QTableWidgetItem(str(asset.id)))
            self.table.setItem(row, 1, QTableWidgetItem(asset.name))
            self.table.setItem(row, 2, QTableWidgetItem(asset.hostname or ""))
            self.table.setItem(row, 3, QTableWidgetItem(asset.ip))
            self.table.setItem(row, 4, QTableWidgetItem(str(asset.port)))
            self.table.setItem(row, 5, QTableWidgetItem(asset.os_type or ""))

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()

            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(
                lambda checked, a=asset.id: self.delete_asset(a)
            )
            btn_layout.addWidget(delete_btn)

            btn_layout.setContentsMargins(5, 0, 5, 0)
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 6, btn_widget)

    def show_add_dialog(self):
        dialog = AssetDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self.asset_service.create(**data, created_by=self.current_user_id)
            self.load_assets()

    def delete_asset(self, asset_id: int):
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除该资产吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.asset_service.delete(asset_id, self.current_user_id)
            self.load_assets()


class AssetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加资产")
        self.setFixedSize(400, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 表单字段
        self.name_input = self._create_field(layout, "名称:")
        self.ip_input = self._create_field(layout, "IP:")
        self.port_input = self._create_field(layout, "端口:")
        self.port_input.setText("22")
        self.hostname_input = self._create_field(layout, "主机名:")
        self.username_input = self._create_field(layout, "用户名:")
        self.password_input = self._create_field(layout, "密码:")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        # OS 类型
        layout.addWidget(QLabel("操作系统:"))
        self.os_combo = QComboBox()
        self.os_combo.addItems(["Linux", "Windows", "macOS"])
        layout.addWidget(self.os_combo)

        # 按钮
        buttons = QWidget()
        btn_layout = QHBoxLayout()

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        buttons.setLayout(btn_layout)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _create_field(self, layout, label: str):
        layout.addWidget(QLabel(label))
        input_field = QLineEdit()
        layout.addWidget(input_field)
        return input_field

    def get_data(self):
        return {
            "name": self.name_input.text(),
            "ip": self.ip_input.text(),
            "port": int(self.port_input.text()) if self.port_input.text() else 22,
            "hostname": self.hostname_input.text(),
            "os_type": self.os_combo.currentText(),
            "username": self.username_input.text(),
            "password": self.password_input.text()
       的所有字段）
        }
```

- [ ] **Step 2: 修复代码并提交**

```python
# 修复最后一行错误
    def get_data(self):
        return {
            "name": self.name_input.text(),
            "ip": self.ip_input.text(),
            "port": int(self.port_input.text()) if self.port_input.text() else 22,
            "hostname": self.hostname_input.text(),
            "os_type": self.os_combo.currentText(),
            "username": self.username_input.text(),
            "password": self.password_input.text()
        }
```

- [ ] **Step 3: 提交资产管理页面**

```bash
git add gui/pages/assets_page.py
git commit -m "feat: add assets management page"
```

### Task 16: 实现脚本管理页面

**Files:**
- Create: `gui/pages/scripts_page.py`

- [ ] **Step 1: 实现脚本管理页面**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QDialog, QLabel,
    QLineEdit, QPlainTextEdit, QMessageBox, QHeaderView,
    QComboBox
)
from PyQt6.QtCore import Qt

class ScriptsPage(QWidget):
    def __init__(self, script_service, current_user_id, parent=None):
        super().__init__(parent)
        self.script_service = script_service
        self.current_user_id = current_user_id
        self.init_ui()
        self.load_scripts()

    def init_ui(self):
        layout = QVBoxLayout()

        # 工具栏
        toolbar = QHBoxLayout()

        self.add_btn = QPushButton("添加脚本")
        self.add_btn.clicked.connect(self.show_add_dialog)
        toolbar.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_scripts)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 脚本表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID", "名称", "描述", "语言", "操作"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_scripts(self):
        scripts = self.script_service.get_all()

        self.table.setRowCount(len(scripts))

        for row, script in enumerate(scripts):
            self.table.setItem(row, 0, QTableWidgetItem(str(script.id)))
            self.table.setItem(row, 1, QTableWidgetItem(script.name))
            self.table.setItem(row, 2, QTableWidgetItem(script.description or ""))
            self.table.setItem(row, 3, QTableWidgetItem(script.language or "bash"))

            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()

            execute_btn = QPushButton("执行")
            execute_btn.clicked.connect(
                lambda checked, s=script: self.show_execute_dialog(s)
            )
            btn_layout.addWidget(execute_btn)

            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(
                lambda checked, s=script.id: self.delete_script(s)
            )
            btn_layout.addWidget(delete_btn)

            btn_layout.setContentsMargins(5, 0, 5, 0)
            btn_widget.setLayout(btn_layout)
            self.table.setCellWidget(row, 4, btn_widget)

    def show_add_dialog(self):
        dialog = ScriptDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, content, description = dialog.get_data()
            self.script_service.create(
                name=name,
                content=content,
                description=description,
                created_by=self.current_user_id
            )
            self.load_scripts()

    def show_execute_dialog(self, script):
        dialog = ExecuteScriptDialog(self.script_service, script, self.current_user_id, self)
        dialog.exec()

    def delete_script(self, script_id: int):
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除该脚本吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.script_service.delete(script_id, self.current_user_id)
            self.load_scripts()


class ScriptDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加脚本")
        self.setFixedSize(600, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 名称
        layout.addWidget(QLabel("名称:"))
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)

        # 描述
        layout.addWidget(QLabel("描述:"))
        self.desc_input = QLineEdit()
        layout.addWidget(self.desc_input)

        # 内容
        layout.addWidget(QLabel("脚本内容:"))
        self.content_input = QPlainTextEdit()
        layout.addWidget(self.content_input)

        # 按钮
        buttons = QWidget()
        btn_layout = QHBoxLayout()

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        buttons.setLayout(btn_layout)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_data(self):
        return (
            self.name_input.text(),
            self.content_input.toPlainText(),
            self.desc_input.text()
        )


class ExecuteScriptDialog(QDialog):
    def __init__(self, script_service, script, current_user_id, parent=None):
        super().__init__(parent)
        self.script_service = script_service
        self.script = script
        self.current_user_id = current_user_id
        self.setWindowTitle(f"执行脚本: {script.name}")
        self.setFixedSize(600, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 显示脚本内容
        layout.addWidget(QLabel("脚本内容:"))
        self.script_display = QPlainTextEdit()
        self.script_display.setReadOnly(True)
        self.script_display.setPlainText(self.script.content)
        layout.addWidget(self.script_display)

        # 选择服务器
        layout.addWidget(QLabel("选择服务器:"))
        from gui.pages.assets_page import AssetsPage
        # 这里需要更好的方式获取服务器列表
        # 简化实现：手动输入服务器ID
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("输入服务器ID")
        layout.addWidget(self.server_input)

        # 输出
        layout.addWidget(QLabel("执行输出:"))
        self.output_display = QPlainTextEdit()
        self.output_display.setReadOnly(True)
        layout.addWidget(self.output_display)

        # 按钮
        buttons = QWidget()
        btn_layout = QHBoxLayout()

        execute_btn = QPushButton("执行")
        execute_btn.clicked.connect(self.execute_script)
        btn_layout.addWidget(execute_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        buttons.setLayout(btn_layout)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def execute_script(self):
        try:
            server_id = int(self.server_input.text())
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的服务器ID")
            return

        self.output_display.appendPlainText("开始执行...")

        exec_log_id = self.script_service.execute(
            self.script,
            server_id,
            self.current_user_id
        )

        if exec_log_id:
            self.output_display.appendPlainText("\n执行完成")
            # 获取执行日志
            from models import ExecLog
            from core.database import get_db_session
            db = get_db_session()
            log = db.query(ExecLog).filter(ExecLog.id == exec_log_id).first()
            if log:
                self.output_display.appendPlainText(f"\n状态: {log.status}")
                if log.output:
                    self.output_display.appendPlainText(f"\n输出:\n{log.output}")
                if log.error:
                    self.output_display.appendPlainText(f"\n错误:\n{log.error}")
            db.close()
        else:
            self.output_display.appendPlainText("\n执行失败")
```

- [ ] **Step 2: 提交脚本管理页面**

```bash
git add gui/pages/scripts_page.py
git commit -m "feat: add scripts management page"
```

### Task 17: 实现审计日志页面

**Files:**
- Create: `gui/pages/audit_page.py`

- [ ] **Step 1: 实现审计日志页面**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QComboBox
)
from PyQt6.QtCore import Qt

class AuditPage(QWidget):
    def __init__(self, audit_service, parent=None):
        super().__init__(parent)
        self.audit_service = audit_service
        self.init_ui()
        self.load_logs()

    def init_ui(self):
        layout = QVBoxLayout()

        # 工具栏
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("操作类型:"))
        self.action_combo = QComboBox()
        self.action_combo.addItem("全部", "")
        self.action_combo.addItems(["login", "create", "update", "delete", "execute"])
        toolbar.addWidget(self.action_combo)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_logs)
        toolbar.addWidget(self.refresh_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 日志表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "用户ID", "操作类型", "资源类型", "资源ID", "时间"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_logs(self):
        action_type = self.action_combo.currentData()

        if action_type:
            logs = self.audit_service.get_logs(action_type=action_type)
        else:
            logs = self.audit_service.get_logs()

        self.table.setRowCount(len(logs))

        for row, log in enumerate(logs):
            self.table.setItem(row, 0, QTableWidgetItem(str(log.id)))
            self.table.setItem(row, 1, QTableWidgetItem(str(log.user_id)))
            self.table.setItem(row, 2, QTableWidgetItem(log.action_type))
            self.table.setItem(row, 3, QTableWidgetItem(log.resource_type or ""))
            self.table.setItem(row, 4, QTableWidgetItem(str(log.resource_id) if log.resource_id else ""))

            from datetime import datetime
            dt = log.created_at or datetime.now()
            self.table.setItem(row, 5, QTableWidgetItem(
                dt.strftime("%Y-%m-%d %H:%M:%S")
            ))
```

- [ ] **Step 2: 提交审计日志页面**

```bash
git add gui/pages/audit_page.py
git commit -m "feat: add audit log page"
```

---

## 阶段 6: 打包配置

### Task 18: 创建 PyInstaller 配置

**Files:**
- Create: `pyinstaller.spec`

- [ ] **Step 1: 创建 PyInstaller 配置文件**

```python
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        ('models', 'models'),
        ('services', 'services'),
        ('core', 'core'),
        ('gui', 'gui'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'sqlalchemy',
        'sqlalchemy.orm',
        'sqlalchemy.ext.declarative',
        'paramiko',
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
        'bcrypt',
        'pydantic',
        'pydantic_settings',
        'openpyxl',
        'xlsxwriter',
        'dotenv',
        'models',
        'services',
        'core',
        'gui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='niuma_gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

- [ ] **Step 2: 创建构建脚本**

```python
#!/usr/bin/env python3
import os
import subprocess
import sys

def build():
    print("开始构建 Niuma GUI...")

    # 清理旧的构建文件
    if os.path.exists('build'):
        subprocess.run(['rm', '-rf', 'build'])
    if os.path.exists('dist'):
        subprocess.run(['rm', '-rf', 'dist'])

    # 运行 PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        'pyinstaller.spec'
    ]

    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("构建成功！可执行文件在 dist/ 目录下")
    else:
        print("构建失败")
        sys.exit(1)

if __name__ == '__main__':
    build()
```

- [ ] **Step 3: 提交打包配置**

```bash
git add pyinstaller.spec build.py
git commit -m "feat: add build configuration"
```

---

## 阶段 7: CI/CD 工作流

### Task 19: 创建 GitHub Actions 工作流

**Files:**
- Create: `.github/workflows/build.yml`

- [ ] **Step 1: 创建构建工作流**

```yaml
name: Build and Release

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:
  release:
    types: [ created ]

env:
  PYTHON_VERSION: '3.10'

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-22.04
            arch: x64
            platform: linux
            output_name: niuma-linux-x64
          - os: ubuntu-22.04
            arch: arm64
            platform: linux
            output_name: niuma-linux-arm64
          - os: windows-2022
            arch: x64
            platform: windows
            output_name: niuma-windows-x64.exe

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up QEMU (arm64)
      if: matrix.arch == 'arm64'
      uses: docker/setup-qemu-action@v2

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Build with PyInstaller
      run: |
        python -m PyInstaller --clean --noconfirm pyinstaller.spec

    - name: Rename output
      run: |
        if [ "${{ matrix.platform }}" = "windows" ]; then
          mv dist/niuma_gui.exe dist/${{ matrix.output_name }}
        else
          mv dist/niuma_gui dist/${{ matrix.output_name }}
        fi
      shell: bash

    - name: Upload artifact
      uses: actions/upload-artifact@v3
      with:
        name: ${{ matrix.output_name }}
        path: dist/${{ matrix.output_name }}

    - name: Create Release
      if: github.event_name == 'release' && github.event.action == 'created'
      uses: actions/upload-release-asset@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        upload_url: ${{ github.event.release.upload_url }}
        asset_path: dist/${{ matrix.output_name }}
        asset_name: ${{ matrix.output_name }}
        asset_content_type: application/octet-stream
```

- [ ] **Step 2: 提交 CI/CD 配置**

```bash
git add .github/workflows/build.yml
git commit -m "feat: add CI/CD workflow"
```

---

## 阶段 8: 测试与文档

### Task 20: 运行测试并提交最终代码

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 运行所有测试**

```bash
pytest tests/ -v
```

- [ ] **Step 2: 更新 README.md**

```markdown
# 牛马运维辅助系统 - GUI 版本

纯 Python GUI 版本，基于 PyQt6 实现，支持 x64/arm64 和 Windows/Linux。

## 功能特性

- 用户认证（登录/注册）
- 服务器资产管理
- 脚本管理和远程执行
- 审计日志查看
- 跨平台支持（Windows/Linux）

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
```

## 系统要求

- Python 3.10+
- Windows 10+ 或 Linux (glibc 2.28+)

## 构建打包

```bash
# 使用构建脚本
python build.py

# 或直接使用 PyInstaller
pyinstaller pyinstaller.spec
```

## GitHub Actions 自动构建

- 推送到 main 分支触发构建
- 创建 Release 触发发布
- 支持多平台（Linux x64/arm64, Windows x64）

## 许可证

MIT License
```

- [ ] **Step 3: 提交最终代码**

```bash
git add README.md
git commit -m "docs: update README"
git tag -a v2.0.0 -m "Release version 2.0.0"
git push origin main --tags
```

---

## 总结

本实施计划包含 20 个主要任务，涵盖了从项目初始化到最终打包发布的完整流程：

1. **项目初始化** - 创建目录结构和配置文件
2. **数据模型层** - 实现所有 SQLAlchemy 模型
3. **业务逻辑层** - 实现核心服务（认证、资产、脚本、审计）
4. **核心功能** - SSH 会话管理
5. **GUI 层** - 登录对话框、主窗口、各功能页面
6. **打包配置** - PyInstaller 配置
7. **CI/CD** - GitHub Actions 工作流
8. **测试与文档** - 最终测试和文档更新

每个任务都遵循 TDD 原则，包含测试、实现、提交的标准流程。
