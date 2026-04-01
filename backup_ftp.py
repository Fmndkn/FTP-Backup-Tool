#!/usr/bin/env python3
"""
FTP Backup Script for existing multi-volume archives with enhanced error handling and log rotation
"""

import argparse
import logging
import sys
import os
from .config import Config
from .ftp_client import FTPClient
from .archive_handler import ArchiveHandler
from .sync_manager import SyncManager
from .cleanup_manager import CleanupManager
from .logger import setup_logger

def main():
    parser = argparse.ArgumentParser(description='FTP Backup Tool')
    parser.add_argument('--config', default='config.ini', help='Path to config file')
    args = parser.parse_args()

    try:
        config = Config(args.config)

        # Определение папки логов
        log_dir = getattr(config, 'log_dir', None)
        if not log_dir:
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            log_dir = os.path.join(script_dir, 'log')

        log_file_path = os.path.join(log_dir, 'backup.log')
        root_logger = setup_logger('backup', log_file_path)

        # Создание экземпляров компонентов с передачей логгера
        ftp_client = FTPClient(
            config.ftp_host,
            config.ftp_user,
            config.ftp_pass,
            logger=root_logger
        )
        archive_handler = ArchiveHandler()
        sync_manager = SyncManager(ftp_client, archive_handler, logger=root_logger)
        cleanup_manager = CleanupManager(logger=root_logger)

        if not ftp_client.connect():
            return

        sync_manager.sync_archives(config.local_backup_dir, config.remote_backup_dir)
        cleanup_manager.cleanup_local(config.local_backup_dir, config.max_local_copies)
        cleanup_manager.cleanup_remote(
            ftp_client,
            config.remote_backup_dir,
            config.max_remote_copies
        )

        ftp_client.close()
    except Exception as e:
        # Логирование критической ошибки, если логгер ещё не инициализирован
        logging.exception(f"Critical error: {e}")

if __name__ == '__main__':
    main()