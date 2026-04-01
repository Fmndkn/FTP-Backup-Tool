#!/usr/bin/env python3
"""
Точка входа для FTP Backup Tool.

Этот скрипт инициализирует все компоненты, запускает процесс синхронизации
и очистки, а также обрабатывает критические ошибки.
"""

import argparse
import logging
import os
import sys

# Импортируем компоненты из модулей проекта
from .config import Config
from .ftp_client import FTPClient
from .archive_handler import ArchiveHandler
from .sync_manager import SyncManager
from .cleanup_manager import CleanupManager


def main():
    """
    Основная функция приложения.
    """
    # 1. Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description='FTP Backup Tool')
    parser.add_argument('--config', default='config.ini',
                        help='Путь к конфигурационному файлу (по умолчанию: config.ini)')
    args = parser.parse_args()

    # Инициализируем корневой логгер (без хендлеров пока)
    root_logger = logging.getLogger('backup')
    root_logger.setLevel(logging.INFO)

    try:
        # 2. Загрузка конфигурации
        config = Config(args.config)

        # 3. Определение пути к логам (из конфига или по умолчанию)
        log_dir = config.log_dir
        if not log_dir:
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            log_dir = os.path.join(script_dir, 'log')

        log_file_path = os.path.join(log_dir, 'backup.log')

        # 4. Настройка логгера (JSON + Ротация + Консоль)
        from .logger import setup_logger
        logger = setup_logger('backup', log_file_path)

        # Заменяем логгер в root_logger на настроенный (если нужно)
        # или просто используем 'logger' далее.
        # Для простоты будем использовать 'logger'.

        logger.info("Запуск процесса резервного копирования", extra={"event": "startup"})
        logger.debug(f"Используемый конфиг: {args.config}")

        # 5. Создание экземпляров компонентов с передачей логгера
        ftp_client = FTPClient(
            host=config.ftp_host,
            user=config.ftp_user,
            password=config.ftp_pass,
            logger=logger
        )

        archive_handler = ArchiveHandler(logger=logger)
        sync_manager = SyncManager(
            ftp_client=ftp_client,
            archive_handler=archive_handler,
            logger=logger
        )

        cleanup_manager = CleanupManager(logger=logger)

        # 6. Выполнение основной логики
        if not ftp_client.connect():
            logger.error("Не удалось установить соединение с FTP. Прерывание работы.",
                         extra={"event": "connection_failed"})
            return

        logger.info("Синхронизация архивов...", extra={"event": "sync_start"})
        sync_manager.sync_archives(
            local_dir=config.local_backup_dir,
            remote_dir=config.remote_backup_dir
        )

        logger.info("Очистка локальных копий...", extra={"event": "cleanup_local_start"})
        cleanup_manager.cleanup_local(
            path=config.local_backup_dir,
            max_copies=config.max_local_copies
        )

        logger.info("Очистка удаленных копий...", extra={"event": "cleanup_remote_start"})
        cleanup_manager.cleanup_remote(
            ftp_client=ftp_client,
            remote_dir=config.remote_backup_dir,
            max_copies=config.max_remote_copies
        )

        ftp_client.close()
        logger.info("Процесс резервного копирования завершен успешно.", extra={"event": "shutdown_success"})

    except Exception as e:
        # Логируем критическую ошибку, если логгер еще не был настроен или упал
        exc_info = sys.exc_info()
        logging.critical(
            f"Критическая ошибка: {e}",
            exc_info=exc_info,
            extra={"event": "critical_error"}
        )
        sys.exit(1)


if __name__ == '__main__':
    main()