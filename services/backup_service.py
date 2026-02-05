# services/backup_service.py
"""
Чистая бизнес-логика бэкапов — без зависимости от интерфейса (CLI/Web/Telegram)
"""

from typing import List, Dict
from core.engine import run_engine
from core.config import Config


def backup_ib(ib_name: str, format_type: str) -> Dict[str, any]:
    """
    Создать бэкап одной информационной базы
    
    Args:
        ib_name: имя ИБ (например, 'artel_2025')
        format_type: 'dump' или 'sql'
    
    Returns:
        {
            "success": bool,
            "ib_name": str,
            "format": str,
            "stdout": str,
            "stderr": str,
            "returncode": int
        }
    """
    config = Config.load()
    cmd = ["--ib", ib_name, "--format", format_type]
    
    result = run_engine("backup.sh", cmd, user=config.BACKUP_USER)
    
    return {
        "success": result["success"],
        "ib_name": ib_name,
        "format": format_type,
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "returncode": result["returncode"]
    }


def backup_multiple(ib_list: List[str], format_type: str) -> List[Dict[str, any]]:
    """
    Создать бэкапы для списка информационных баз (последовательно)
    
    Args:
        ib_list: список имён ИБ
        format_type: 'dump' или 'sql'
    
    Returns:
        Список результатов для каждой ИБ
    """
    results = []
    for ib_name in ib_list:
        results.append(backup_ib(ib_name, format_type))
    return results