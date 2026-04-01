import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from .errors import BackupErrorCodes


class SyncManager:
    def __init__(self, ftp_client, archive_handler, logger=None):
        self.ftp_client = ftp_client
        self.archive_handler = archive_handler
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Кэш списка файлов на сервере
        self._remote_files_cache = None

    def _get_remote_files(self, remote_dir):
        """
        Получает список файлов с сервера.
        Использует кэширование, чтобы избежать повторных запросов к серверу.
        """
        if self._remote_files_cache is None:
            self.logger.debug(f"Запрашиваю список файлов с FTP-сервера (директория: {remote_dir})")
            try:
                self._remote_files_cache = set(self.ftp_client.list_files(remote_dir))
                self.logger.debug(f"Кэшировано {len(self._remote_files_cache)} файлов")
            except Exception as e:
                self.logger.error(f"Не удалось получить список файлов для кэширования: {e}",
                                  extra={"error_code": BackupErrorCodes.FTP_LIST_FAILED})
                # Если ошибка критическая, лучше прервать процесс
                raise
        return self._remote_files_cache

    def _upload_task(self, local_dir, remote_dir, archive_name):
        """
        Задача для потока: загрузить один файл, если его нет на сервере.
        """
        local_path = os.path.join(local_dir, archive_name)
        remote_path = os.path.join(remote_dir, archive_name)

        # Проверяем наличие файла в кэше
        if archive_name in self._get_remote_files(remote_dir):
            self.logger.debug(f"Файл {archive_name} уже есть на сервере. Пропускаем.")
            return {"file": archive_name, "status": "skipped", "reason": "exists"}

        try:
            self.ftp_client.upload_file(local_path, remote_path)
            return {"file": archive_name, "status": "success"}
        except Exception as e:
            # Логируем ошибку и возвращаем информацию о сбое
            self.logger.error(f"Ошибка загрузки {archive_name}: {e}",
                              extra={"error_code": BackupErrorCodes.FTP_UPLOAD_FAILED})
            return {"file": archive_name, "status": "failed", "error": str(e)}

    def sync_archives(self, local_dir, remote_dir):
        """
        Основная функция синхронизации.
        Использует многопоточность для загрузки нескольких файлов одновременно.
        """
        self.logger.info("Начало синхронизации архивов", extra={"event": "sync_start"})

        # Сбрасываем кэш перед новой операцией синхронизации
        self._remote_files_cache = None

        local_archives = self.archive_handler.find_archives(local_dir)

        if not local_archives:
            self.logger.warning("Архивы для загрузки не найдены.", extra={"event": "no_files"})
            return

        self.logger.info(f"Найдено {len(local_archives)} архивов для проверки.",
                         extra={"file_count": len(local_archives)})

        # Используем ThreadPoolExecutor для параллельной загрузки
        # max_workers=5 означает, что одновременно будет загружаться до 5 файлов.
        # Это число можно сделать настраиваемым через конфиг.
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {
                executor.submit(self._upload_task, local_dir, remote_dir, archive): archive
                for archive in local_archives
            }

            for future in as_completed(future_to_file):
                file_name = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result["status"] == "success":
                        self.logger.info(f"Обработан файл: {file_name}",
                                         extra={"event": "file_processed", "status": "success"})
                    elif result["status"] == "skipped":
                        self.logger.debug(f"Файл пропущен: {file_name}",
                                          extra={"event": "file_processed", "status": "skipped"})
                    else:
                        self.logger.warning(f"Файл не загружен: {file_name}",
                                            extra={"event": "file_processed", "status": "failed"})
                except Exception as exc:
                    # Это исключение из самой задачи _upload_task (например, ошибка при открытии файла)
                    self.logger.error(f"Файл {file_name} сгенерировал исключение: {exc}", exc_info=True)
                    results.append({"file": file_name, "status": "error", "error": str(exc)})

        # Итоговый отчет
        success_count = sum(1 for r in results if r["status"] == "success")
        skipped_count = sum(1 for r in results if r["status"] == "skipped")
        failed_count = sum(1 for r in results if r["status"] == "failed")

        self.logger.info(
            f"Синхронизация завершена. Успешно: {success_count}, Пропущено: {skipped_count}, Ошибок: {failed_count}",
            extra={"event": "sync_finish", "success": success_count, "skipped": skipped_count, "failed": failed_count}
        )