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

        # Проверяем наличие всех обязательных параметров
        required_params = [
            ('FTP Host', config.ftp_host),
            ('FTP User', config.ftp_user),
            ('FTP Password', '***' if config.ftp_pass else 'НЕ ЗАДАНО'),
            ('Local Dir', config.local_backup_dir),
            ('Remote Dir', config.remote_backup_dir),
        ]

        for name, value in required_params:
            if not value or (name == 'FTP Password' and value == '***'):
                logger.error(f"ОШИБКА: {name} не задан в конфигурации.",
                             extra={"error_code": BackupErrorCodes.CONFIG_MISSING})
                return False

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
    """Проверяет возможность подключения к FTP серверу и доступность директории."""
    logger.info("3. Проверка соединения с FTP сервером...")

    ftp_client = FTPClient(
        host=config.ftp_host,
        user=config.ftp_user,
        password=config.ftp_pass,
        logger=logger
    )

    try:
        if not ftp_client.connect():
            logger.error("ОШИБКА: Не удалось подключиться к FTP серверу.",
                         extra={"error_code": BackupErrorCodes.FTP_CONNECTION_FAILED})
            return False

        # Проверяем доступность удаленной директории (пробуем получить список файлов)
        try:
            ftp_client.list_files(config.remote_backup_dir)
            logger.info(f"✅ Удаленная директория доступна: {config.remote_backup_dir}")
        except Exception as e:
            logger.error(f"ОШИБКА: Не удалось получить доступ к удаленной директории: {e}",
                         extra={"error_code": BackupErrorCodes.FTP_LIST_FAILED})
            ftp_client.close()
            return False

        ftp_client.close()
        logger.info("✅ Соединение с FTP сервером успешно установлено.")
        return True

    except Exception as e:
        logger.error(f"НЕИЗВЕСТНАЯ ОШИБКА при проверке FTP: {e}")
        return False


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