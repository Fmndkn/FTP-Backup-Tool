#!/usr/bin/env python3
"""
Утилита self-check для FTP Backup Tool.
Выполняет автоматическую проверку конфигурации и доступности ресурсов.
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Импортируем компоненты проекта
from .config import Config
from .ftp_client import FTPClient
from .errors import BackupErrorCodes

# Настраиваем простой логгер для вывода в консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('self_check')


def check_config(config_path):
    """Проверяет наличие и корректность конфигурационного файла."""
    logger.info("1. Проверка конфигурации...")
    try:
        config = Config(config_path)

        # --- ИСПРАВЛЕННАЯ ПРОВЕРКА ПАРАМЕТРОВ ---
        # Проверяем наличие всех обязательных параметров
        # Используем кортежи (имя, значение, is_password_flag)
        params_to_check = [
            ('FTP Host', config.ftp_host, False),
            ('FTP User', config.ftp_user, False),
            ('FTP Password', config.ftp_pass, True),  # Передаем реальное значение
            ('Local Dir', config.local_backup_dir, False),
            ('Remote Dir', config.remote_backup_dir, False),
        ]

        for name, real_value, is_password in params_to_check:
            display_value = '***' if is_password else real_value

            # Проверяем, что реальное значение не пустое (None или пустая строка)
            if not real_value:
                logger.error(f"ОШИБКА: {name} не задан в конфигурации.",
                             extra={"error_code": BackupErrorCodes.CONFIG_MISSING})
                return False
            else:
                logger.info(f"✅ {name}: {display_value}")

        logger.info("✅ Конфигурация в порядке.")
        return True

    except FileNotFoundError:
        logger.error(f"ОШИБКА: Конфигурационный файл '{config_path}' не найден.",
                     extra={"error_code": BackupErrorCodes.CONFIG_MISSING})
        return False
    except Exception as e:
        logger.error(f"ОШИБКА: Не удалось прочитать конфигурацию: {e}",
                     extra={"error_code": BackupErrorCodes.CONFIG_VALUE_ERROR})
        return False


def check_local_paths(config):
    """Проверяет существование локальных директорий и наличие прав на запись."""
    logger.info("2. Проверка локальных путей...")

    # Проверка директории бэкапов
    if not os.path.isdir(config.local_backup_dir):
        logger.error(f"ОШИБКА: Локальная директория не существует: {config.local_backup_dir}",
                     extra={"error_code": BackupErrorCodes.LOCAL_DIR_NOT_FOUND})
        return False

    # Проверка прав на запись (создаем и удаляем временный файл)
    test_file = os.path.join(config.local_backup_dir, '.write_test')
    try:
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info(f"✅ Локальная директория доступна для записи: {config.local_backup_dir}")
    except PermissionError:
        logger.error(f"ОШИБКА: Нет прав на запись в локальную директорию: {config.local_backup_dir}")
        return False

    # Проверка директории логов (если она отличается от стандартной)
    log_dir = config.log_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'log')
    if not os.path.exists(log_dir):
        logger.warning(f"ВНИМАНИЕ: Папка для логов не существует. Будет создана автоматически: {log_dir}")
    else:
        if not os.access(log_dir, os.W_OK):
            logger.error(f"ОШИБКА: Нет прав на запись в папку логов: {log_dir}")
            return False

    logger.info("✅ Локальные пути в порядке.")
    return True


def check_ftp_connection(config):
    """Проверяет возможность подключения к FTP серверу."""
    logger.info("3. Проверка соединения с FTP сервером...")

    # Используем контекстный менеджер для автоматического закрытия соединения
    with FTPClient(
            host=config.ftp_host,
            user=config.ftp_user,
            password=config.ftp_pass,
            logger=logger
    ) as ftp_client:

        # Метод connect() внутри __enter__ должен возвращать True/False или бросать исключение
        # Давайте предположим, что он бросает исключение или возвращает False при ошибке.
        # Если он возвращает False, объект будет создан, но соединение не установится.

        # Проверяем, успешно ли прошло соединение (зависит от реализации __enter__)
        # Если connect() внутри __enter__ бросает исключение, код сюда не дойдет.

        # Проверяем доступность удаленной директории
        try:
            ftp_client.list_files(config.remote_backup_dir)
            logger.info(f"✅ Удаленная директория доступна: {config.remote_backup_dir}")
            logger.info("✅ Соединение с FTP сервером успешно установлено.")
            return True

        except Exception as e:
            logger.error(f"ОШИБКА: Не удалось получить доступ к удаленной директории: {e}",
                         extra={"error_code": BackupErrorCodes.FTP_LIST_FAILED})
            return False

    # Код здесь выполнится после выхода из блока 'with', т.е. соединение уже закрыто.


def main():
    parser = argparse.ArgumentParser(description='Self-check утилита для FTP Backup Tool.')
    parser.add_argument('--config', default='config.ini', help='Путь к конфигурационному файлу')
    args = parser.parse_args()

    logger.info("=== ЗАПУСК SELF-CHECK ===")

    # Последовательная проверка всех компонентов
    config_ok = check_config(args.config)
    if not config_ok:
        sys.exit(1)  # Критическая ошибка, выходим

    # Если конфиг ок, создаем объект для дальнейших проверок
    config = Config(args.config)

    local_ok = check_local_paths(config)
    if not local_ok:
        sys.exit(1)

    ftp_ok = check_ftp_connection(config)
    if not ftp_ok:
        sys.exit(1)

    logger.info("=== SELF-CHECK ЗАВЕРШЕН УСПЕШНО! Система готова к работе. ===")


if __name__ == '__main__':
    main()