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
