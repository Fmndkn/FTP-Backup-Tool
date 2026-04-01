# ftp_client.py
import ftplib
import logging

class FTPClient:
    def __init__(self, host, user, password, timeout=30, logger=None):
        self.host = host
        self.user = user
        self.password = password
        self.timeout = timeout
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.ftp = None

    def connect(self):
        try:
            self.ftp = ftplib.FTP(self.host, self.user, self.password, timeout=self.timeout)
            self.logger.info(f"Connected to {self.host}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to FTP: {e}")
            return False

    def list_files(self, remote_dir):
        try:
            return self.ftp.nlst(remote_dir)
        except Exception as e:
            self.logger.warning(f"Error listing files in {remote_dir}: {e}")
            return []

    def upload_file(self, local_path, remote_path):
        try:
            with open(local_path, 'rb') as f:
                self.ftp.storbinary(f'STOR {remote_path}', f)
            self.logger.info(f"Uploaded {local_path} to {remote_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to upload {local_path}: {e}")
            return False

    def close(self):
        if self.ftp:
            self.ftp.quit()
            self.logger.info("FTP connection closed")

    def delete_file(self, remote_path):
        """Удаляет файл на FTP-сервере."""
        try:
            self.ftp.delete(remote_path)
            self.logger.info(f"Deleted remote file: {remote_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete {remote_path}: {e}")
            return False