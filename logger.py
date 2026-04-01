# logger.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

try:
    # Для форматирования логов в JSON
    import jsonlogger
except ImportError:
    # Если библиотека не установлена, используем стандартный формат
    # (это позволит скрипту запуститься, но без JSON)
    jsonlogger = None


def _get_json_formatter():
    """Возвращает форматтер JSON, если библиотека доступна."""
    if jsonlogger:
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S%z'
        )
        return formatter
    return None


def setup_logger(name, log_file_path, level=logging.INFO):
    """
    Настраивает логгер с двумя хендлерами:
    1. RotatingFileHandler с форматом JSON.
    2. StreamHandler (stdout) со стандартным форматом.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Предотвращаем добавление дублирующих хендлеров при повторном вызове
    if logger.handlers:
        return logger

    # 1. Хендлер для записи в файл (JSON + Ротация)
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=5 * 1024 * 1024,  # 5 МБ
        backupCount=10,  # Хранить 10 старых файлов
        encoding='utf-8'
    )

    json_formatter = _get_json_formatter()
    if json_formatter:
        file_handler.setFormatter(json_formatter)
        # Добавляем поле 'service' для удобства фильтрации во внешних системах
        file_handler.addFilter(lambda record: setattr(record, 'service', 'ftp_backup_tool'))
    else:
        # Если jsonlogger нет, используем стандартный формат
        std_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(std_formatter)

    # 2. Хендлер для вывода в консоль (Стандартный формат)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(message)s')
    console_handler.setFormatter(console_formatter)

    # Добавляем оба хендлера к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger