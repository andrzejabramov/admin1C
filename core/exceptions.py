"""
Иерархия исключений для оркестратора 1С
Расширять по мере надобности — минимальная база для старта
"""

class OrchestratorError(Exception):
    """Базовый класс для всех ошибок оркестратора"""
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message}\n   Подробности: {self.details}"
        return self.message


class ConfigError(OrchestratorError):
    """Ошибка конфигурации"""
    pass


class BackupError(OrchestratorError):
    """Ошибка при создании бэкапа"""
    pass


class BackupTimeoutError(BackupError):
    """
    Ошибка таймаута при создании бэкапа.
    
    Возникает, когда бэкап не завершился за рассчитанное время.
    Рекомендуется увеличить таймаут в конфигурации или проверить производительность сети/диска.
    """
    
    def __init__(self, ib_name: str, timeout_seconds: int, estimated_size_gb: float = None):
        self.ib_name = ib_name
        self.timeout_seconds = timeout_seconds
        self.estimated_size_gb = estimated_size_gb
        
        size_info = f" (оценочный размер: {estimated_size_gb:.1f} ГБ)" if estimated_size_gb else ""
        timeout_min = timeout_seconds // 60
        
        message = (
            f"❌ Прервано по таймауту: бэкап ИБ «{ib_name}» не завершился за {timeout_min} мин{size_info}\n"
            f"   → Для больших ИБ увеличьте BACKUP_TIMEOUT_MINUTES_PER_GB в /opt/1cv8/scripts/core/config.py\n"
            f"   → Или проверьте производительность сети/диска (медленное подключение к БД 10.129.0.27?)"
        )
        super().__init__(message)


class RmError(OrchestratorError):
    """Ошибка при удалении бэкапов"""
    pass


class PermissionError(OrchestratorError):
    """Ошибка прав доступа"""
    pass


class NotFoundError(OrchestratorError):
    """Ресурс не найден (ИБ, бэкап, кластер)"""
    pass


class ClusterError(OrchestratorError):
    """Ошибка взаимодействия с кластером 1С"""
    pass
