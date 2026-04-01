# cleanup_manager.py
import os
import logging

class CleanupManager:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def cleanup_local(self, path, max_copies):
        """Удаляет старые локальные резервные копии, оставляя только max_copies."""
        try:
            files = sorted(
                os.listdir(path),
                key=lambda x: os.path.getmtime(os.path.join(path, x))
            )
            for f in files[:-max_copies]:
                file_path = os.path.join(path, f)
                os.remove(file_path)
                self.logger.info(f"Removed local file: {file_path}")
        except Exception as e:
            self.logger.error(f"Local cleanup error: {e}")

    def cleanup_remote(self, ftp_client, remote_dir, max_copies):
        """
        Удаляет старые файлы на FTP-сервере, оставляя только max_copies.
        Требует подключённый FTPClient.
        """
        try:
            files = ftp_client.list_files(remote_dir)
            # Сортируем по времени модификации (если доступно) или по имени
            # Для простоты — по имени, если нет времени модификации
            files_sorted = sorted(files)
            for f in files_sorted[:-max_copies]:
                remote_path = os.path.join(remote_dir, f)
                ftp_client.delete_file(remote_path)
        except Exception as e:
            self.logger.error(f"Remote cleanup error: {e}")