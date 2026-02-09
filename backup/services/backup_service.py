# services/backup_service.py
"""
Чистая бизнес-логика бэкапов — без зависимости от интерфейса (CLI/Web/Telegram)
"""

from typing import List, Dict, Optional
from core.engine import run_engine
from core.config import Config
import subprocess
import sys
import os


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
            print(f"[DEBUG] Ошибка размера ИБ '{ib_name}': {result.stderr.strip()[:100]}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"[DEBUG] Исключение размера ИБ '{ib_name}': {e}", file=sys.stderr)
        return None


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

    result = run_engine(
        "backup.sh",
        cmd,
        timeout=timeout,
        user=config.BACKUP_USER,
        capture_output=capture
    )

    # Улучшаем диагностику при таймауте — используем ПРАВИЛЬНОЕ имя ИБ (ib_name)
    if not result["success"] and "Timeout expired" in result.get("stderr", ""):
        size_gb = (size_bytes / (1024 ** 3)) if size_bytes else 0
        size_info = f" (~{size_gb:.1f} ГБ)" if size_bytes and size_bytes > 0 else " (размер не определён)"
        timeout_min = timeout // 60
        
        result["stderr"] = (
            f"❌ Прервано по таймауту: бэкап ИБ «{ib_name}»{size_info} не завершился за {timeout_min} мин\n"
            f"   → Проверьте: нет ли запроса пароля при sudo/psql?\n"
            f"   → Для очень больших ИБ увеличьте BACKUP_TIMEOUT_MINUTES_PER_GB в конфигурации"
        )

    return {
        "success": result["success"],
        "ib_name": ib_name,  # ← КРИТИЧЕСКИ ВАЖНО: сохраняем правильное имя ИБ
        "format": format_type,
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "returncode": result["returncode"]
    }


def backup_multiple(ib_list: List[str], format_type: str, dry_run: bool = False) -> List[Dict[str, any]]:
    """
    Создать бэкапы для списка информационных баз (последовательно)
    """
    results = []
    for ib_name in ib_list:
        results.append(backup_ib(ib_name, format_type, dry_run))
    return results