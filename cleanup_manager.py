# cleanup_manager.py
import os
import logging
from .errors import BackupErrorCodes


class CleanupManager:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def cleanup_local(self, path, max_copies):
        """Удаляет старые локальные резервные копии."""
        if not os.path.isdir(path):
            self.logger.error(f"Локальная папка для очистки не найдена: {path}",
                              extra={"error_code": BackupErrorCodes.LOCAL_DIR_NOT_FOUND})
            return

        try:
            files = sorted(
                os.listdir(path),
                key=lambda x: os.path.getmtime(os.path.join(path, x))
            )
            if len(files) <= max_copies:
                self.logger.debug(f"Локальная очистка не требуется. Копий: {len(files)}, лимит: {max_copies}")
                return

            for f in files[:-max_copies]:
                file_path = os.path.join(path, f)
                os.remove(file_path)
                self.logger.info(f"Удален локальный файл: {file_path}", extra={"deleted_file": f})
            self.logger.info(f"Локальная очистка завершена. Осталось копий: {max_copies}")

        except Exception as e:
            self.logger.error(f"Ошибка при локальной очистке: {e}", exc_info=True)