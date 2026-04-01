# config.py
import configparser
import os

class Config:
    def __init__(self, config_path='config.ini'):
        self.config_path = config_path
        self.parser = configparser.ConfigParser()
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file {self.config_path} not found")
        self.parser.read(self.config_path)

    @property
    def ftp_host(self):
        return self.parser.get('FTP', 'host')
    @property
    def ftp_user(self):
        return self.parser.get('FTP', 'user')
    @property
    def ftp_pass(self):
        return self.parser.get('FTP', 'password')
    @property
    def local_backup_dir(self):
        return self.parser.get('Paths', 'local_backup_dir')
    @property
    def remote_backup_dir(self):
        return self.parser.get('Paths', 'remote_backup_dir')
    @property
    def max_local_copes(self):
        return self.parser.getint('Cleanup', 'max_local_copies')
    @property
    def max_remote_copes(self):
        return self.parser.getint('Cleanup', 'max_remote_copies')

    @property
    def log_dir(self):
        """Возвращает путь к папке логов, если задан в конфиге, иначе None."""
        if self.parser.has_section('Logging') and self.parser.has_option('Logging', 'log_dir'):
            return self.parser.get('Logging', 'log_dir')
        return None