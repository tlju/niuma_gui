from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, model_validator
from typing import Optional
import os
import sys
from dotenv import load_dotenv
from core.utils import get_base_path

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///niuma.db"
    CRYPTO_KEY: str = ""  # 必须通过 .env 文件或环境变量配置，不允许使用默认值
    SESSION_TIMEOUT: int = 1800
    MAX_SESSIONS_PER_USER: int = 5
    LOG_LEVEL: str = "WARNING"

    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"
    DEFAULT_ADMIN_FULL_NAME: str = "系统管理员"

    BASTION_MAX_RETRIES: int = 3
    BASTION_RETRY_INTERVAL: int = 5
    BASTION_CONNECTION_TIMEOUT: int = 30
    BASTION_KEEPALIVE_INTERVAL: int = 30
    BASTION_MAX_AUTH_RETRIES: int = 5

    WORKFLOW_MAX_WORKERS: int = 4
    WORKFLOW_STATUS_CHECK_INTERVAL: float = 1.0

    SSH_SESSION_TIMEOUT: int = 30
    SSH_DEFAULT_PORT: int = 22

    LOG_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_BACKUP_COUNT: int = 5

    model_config = ConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode='after')
    def _resolve_database_url(self) -> 'Settings':
        if "sqlite" in self.DATABASE_URL:
            db_name = self.DATABASE_URL.split("///")[-1]
            db_path = os.path.join(get_base_path(), db_name)
            self.DATABASE_URL = f"sqlite:///{db_path}"
        return self

    @model_validator(mode='after')
    def _validate_crypto_key(self) -> 'Settings':
        """强制要求配置 CRYPTO_KEY，禁止使用空值或默认弱密钥"""
        if not self.CRYPTO_KEY:
            raise ValueError(
                "CRYPTO_KEY 未配置！请在 .env 文件中设置 CRYPTO_KEY 环境变量，"
                "或通过系统环境变量 CRYPTO_KEY 传入。"
                "可使用以下命令生成随机密钥: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        if len(self.CRYPTO_KEY.encode()) < 16:
            raise ValueError("CRYPTO_KEY 长度过短（至少16字节），请使用更长的随机密钥")
        return self

    @property
    def db_path(self) -> str:
        if "sqlite" in self.DATABASE_URL:
            db_name = self.DATABASE_URL.split("///")[-1]
            return os.path.join(get_base_path(), db_name)
        return "niuma.db"

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.DATABASE_URL


settings = Settings()
