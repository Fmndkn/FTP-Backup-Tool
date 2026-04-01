# 📦 FTP Backup Tool

![Version](https://img.shields.io/badge/version-0.0.5-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-green.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

Автоматизированный инструмент для надежного резервного копирования данных на FTP-сервер.

**Ключевые возможности:**
*   **Интеллектуальная синхронизация:** копирует только новые или измененные файлы.
*   **Безопасность:** хранение секретов в переменных окружения (`.env`), а не в открытом коде.
*   **Надежность:** автоматические повторы при сбоях сети и детальные коды ошибок.
*   **Производительность:** параллельная загрузка файлов (многопоточность).
*   **Самодиагностика:** команда `self-check` для проверки системы перед запуском.

---

## 📦 Установка

### 1. Клонируйте репозиторий
```bash
git clone https://github.com/your-username/ftp-backup-tool.git
cd ftp-backup-tool
```

### 2. Создайте виртуальное окружение
Это рекомендуется для изоляции зависимостей проекта.
```bash
python -m venv venv
```
*   **Linux/macOS:**
    ```bash
    source venv/bin/activate
    ```
*   **Windows (PowerShell/Cmd):**
    ```bash
    .\venv\Scripts\activate
    ```

### 3. Установите зависимости
```bash
pip install -r requirements.txt
```

---

## ⚙️ Настройка конфигурации

Проект использует переменные окружения как основной источник настроек. Файл `config.ini` служит резервным вариантом или для документирования.

### 1. Создайте файл `.env`
В корне проекта создайте файл `.env` и добавьте в него свои данные. **НИКОГДА не добавляйте этот файл в систему контроля версий (он должен быть в `.gitignore`).**

**Пример `.env`:**
```env
# --- Настройки FTP ---
FTP_HOST=ftp.yourdomain.com
FTP_USER=backup_user
FTP_PASS=Your_Strong_Password_123!

# --- Пути к данным ---
LOCAL_BACKUP_DIR=/home/user/backups/local # Локальная папка с архивами
REMOTE_BACKUP_DIR=/backups # Папка на FTP-сервере

# --- Настройки очистки (сколько копий хранить) ---
MAX_LOCAL_COPIES=10
MAX_REMOTE_COPIES=10

# --- Логирование ---
LOG_DIR=/var/log/ftp_backup

# --- (Опционально) Планировщик ---
# CRON_SCHEDULE="0 3 * * *" # Запуск каждый день в 03:00
```

### 2. (Опционально) Настройте `config.ini`
Этот файл можно использовать для хранения значений по умолчанию или если вы не используете `.env`.

**Пример `config.ini`:**
```ini
[FTP]
host = ftp.yourdomain.com
user = backup_user
password = your_password_here

[Paths]
local_backup_dir = /home/user/backups/local
remote_backup_dir = /backups

[Cleanup]
max_local_copies = 10
max_remote_copies = 10

[Logging]
log_dir = /var/log/ftp_backup
```

---

## ▶️ Запуск и тестирование

Все команды выполняются из корня проекта при активированном виртуальном окружении (`source venv/bin/activate`).

### 1. Тестовый запуск (Ручной)
Выполните резервное копирование один раз, чтобы убедиться, что всё работает.
```bash
python -m ftp_backup_tool.backup_ftp run --config config.ini
```
*   Если `config.ini` лежит в стандартной папке, флаг `--config` можно опустить.

### 2. Запуск самопроверки (`self-check`)
Перед запуском бэкапа рекомендуется проверить систему на наличие ошибок (доступность FTP, права на папки и т.д.).
```bash
python -m ftp_backup_tool.backup_ftp check --config config.ini
```
*   Если проверка пройдет успешно, вы увидите сообщение `Самопроверка завершена успешно`.

### 3. Просмотр логов в реальном времени
Во время работы скрипта вы можете следить за логами:
```bash
tail -f log/backup.log
```
*(Логи пишутся в формате JSON для удобного парсинга системами мониторинга).*

---

## ⏱️ Автоматизация (Cron)

Для регулярного запуска используйте скрипт `setup_cron.sh`. Он настроит виртуальное окружение и добавит задачу в cron.

### 1. Запустите скрипт настройки
```bash
./setup_cron.sh
```
*   Скрипт автоматически создаст виртуальное окружение, установит зависимости и добавит задачу в cron с расписанием по умолчанию (`0 3 * * *` — каждый день в 03:00).

### 2. (Опционально) Настройте собственное расписание
Вы можете передать параметры скрипту:
```bash
# Запускать каждый час, логи писать в /var/log/my_backups
./setup_cron.sh --schedule "0 * * * *" --log-dir /var/log/my_backups
```

### 3. Проверьте текущие задачи cron
```bash
crontab -l
```
Вы должны увидеть строку, похожую на эту:
```bash
0 3 * * * /path/to/your/project/venv/bin/python /path/to/your/project/ftp_backup_tool/backup_ftp.py --config /path/to/your/project/config.ini >> log/backup.log 2>&1
```

---

## 🗑️ Очистка проекта

Чтобы удалить виртуальное окружение и временные файлы:
```bash
./setup_cron.sh clean # Если вы добавили такую функцию, или просто удалите папку venv вручную
rm -rf venv/
```