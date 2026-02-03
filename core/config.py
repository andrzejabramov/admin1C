# Конфигурация оркестратора 1С
import os
from pathlib import Path

class Config:
    """Конфигурация системы"""
    
    # Пути
    BACKUP_ROOT = Path(os.getenv("BACKUP_ROOT", "/var/backups/1c"))
    SCRIPTS_DIR = Path("/opt/1cv8/scripts/engines")
    LOG_FILE = Path("/var/log/1c_orchestrator.log")
    
    # Пользователь для выполнения команд
    BACKUP_USER = os.getenv("BACKUP_USER", "usr1cv8")
    
    @classmethod
    def load(cls):
        """Загрузить конфигурацию (заглушка для будущего расширения)"""
        return cls()
