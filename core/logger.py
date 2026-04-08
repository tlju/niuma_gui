"""
日志配置模块
提供统一的日志记录功能
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logger(log_level=logging.INFO):
    """
    配置日志系统

    Args:
        log_level: 日志级别，默认为INFO
    """
    # 创建logs目录
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成日志文件名（按日期）
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(log_dir, f'niuma_{today}.log')

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有的处理器
    root_logger.handlers.clear()

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器（滚动日志，每个文件最大10MB，保留5个备份）
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name):
    """
    获取指定名称的日志记录器

    Args:
        name: 日志记录器名称（通常是模块名）

    Returns:
        Logger对象
    """
    return logging.getLogger(name)


# 初始化日志系统
logger = setup_logger()
