"""
rm_service.py — бизнес-логика удаления бэкапов
Вызывает движок через универсальный адаптер core.engine.run_engine()
"""

from pathlib import Path
from core.engine import run_engine
from core.exceptions import NotFoundError, RmError

class RmService:
    """Сервис удаления бэкапов ИБ"""
    
    def __init__(self):
        self.backup_root = Path("/var/backups/1c")
    
    def _validate_ib(self, ib_name: str) -> None:
        """Проверить существование ИБ в хранилище"""
        ib_path = self.backup_root / ib_name
        if not ib_path.exists():
            raise NotFoundError(
                message=f"ИБ '{ib_name}' не найдена в хранилище",
                details=f"Путь: {ib_path}"
            )
        if not ib_path.is_dir():
            raise NotFoundError(
                message=f"'{ib_name}' не является директорией ИБ",
                details=f"Путь: {ib_path}"
            )
    
    def remove_backup(self, ib_name: str, timestamp: str = None, 
                     older_than: str = None, dry_run: bool = False, 
                     confirm: bool = False) -> dict:
        """
        Удалить бэкап(ы) ИБ через движок rm.sh
        
        Бизнес-правило безопасности:
        - Для удаления ВСЕХ бэкапов без фильтра (--timestamp/--older-than)
          требуется подтверждение (--confirm) ИЛИ режим симуляции (--dry-run)
        - Для удаления конкретного бэкапа (--timestamp/--older-than)
          подтверждение не требуется в режиме симуляции
        """
        self._validate_ib(ib_name)
        
        # 🔑 ЕДИНСТВЕННАЯ ТОЧКА ПРОВЕРКИ ПОДТВЕРЖДЕНИЯ (бизнес-логика)
        if not dry_run and not confirm and not timestamp and not older_than:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Требуется --confirm для удаления ВСЕХ бэкапов ИБ '{ib_name}'"
            }
        
        # Формирование аргументов для движка
        args = ["--ib", ib_name]
        if timestamp:
            args.extend(["--timestamp", timestamp])
        if older_than:
            args.extend(["--older-than", older_than])
        if dry_run:
            args.append("--dry-run")
        if confirm or dry_run:  # Для симуляции разрешаем без явного --confirm
            args.append("--confirm")
        
        # Вызов движка через универсальный адаптер с доменным путём
        return run_engine(
            script_path="rm/engines/rm.sh",  # ← Относительный путь от корня проекта
            args=args,
            timeout=300,  # 5 минут на операцию
            user="usr1cv8",
            capture_output=True
        )
    
    def remove_all_backups(self, ib_name: str, confirm: bool = False, 
                          dry_run: bool = False) -> dict:
        """
        Удалить ВСЕ бэкапы ИБ
        
        Делегирует проверку подтверждения в remove_backup()
        """
        return self.remove_backup(
            ib_name=ib_name,
            dry_run=dry_run,
            confirm=confirm
        )
