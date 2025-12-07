import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(log_file: str, log_level: int = logging.INFO) -> logging.Logger:
    """
    Настройка логирования с файловым и консольным handler.
    
    Args:
        log_file: Путь к файлу лога
        log_level: Уровень логирования (по умолчанию INFO)
    
    Returns:
        Настроенный logger
    """
    log_dir = os.path.dirname(log_file) if os.path.dirname(log_file) else "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(file_formatter)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[file_handler, console_handler],
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: {log_file}")
    
    return logger

