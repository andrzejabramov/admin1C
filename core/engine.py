# core/engine.py
"""
Универсальный запуск bash-скриптов из проекта
Поддерживает как глобальные скрипты (/engines/), так и доменные (/домен/engines/)
"""

from pathlib import Path
import subprocess
import sys
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_engine(
    script_path: str,
    args: List[str],
    timeout: int = 300,
    user: Optional[str] = None,
    capture_output: bool = True
) -> Dict[str, any]:
    """
    Выполнить bash-скрипт из проекта
    
    Args:
        script_path: Относительный путь от корня проекта (например, "rm/engines/rm.sh")
        args: аргументы для скрипта
        timeout: таймаут выполнения в секундах
        user: пользователь для выполнения (если требуется)
        capture_output: True — захватить вывод для парсинга
                        False — проксировать вывод напрямую в терминал (для прогресса)
    
    Returns:
        dict с ключами: returncode, stdout, stderr, success
    """
    full_script_path = PROJECT_ROOT / script_path
    
    if not full_script_path.exists():
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Скрипт не найден: {full_script_path}"
        }
    
    # Формирование команды
    cmd = []
    if user:
        cmd.extend(["sudo", "-u", user])
    cmd.extend([str(full_script_path)] + args)
    
    try:
        if capture_output:
            # Режим захвата вывода (для парсинга: disk_usage, list_backups)
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        else:
            # Режим потокового вывода (для прогресса: backup, rm больших файлов)
            if user:
                cmd_str = ' '.join(cmd)
                cmd_wrapper = ['script', '-q', '-c', cmd_str, '/dev/null']
                process = subprocess.Popen(
                    cmd_wrapper,
                    cwd=PROJECT_ROOT,
                    stdout=sys.stdout,
                    stderr=sys.stderr
                )
            else:
                process = subprocess.Popen(
                    cmd,
                    cwd=PROJECT_ROOT,
                    stdout=sys.stdout,
                    stderr=sys.stderr
                )
            try:
                process.wait(timeout=timeout)
                return {
                    "success": process.returncode == 0,
                    "returncode": process.returncode,
                    "stdout": "",
                    "stderr": ""
                }
            except subprocess.TimeoutExpired:
                process.kill()
                from core.exceptions import BackupTimeoutError
                raise BackupTimeoutError(
                    ib_name=script_path.replace('.sh', ''),
                    timeout_seconds=timeout
                )
    
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e)
        }
