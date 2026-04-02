# logger.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

try:
    import jsonlogger
except ImportError:
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


def setup_logger(name, log_dir, level=logging.INFO):
    """
    Настраивает логгер с двумя хендлерами.

    Args:
        name (str): Имя логгера.
        log_dir (str): Путь к директории, где будут храниться лог-файлы.
        level: Уровень логирования (по умолчанию INFO).

    Returns:
        logging.Logger: Настроенный объект логгера.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Предотвращаем добавление дублирующих хендлеров
    if logger.handlers:
        return logger

    # 1. Формируем полный путь к файлу лога внутри указанной папки
    if not log_dir:
        # Если путь не задан, используем текущую директорию (для отладки)
        log_dir = os.getcwd()

    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, 'backup.log')

    # 2. Хендлер для записи в файл (JSON + Ротация)
    file_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=5 * 1024 * 1024,  # 5 МБ
        backupCount=10,  # Хранить 10 старых файлов
        encoding='utf-8'
    )

    json_formatter = _get_json_formatter()
    if json_formatter:
        file_handler.setFormatter(json_formatter)
        file_handler.addFilter(lambda record: setattr(record, 'service', 'ftp_backup_tool'))
    else:
        std_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(std_formatter)

    # 3. Хендлер для вывода в консоль (Стандартный формат)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(message)s')
    console_handler.setFormatter(console_formatter)

    # Добавляем оба хендлера к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger