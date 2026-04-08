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
