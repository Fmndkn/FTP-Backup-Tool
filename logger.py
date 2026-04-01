# logger.py
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name, log_file_path, level=logging.INFO):
    """
    Настраивает логгер с ротацией файлов.
    :param name: Имя логгера.
    :param log_file_path: Полный путь к файлу лога.
    :param level: Уровень логирования.
    :return: Настроенный логгер.
    """
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding='utf-8'
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Предотвращает дублирование хендлеров при повторных вызовах
    if not logger.handlers:
        logger.addHandler(handler)
    return logger