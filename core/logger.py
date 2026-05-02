"""
日志配置模块
提供统一的日志记录功能
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
from core.utils import get_base_path

_logger_initialized = False


def setup_logger(log_level: int = logging.INFO) -> logging.Logger:
    """
    配置日志系统

    Args:
        log_level: 日志级别，默认为INFO
    """
    global _logger_initialized
    if _logger_initialized:
        return logging.getLogger()

    base_path = get_base_path()
    log_dir = os.path.join(base_path, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    today = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'niuma_{today}.log')

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    root_logger.handlers.clear()

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    _logger_initialized = True
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器

    Args:
        name: 日志记录器名称（通常是模块名）

    Returns:
        Logger对象
    """
    return logging.getLogger(name)
