#!/usr/bin/env python3
"""
Точка входа для FTP Backup Tool.

Этот скрипт инициализирует все компоненты, запускает процесс синхронизации
и очистки, а также обрабатывает критические ошибки. Поддерживает команды
`run` (по умолчанию) и `check` для самопроверки.
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

    # Создаем сабпарсеры для команд 'run' и 'check'
    subparsers = parser.add_subparsers(dest='command', required=False, help='Доступные команды')

    # Подкоманда 'run' - запуск бэкапа
    parser_run = subparsers.add_parser('run', help='Запустить процесс резервного копирования')
    parser_run.add_argument('--config', default='config.ini', help='Путь к конфигурационному файлу')

    # Подкоманда 'check' - self-check
    parser_check = subparsers.add_parser('check', help='Выполнить автоматическую проверку работоспособности')
    parser_check.add_argument('--config', default='config.ini', help='Путь к конфигурационному файлу')

    args = parser.parse_args()

    # Если команда не указана (например, при вызове из cron), считаем, что это 'run'
    if args.command is None:
        args.command = 'run'

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

        # 5. Обработка команды 'check'
        if args.command == 'check':
            logger.info("Запуск самопроверки системы.", extra={"event": "self_check_start"})
            from .check_status import main as run_self_check

            # Модифицируем sys.argv для корректного парсинга внутри run_self_check
            sys.argv = [sys.argv[0], '--config', args.config]

            try:
                run_self_check()
                logger.info("Самопроверка завершена успешно.", extra={"event": "self_check_success"})
            except SystemExit as e:
                # Скрипт проверки сам вызывает sys.exit(). Мы перехватываем это.
                if e.code == 0:
                    logger.info("Самопроверка завершена успешно.", extra={"event": "self_check_success"})
                else:
                    logger.error("Самопроверка выявила критические ошибки.", extra={"event": "self_check_failed"})
                    raise  # Пробрасываем ошибку дальше, чтобы завершить основной скрипт с кодом 1

        # 6. Обработка команды 'run' (основная логика)
        elif args.command == 'run':
            logger.info("Запуск процесса резервного копирования", extra={"event": "startup"})
            logger.debug(f"Используемый конфиг: {args.config}")

            # Создание экземпляров компонентов с передачей логгера
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

            # Выполнение основной логики
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