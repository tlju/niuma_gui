from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
import os
import sys
from dotenv import load_dotenv
from core.logger import get_logger

logger = get_logger(__name__)
load_dotenv()

def _get_base_path():
    """
    获取程序的基础路径
    在编译后的程序中使用可执行文件所在目录，否则使用脚本所在目录
    支持 PyInstaller (sys.frozen) 和 Nuitka (__compiled__)
    """
    if getattr(sys, 'frozen', False) or globals().get('__compiled__'):
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        return os.path.dirname(os.path.dirname(__file__))

class Settings(BaseSettings):
    # 数据库配置
    _DATABASE_URL: str = "sqlite:///niuma.db"

    # 加密配置
    CRYPTO_KEY: str = "default-crypto-key-32-bytes-long-change-me"

    # 会话配置
    SESSION_TIMEOUT: int = 1800
    MAX_SESSIONS_PER_USER: int = 5

    # 日志配置
    LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(env_file=".env", extra="ignore")

    @property
    def db_path(self) -> str:
        if "sqlite" in self.DATABASE_URL:
            db_name = self.DATABASE_URL.split("///")[-1]
            return os.path.join(_get_base_path(), db_name)
        return "niuma.db"

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.DATABASE_URL

    @property
    def DATABASE_URL(self) -> str:
        if "sqlite" in self._DATABASE_URL:
            db_name = self._DATABASE_URL.split("///")[-1]
            db_path = os.path.join(_get_base_path(), db_name)
            return f"sqlite:///{db_path}"
        return self._DATABASE_URL

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._DATABASE_URL = kwargs.get('DATABASE_URL', "sqlite:///niuma.db")

settings = Settings()
