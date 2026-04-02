import os
import configparser
from dotenv import load_dotenv
from cryptography.fernet import Fernet


class Config:
    def __init__(self, config_path='config.ini'):
        load_dotenv()
        self.parser = configparser.ConfigParser()
        self.parser.read(config_path)
        self.encryption_key = os.getenv('ENCRYPTION_KEY')
        self.fernet = Fernet(self.encryption_key.encode()) if self.encryption_key else None

    def _get_value(self, env_var, section, option, default=None):
        value = os.getenv(env_var) if env_var else None
        if value is not None:
            return value
        if self.parser.has_section(section) and self.parser.has_option(section, option):
            return self.parser.get(section, option)
        return default

    @property
    def ftp_host(self):
        val = self._get_value('FTP_HOST', 'FTP', 'host')
        if not val:
            raise ValueError("Не указан FTP-хост (FTP_HOST или [FTP] host)")
        return val

    @property
    def ftp_user(self):
        val = self._get_value('FTP_USER', 'FTP', 'user')
        if not val:
            raise ValueError("Не указан FTP-пользователь (FTP_USER или [FTP] user)")
        return val

    @property
    def ftp_pass(self):
        pass_from_env = os.getenv('FTP_PASS')
        if pass_from_env:
            return pass_from_env

        plain_pass = self._get_value(None, 'FTP', 'password')
        if plain_pass:
            return plain_pass

        if self.fernet:
            encrypted_pass = self._get_value(None, 'FTP', 'password_encrypted')
            if encrypted_pass:
                try:
                    decrypted = self.fernet.decrypt(encrypted_pass.encode())
                    return decrypted.decode()
                except Exception as e:
                    raise ValueError("Ошибка расшифровки пароля. Проверьте ENCRYPTION_KEY.") from e

        raise ValueError("Пароль FTP не найден ни в переменных окружения, ни в конфиге.")

    @property
    def local_backup_dir(self):
        val = self._get_value('LOCAL_BACKUP_DIR', 'Paths', 'local_backup_dir')
        if not val:
            raise ValueError("Не указан путь к локальным бэкапам (LOCAL_BACKUP_DIR или [Paths] local_backup_dir)")
        return val

    @property
    def remote_backup_dir(self):
        val = self._get_value('REMOTE_BACKUP_DIR', 'Paths', 'remote_backup_dir')
        if not val:
            raise ValueError("Не указан путь к удалённым бэкапам (REMOTE_BACKUP_DIR или [Paths] remote_backup_dir)")
        return val

    @property
    def max_local_copies(self):
        val = self._get_value('MAX_LOCAL_COPIES', 'Cleanup', 'max_local_copies')
        if not val:
            raise ValueError("Не указано количество локальных копий (MAX_LOCAL_COPIES или [Cleanup] max_local_copies)")
        return int(val)

    @property
    def max_remote_copies(self):
        val = self._get_value('MAX_REMOTE_COPIES', 'Cleanup', 'max_remote_copies')
        if not val:
            raise ValueError("Не указано количество удалённых копий (MAX_REMOTE_COPIES или [Cleanup] max_remote_copies)")
        return int(val)

    @property
    def log_dir(self):
        return self._get_value('LOG_DIR', 'Logging', 'log_dir')