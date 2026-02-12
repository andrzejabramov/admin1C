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
                     after: str = None, before: str = None,
                     dry_run: bool = False, confirm: bool = False) -> dict:
        """
        Удалить бэкап(ы) ИБ через движок rm.sh
        
        Бизнес-правило безопасности:
        - Для удаления ВСЕХ бэкапов без фильтра требуется подтверждение (--confirm)
          ИЛИ режим симуляции (--dry-run)
        """
        self._validate_ib(ib_name)
        
        # 🔑 ЕДИНСТВЕННАЯ ТОЧКА ПРОВЕРКИ ПОДТВЕРЖДЕНИЯ (бизнес-логика)
        if not dry_run and not confirm and not timestamp and not after and not before:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Требуется --confirm для удаления ВСЕХ бэкапов ИБ '{ib_name}'"
            }
        
        # Формирование аргументов для движка
        args = ["--ib", ib_name]
        if timestamp:
            args.extend(["--timestamp", timestamp])
        if after:
            args.extend(["--after", after])
        if before:
            args.extend(["--before", before])
        if dry_run:
            args.append("--dry-run")
        if confirm or dry_run:  # Для симуляции разрешаем без явного --confirm
            args.append("--confirm")
        
        # Вызов движка через универсальный адаптер с доменным путём
        return run_engine(
            script_path="rm/engines/rm.sh",
            args=args,
            timeout=300,  # 5 минут на операцию
            user="usr1cv8",
            capture_output=True
        )
    
    def remove_all_backups(self, ib_name: str, confirm: bool = False, 
                          dry_run: bool = False) -> dict:
        """
        Удалить ВСЕ бэкапы указанной ИБ
        
        Делегирует проверку подтверждения в remove_backup()
        """
        return self.remove_backup(
            ib_name=ib_name,
            dry_run=dry_run,
            confirm=confirm
        )
    
    def remove_all_ibs(self, dry_run: bool = False, confirm: bool = False) -> dict:
        """
        Удалить ВСЕ бэкапы ВСЕХ ИБ (глобальная операция)
        
        Требует явного подтверждения (--confirm) или симуляции (--dry)
        """
        if not dry_run and not confirm:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Требуется --confirm для удаления ВСЕХ бэкапов всех ИБ (глобальная операция!)"
            }
        
        args = ["--all"]
        if dry_run:
            args.append("--dry-run")
        if confirm or dry_run:
            args.append("--confirm")
        
        return run_engine(
            script_path="rm/engines/rm.sh",
            args=args,
            timeout=600,  # 10 минут на глобальную операцию
            user="usr1cv8",
            capture_output=True
        )
