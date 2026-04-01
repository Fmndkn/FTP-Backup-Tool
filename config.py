import os, base64, configparser
from dotenv import load_dotenv
from cryptography.fernet import Fernet


class Config:
    def __init__(self, config_path='config.ini'):
        load_dotenv()
        self.parser = configparser.ConfigParser()
        self.parser.read(config_path)

        # Ключ шифрования из переменной окружения (безопасно)
        self.encryption_key = os.getenv('ENCRYPTION_KEY')
        self.fernet = Fernet(self.encryption_key.encode()) if self.encryption_key else None

    def _get_value(self, env_var, section, option, default=None):
        value = os.getenv(env_var)
        if value is not None:
            return value
        if self.parser.has_section(section) and self.parser.has_option(section, option):
            return self.parser.get(section, option)
        return default

    @property
    def ftp_pass(self):
        # 1. Пробуем взять из переменной окружения (самый высокий приоритет)
        pass_from_env = os.getenv('FTP_PASS')
        if pass_from_env:
            return pass_from_env

        # 2. Пробуем взять из config.ini как есть (старый способ)
        plain_pass = self._get_value(None, 'FTP', 'password')
        if plain_pass:
            return plain_pass

        # 3. Пробуем взять зашифрованный пароль и расшифровать его
        if self.fernet:
            encrypted_pass = self._get_value(None, 'FTP', 'password_encrypted')
            if encrypted_pass:
                try:
                    decrypted = self.fernet.decrypt(encrypted_pass.encode())
                    return decrypted.decode()
                except Exception as e:
                    raise ValueError("Ошибка расшифровки пароля. Проверьте ENCRYPTION_KEY.") from e

        raise ValueError("Пароль FTP не найден ни в переменных окружения, ни в конфиге.")