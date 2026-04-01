# sync_manager.py
from .ftp_client import FTPClient
from .archive_handler import ArchiveHandler

class SyncManager:
    def __init__(self, ftp_client: FTPClient, archive_handler: ArchiveHandler, logger=None):
        self.ftp_client = ftp_client
        self.archive_handler = archive_handler
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def sync_archives(self, local_dir, remote_dir):
        local_archives = self.archive_handler.find_archives(local_dir)
        remote_files = self.ftp_client.list_files(remote_dir)

        for archive in local_archives:
            if archive not in remote_files:
                local_path = os.path.join(local_dir, archive)
                remote_path = os.path.join(remote_dir, archive)
                if not self.ftp_client.upload_file(local_path, remote_path):
                    self.logger.warning(f"Skipping {archive} due to upload error")