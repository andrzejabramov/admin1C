"""
rm_service.py — бизнес-логика удаления бэкапов
Прямой вызов скрипта /opt/1cv8/scripts/engines/rm.sh через subprocess
"""

import subprocess
import sys
from pathlib import Path
from core.exceptions import RmError, PermissionError, NotFoundError

class RmService:
    """Сервис удаления бэкапов ИБ"""
    
    def __init__(self):
        self.backup_root = Path("/var/backups/1c")
        self.rm_script = Path("/opt/1cv8/scripts/engines/rm.sh")
    
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
        Удалить бэкап(ы) ИБ через скрипт rm.sh
        
        Args:
            ib_name: Имя информационной базы
            timestamp: Конкретная метка времени (опционально)
            older_than: Удалить бэкапы старше даты (опционально)
            dry_run: Режим симуляции (не удаляет файлы)
            confirm: Подтверждение для реального удаления
        
        Returns:
            dict: {"success": bool, "stdout": str, "stderr": str}
        """
        try:
            self._validate_ib(ib_name)
            
            # Формируем аргументы для скрипта
            args = ["sudo", "-u", "usr1cv8", str(self.rm_script), "--ib", ib_name]
            if timestamp:
                args.extend(["--timestamp", timestamp])
            if older_than:
                args.extend(["--older-than", older_than])
            if dry_run:
                args.append("--dry-run")
            if confirm or dry_run:  # Для --dry-run подтверждение не требуется (передаём --confirm в скрипт для разблокировки)
                args.append("--confirm")
            
            # Вызов скрипта напрямую через subprocess
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=300  # 5 минут на операцию
            )
            
            # Обработка результата
            if result.returncode != 0:
                stderr = result.stderr.strip() or result.stdout.strip()
                if "не найден" in stderr or "not found" in stderr:
                    raise NotFoundError("Бэкап не найден", stderr)
                elif "Отказано в доступе" in stderr or "Permission denied" in stderr:
                    raise PermissionError("Ошибка прав доступа при удалении бэкапа", stderr)
                else:
                    raise RmError("Ошибка при выполнении операции удаления", stderr)
            
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Таймаут операции удаления (300 сек)"
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e)
            }
    
    def remove_all_backups(self, ib_name: str, confirm: bool = False, 
                          dry_run: bool = False) -> dict:
        """
        Удалить ВСЕ бэкапы ИБ
        
        Для --dry-run подтверждение НЕ требуется — показываем, что будет удалено.
        """
        # Для симуляции подтверждение не нужно (передаём --confirm в скрипт)
        if dry_run:
            return self.remove_backup(ib_name=ib_name, dry_run=True, confirm=True)
        
        # Без --dry-run и без --confirm — блокируем опасную операцию
        if not confirm:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Требуется --confirm для удаления ВСЕХ бэкапов ИБ '{ib_name}'"
            }
        
        return self.remove_backup(ib_name=ib_name, dry_run=False, confirm=True)
