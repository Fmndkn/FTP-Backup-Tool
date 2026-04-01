#!/bin/bash

# --- НАСТРОЙКИ ПО УМОЛЧАНИЮ ---
CRON_SCHEDULE="0 3 * * *" # По умолчанию: каждый день в 03:00
VENV_NAME="ftp_backup_venv"
LOG_DIR="log"

# --- ПАРСИНГ АРГУМЕНТОВ ---
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -s|--schedule)
        CRON_SCHEDULE="$2"
        shift # past argument
        shift # past value
        ;;
        -l|--log-dir)
        LOG_DIR="$2"
        shift # past argument
        shift # past value
        ;;
        -h|--help)
        echo "Использование: ./setup_cron.sh [ОПЦИИ]"
        echo "  -s, --schedule <cron_expr>   Частота запуска (например, '0 3 * * *'). По умолчанию: '0 3 * * *'"
        echo "  -l, --log-dir <путь>         Папка для логов. По умолчанию: 'log'"
        echo "  -h, --help                   Показать эту справку"
        exit 0
        ;;
        *)    # неизвестный параметр
        echo "Неизвестный параметр: $1"
        exit 1
        ;;
    esac
done

# --- ПУТИ ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
VENV_DIR="$SCRIPT_DIR/$VENV_NAME"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"
CRON_SCRIPT_PATH="$SCRIPT_DIR/backup_ftp.py"

# --- ВАЛИДАЦИЯ ---
if [ ! -f "$CRON_SCRIPT_PATH" ]; then
    echo "Ошибка: скрипт '$CRON_SCRIPT_PATH' не найден."
    exit 1
fi

# --- СОЗДАНИЕ ВИРТУАЛЬНОГО ОКРУЖЕНИЯ И УСТАНОВКА ЗАВИСИМОСТЕЙ ---
echo "--- Настройка окружения ---"
if [ ! -d "$VENV_DIR" ]; then
    echo "Создаю виртуальное окружение: $VENV_NAME"
    python3 -m venv "$VENV_DIR" || { echo "Ошибка создания venv"; exit 1; }
fi

echo "Обновляю pip и устанавливаю зависимости"
"$PIP_BIN" install --upgrade pip || { echo "Ошибка обновления pip"; exit 1; }
"$PIP_BIN" install -r requirements.txt || { echo "Ошибка установки зависимостей"; exit 1; }

# --- ФОРМИРОВАНИЕ КОМАНДЫ ДЛЯ КРОНА ---
# Формируем команду, которая будет выполняться кроном.
# Используем абсолютные пути для надежности.
CRON_COMMAND="$PYTHON_BIN $CRON_SCRIPT_PATH --config config.ini"

# Добавляем параметр логирования, если папка отличается от стандартной (log в папке скрипта)
DEFAULT_LOG_DIR="$SCRIPT_DIR/log"
if [ "$LOG_DIR" != "$DEFAULT_LOG_DIR" ]; then
    CRON_COMMAND+=" | tee -a '$LOG_DIR/backup.log'" # Логирование в файл и stdout (для cron mail)
else
    CRON_COMMAND+=" >> '$LOG_DIR/backup.log' 2>&1" # Только в файл
fi

# --- ДОБАВЛЕНИЕ ЗАДАЧИ В КРОН ---
echo "--- Добавление задачи в cron ($CRON_SCHEDULE) ---"
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $CRON_COMMAND") | crontab -

# Проверяем, добавилась ли задача
echo "Текущие задачи cron:"
crontab -l | grep "$CRON_COMMAND" || echo "Задача не найдена. Проверьте права доступа."

echo "Готово. Резервное копирование будет выполняться по расписанию: $CRON_SCHEDULE"