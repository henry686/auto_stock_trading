"""
日志模块

统一的日志配置，输出到控制台和文件。
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from config.settings import LOG_LEVEL, LOG_FILE


def setup_logger(name: str = "stock_trading", log_file: Path = None) -> logging.Logger:
    """
    设置日志器

    Args:
        name: 日志器名称
        log_file: 日志文件路径（默认使用 settings.LOG_FILE）

    Returns:
        配置好的 Logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 格式
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 默认 logger 实例
log = setup_logger()
