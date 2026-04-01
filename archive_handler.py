# archive_handler.py
import os
import hashlib

class ArchiveHandler:
    @staticmethod
    def find_archives(path, ext='.tar'):
        return [f for f in os.listdir(path) if f.endswith(ext)]

    @staticmethod
    def file_hash(filepath):
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()