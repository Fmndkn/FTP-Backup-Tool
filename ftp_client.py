# ftp_client.py
import ftplib
import logging
import socket
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
            code = BackupErrorCodes.FTP_CONNECTION_FAILED if 'Connection' in str(e) else BackupErrorCodes.FTP_LOGIN_FAILED
            self.logger.error(f"Ошибка подключения/логина к {self.host}: {e}", extra={"error_code": code})
            return False

    @retry(
        max_retries=5,
        initial_delay=2,
        backoff_factor=2.5,
        exceptions=(ftplib.all_errors, socket.timeout, ConnectionResetError),
        logger=None # Логгер будет взят из self.logger внутри метода-обертки
    )
    def list_files(self, remote_dir):
        """
        Получает список файлов на сервере.
        Декоратор @retry обеспечивает устойчивость к временным сбоям сети.
        """
        self.logger.debug(f"Запрос списка файлов в '{remote_dir}'")
        files = self.ftp.nlst(remote_dir)
        self.logger.debug(f"Получено {len(files)} файлов")
        return files

    @retry(
        max_retries=5,
        initial_delay=2,
        backoff_factor=2.5,
        exceptions=(ftplib.all_errors, OSError), # OSError для проблем с локальным файлом
        logger=None
    )
    def upload_file(self, local_path, remote_path):
        """Загружает файл на сервер с автоматическими повторами."""
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
        """Удаляет файл на сервере с автоматическими повторами."""
        self.logger.info(f"Удаление файла на сервере: {remote_path}")
        self.ftp.delete(remote_path)
        self.logger.info(f"Успешное удаление {remote_path}")