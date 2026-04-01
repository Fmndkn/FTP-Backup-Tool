class BackupErrorCodes:
    """
    Коды ошибок для FTP Backup Tool.
    Используется для структурированного логирования и диагностики.
    """
    # Ошибки конфигурации
    CONFIG_MISSING = "CFG-001"
    CONFIG_VALUE_ERROR = "CFG-002"

    # Ошибки FTP
    FTP_CONNECTION_FAILED = "FTP-001"
    FTP_LOGIN_FAILED = "FTP-002"
    FTP_LIST_FAILED = "FTP-003"
    FTP_UPLOAD_FAILED = "FTP-004"
    FTP_DELETE_FAILED = "FTP-005"

    # Ошибки файловой системы
    LOCAL_DIR_NOT_FOUND = "FS-001"
    LOCAL_FILE_NOT_FOUND = "FS-002"

    # Ошибки синхронизации
    SYNC_INTEGRITY_CHECK_FAILED = "SYNC-001"