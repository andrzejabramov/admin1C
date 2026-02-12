# backup/services/backup_service.py
"""
Чистая бизнес-логика бэкапов — без зависимости от интерфейса (CLI/Web/Telegram)
Реализует адаптивный таймаут и проверку дискового пространства.
"""

from typing import List, Dict, Optional
from core.engine import run_engine
from core.config import Config, BACKUP_ROOT
from core.exceptions import BackupTimeoutError
import subprocess
import sys
import os
import shutil


def get_ib_size(ib_name: str) -> Optional[int]:
    """
    Получить размер ИБ в байтах через запрос к PostgreSQL.
    Возвращает None при ошибке подключения.
    """
    config = Config.load()
    
    # Ключ -H устанавливает домашнюю директорию usr1cv8 для поиска .pgpass
    cmd = [
        "sudo", "-u", config.BACKUP_USER, "-H",
        "/usr/lib/postgresql/15/bin/psql",
        "-h", "10.129.0.27",
        "-p", "5432",
        "-U", "postgres",
        "-d", ib_name,
        "-tAc", f"SELECT pg_database_size('{ib_name}')"
    ]
    
    # Явно указываем PGPASSFILE для надёжности
    env = os.environ.copy()
    env["PGPASSFILE"] = f"/home/{config.BACKUP_USER}/.pgpass"
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            size_str = result.stdout.strip().replace(' ', '').replace(',', '')
            return int(size_str) if size_str.isdigit() else None
        else:
            return None
    except Exception:
        return None


def estimate_backup_size(ib_name: str, format_type: str = "dump") -> float:
    """
    Оценить размер бэкапа одной ИБ в гигабайтах.
    
    Скорректированные коэффициенты на основе реальных замеров:
      - dump: ~45% от pg_database_size() (бинарный формат + исключение индексов/мёртвых кортежей)
      - sql.gz: ~25% от pg_database_size() (текст + gzip)
    """
    size_bytes = get_ib_size(ib_name) or 0
    size_gb = size_bytes / (1024 ** 3) if size_bytes else 0.1  # минимум 0.1 ГБ
    
    if format_type == "sql":
        return max(0.1, size_gb * 0.25)
    else:  # dump
        return max(0.1, size_gb * 0.45)


def estimate_total_backup_size(ib_list: List[str], format_type: str = "dump") -> float:
    """
    Оценить суммарный размер бэкапов для списка ИБ.
    """
    total = 0.0
    for ib_name in ib_list:
        total += estimate_backup_size(ib_name, format_type)
    return total


def get_free_space(path: str = str(BACKUP_ROOT)) -> float:
    """
    Получить свободное место на диске в гигабайтах.
    """
    try:
        stat = shutil.disk_usage(path)
        return stat.free / (1024 ** 3)
    except Exception:
        return 0.0


def check_disk_space(ib_list: List[str], format_type: str = "dump", safety_margin: float = 0.5) -> Dict[str, any]:
    """
    Проверить достаточность дискового пространства для бэкапа.
    """
    required_gb = estimate_total_backup_size(ib_list, format_type) + safety_margin
    free_gb = get_free_space()
    
    sufficient = free_gb >= required_gb
    shortage = max(0.0, required_gb - free_gb)
    
    if sufficient:
        message = (
            f"✅ Достаточно места для бэкапа {len(ib_list)} ИБ:\n"
            f"   Требуется: {required_gb:.1f} ГБ (включая запас {safety_margin:.1f} ГБ)\n"
            f"   Свободно:  {free_gb:.1f} ГБ"
        )
    else:
        message = (
            f"❌ НЕДОСТАТОЧНО места для бэкапа {len(ib_list)} ИБ:\n"
            f"   Требуется: {required_gb:.1f} ГБ (включая запас {safety_margin:.1f} ГБ)\n"
            f"   Свободно:  {free_gb:.1f} ГБ\n"
            f"   Не хватает: {shortage:.1f} ГБ"
        )
    
    return {
        "sufficient": sufficient,
        "required_gb": required_gb,
        "free_gb": free_gb,
        "margin_gb": safety_margin,
        "shortage_gb": shortage,
        "message": message
    }


def backup_ib(ib_name: str, format_type: str, dry_run: bool = False) -> Dict[str, any]:
    """
    Создать бэкап одной информационной базы с адаптивным таймаутом.
    """
    config = Config.load()
    cmd = ["--ib", ib_name, "--format", format_type]

    if dry_run:
        timeout = 300
        capture = True
    else:
        size_bytes = get_ib_size(ib_name)
        timeout = estimate_backup_timeout(ib_name, size_bytes)
        capture = False

    try:
        result = run_engine(
            "backup/engines/backup.sh",  # ← КРИТИЧЕСКИ ВАЖНО: полный путь от корня проекта
            cmd,
            timeout=timeout,
            user=config.BACKUP_USER,
            capture_output=capture
        )
    except BackupTimeoutError as e:
        # Оборачиваем таймаут в структуру результата для единообразия
        return {
            "success": False,
            "ib_name": ib_name,
            "format": format_type,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }

    # Улучшаем диагностику при таймауте (для случая, когда исключение не было выброшено)
    if not result["success"] and "Timeout expired" in result.get("stderr", ""):
        size_gb = (size_bytes / (1024 ** 3)) if size_bytes else 0
        size_info = f" (~{size_gb:.1f} ГБ)" if size_bytes and size_bytes > 0 else " (размер не определён)"
        timeout_min = timeout // 60
        
        result["stderr"] = (
            f"❌ Прервано по таймауту: бэкап ИБ «{ib_name}»{size_info} не завершился за {timeout_min} мин\n"
            f"   → Для очень больших ИБ увеличьте коэффициент в конфигурации"
        )

    return {
        "success": result["success"],
        "ib_name": ib_name,
        "format": format_type,
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "returncode": result["returncode"]
    }


def estimate_backup_timeout(ib_name: str, size_bytes: Optional[int] = None) -> int:
    """
    Рассчитать адаптивный таймаут для бэкапа ИБ.
    
    Формула: 5 минут на каждый ГБ данных + 5 минут запаса.
    Если размер неизвестен — используем 1 ГБ как минимум.
    """
    config = Config.load()
    
    if size_bytes is None or size_bytes == 0:
        # Эвристика: минимум 1 ГБ для неопределённых ИБ
        size_gb = 1.0
    else:
        size_gb = size_bytes / (1024 ** 3)
    
    timeout_minutes = config.BACKUP_TIMEOUT_MINUTES_PER_GB * (size_gb + 1)
    return max(config.BACKUP_TIMEOUT_MINIMUM, int(timeout_minutes * 60))


def backup_multiple(ib_list: List[str], format_type: str, dry_run: bool = False) -> List[Dict[str, any]]:
    """
    Создать бэкапы для списка информационных баз (последовательно)
    """
    results = []
    for ib_name in ib_list:
        results.append(backup_ib(ib_name, format_type, dry_run))
    return results