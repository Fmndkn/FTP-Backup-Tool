# ftp_client.py
import ftplib
import logging
import socket
from contextlib import suppress
from .errors import BackupErrorCodes
from .utils import retry

class FTPClient:
    def __init__(self, host, user, password, timeout=30, logger=None):
        self.host = host
        self.user = user
        self.password = password
        self.timeout = timeout
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.ftp = None

    def connect(self):
        """Устанавливает соединение с FTP-сервером."""
        try:
            self.logger.info(f"Попытка подключения к {self.host}")
            self.ftp = ftplib.FTP(self.host, timeout=self.timeout)
            self.ftp.login(self.user, self.password)
            self.logger.info(f"Успешно подключено к {self.host}")
            return True
        except ftplib.all_errors as e:
            code = (BackupErrorCodes.FTP_CONNECTION_FAILED
                    if 'Connection' in str(e) else BackupErrorCodes.FTP_LOGIN_FAILED)
            self.logger.error(f"Ошибка подключения/логина к {self.host}: {e}",
                             extra={"error_code": code})
            self.close() # Убедимся, что соединение закрыто при ошибке
            return False

    # --- НОВЫЙ МЕТОД: close ---
    def close(self):
        """
        Корректно закрывает соединение с FTP-сервером.
        Использует suppress для игнорирования ошибок, если соединения не было.
        """
        if self.ftp:
            self.logger.debug(f"Закрытие соединения с {self.host}")
            with suppress(Exception):
                self.ftp.quit() # quit() предпочтительнее close()
            self.ftp = None
    # --------------------------------

    # --- НОВЫЕ МЕТОДЫ: Контекстный менеджер ---
    def __enter__(self):
        """Вход в контекстный менеджер. Пробует установить соединение."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера. Всегда закрывает соединение."""
        self.close()
    # -------------------------------------------

    # ... (методы list_files, upload_file, delete_file остаются без изменений) ...

    @retry(
        max_retries=5,
        initial_delay=2,
        backoff_factor=2.5,
        exceptions=(ftplib.all_errors, socket.timeout, ConnectionResetError),
        logger=None
    )
    def list_files(self, remote_dir):
        """Получает список файлов на сервере."""
        self.logger.debug(f"Запрос списка файлов в '{remote_dir}'")
        files = self.ftp.nlst(remote_dir)
        self.logger.debug(f"Получено {len(files)} файлов")
        return files

    @retry(
        max_retries=5,
        initial_delay=2,
        backoff_factor=2.5,
        exceptions=(ftplib.all_errors, OSError),
        logger=None
    )
    def upload_file(self, local_path, remote_path):
        """Загружает файл на сервер."""
        self.logger.info(f"Начало загрузки {local_path} -> {remote_path}")
        with open(local_path, 'rb') as f:
            self.ftp.storbinary(f'STOR {remote_path}', f)
        self.logger.info(f"Успешная загрузка {local_path}")
        return True

    @retry(
        max_retries=3,
        initial_delay=1,
        backoff_factor=2,
        exceptions=(ftplib.all_errors,),
        logger=None
    )
    def delete_file(self, remote_path):
        """Удаляет файл на сервере."""
        self.logger.info(f"Удаление файла на сервере: {remote_path}")
        self.ftp.delete(remote_path)
        self.logger.info(f"Успешное удаление {remote_path}")