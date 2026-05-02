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
    CRYPTO_KEY: str = "default-crypto-key-32-bytes-long-change-me"
    SESSION_TIMEOUT: int = 1800
    MAX_SESSIONS_PER_USER: int = 5
    LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode='after')
    def _resolve_database_url(self) -> 'Settings':
        if "sqlite" in self.DATABASE_URL:
            db_name = self.DATABASE_URL.split("///")[-1]
            db_path = os.path.join(get_base_path(), db_name)
            self.DATABASE_URL = f"sqlite:///{db_path}"
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
