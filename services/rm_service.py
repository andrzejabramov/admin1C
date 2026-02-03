# Сервис удаления бэкапов
from adapters.bash_adapter import BashAdapter
from core.config import Config
from typing import Optional, Dict

class RmService:
    """
    Сервис для ручного удаления бэкапов информационных баз 1С
    
    Примеры использования:
        >>> service = RmService()
        >>> result = service.remove_backup("artel_2025", timestamp="20260203_204828", dry_run=True)
        >>> print(result["success"])  # True/False
    """
    
    def __init__(self, config=None):
        self.config = config or Config.load()
        self.bash = BashAdapter(str(self.config.SCRIPTS_DIR))
        self.user = self.config.BACKUP_USER
    
    def remove_backup(
        self,
        ib_name: str,
        timestamp: Optional[str] = None,
        older_than: Optional[str] = None,
        dry_run: bool = False,
        confirm: bool = False
    ) -> Dict[str, any]:
        """
        Удалить бэкап информационной базы
        
        Args:
            ib_name: имя информационной базы (например, 'artel_2025')
            timestamp: метка времени конкретного бэкапа (ГГГГММДД_ЧЧММСС)
            older_than: удалить бэкапы старше указанной даты (ГГГГММДД)
            dry_run: режим симуляции (без фактического удаления)
            confirm: подтверждение для реальных операций (требуется для удаления)
        
        Returns:
            dict с результатом выполнения
        """
        cmd = ["--ib", ib_name]
        
        if timestamp:
            cmd.extend(["--timestamp", timestamp])
        elif older_than:
            cmd.extend(["--older-than", older_than])
        
        if dry_run:
            cmd.append("--dry-run")
        elif confirm:
            cmd.append("--confirm")
        else:
            # Без --confirm реальное удаление запрещено
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Требуется --confirm для реального удаления"
            }
        
        return self.bash.execute("rm.sh", cmd, user=self.user)
    
    def remove_all_backups(self, ib_name: str, confirm: bool = False) -> Dict[str, any]:
        """
        Удалить ВСЕ бэкапы указанной информационной базы
        
        Args:
            ib_name: имя информационной базы
            confirm: подтверждение (обязательно для удаления)
        
        Returns:
            dict с результатом выполнения
        """
        cmd = ["--ib", ib_name]
        if confirm:
            cmd.append("--confirm")
        else:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Требуется --confirm для удаления всех бэкапов"
            }
        
        return self.bash.execute("rm.sh", cmd, user=self.user)
    
    def remove_all_backups_globally(self, confirm: bool = False) -> Dict[str, any]:
        """
        Удалить ВСЕ бэкапы ВСЕХ информационных баз (осторожно!)
        
        Args:
            confirm: подтверждение (обязательно для удаления)
        
        Returns:
            dict с результатом выполнения
        """
        cmd = ["--all"]
        if confirm:
            cmd.append("--confirm")
        else:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Требуется --confirm для глобального удаления"
            }
        
        return self.bash.execute("rm.sh", cmd, user=self.user)
