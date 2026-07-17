# utils/logger.py
import logging
import sys
from pathlib import Path
from loguru import logger
from datetime import datetime


def setup_logger(log_file: str = "logs/crawler.log", level: str = "INFO"):
    """
    配置日志系统
    
    Args:
        log_file: 日志文件路径
        level: 日志级别
    """
    # 确保日志目录存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置 loguru
    logger.remove()  # 移除默认handler
    
    # 控制台输出
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # 文件输出
    logger.add(
        log_file,
        level=level,
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8"
    )
    
    return logger
