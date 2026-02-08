# core/engine.py
"""
Универсальный запуск bash-скриптов из engines/
Поддерживает как захват вывода (для парсинга), так и потоковый вывод (для прогресса).
"""

from pathlib import Path
import subprocess
import sys
from typing import List, Dict, Optional

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "engines"


def run_engine(
    script_name: str,
    args: List[str],
    timeout: int = 300,
    user: Optional[str] = None,
    capture_output: bool = True
) -> Dict[str, any]:
    """
    Выполнить bash-скрипт из engines/
    
    Args:
        script_name: имя скрипта (например, 'backup.sh')
        args: аргументы для скрипта
        timeout: таймаут выполнения в секундах
        user: пользователь для выполнения (если требуется)
        capture_output: True — захватить вывод для парсинга
                        False — проксировать вывод напрямую в терминал (для прогресса)
    
    Returns:
        dict с ключами: returncode, stdout, stderr, success
    """
    script_path = SCRIPTS_DIR / script_name
    
    if not script_path.exists():
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Скрипт не найден: {script_path}"
        }
    
    # Формирование команды
    cmd = []
    if user:
        cmd.extend(["sudo", "-u", user])
    cmd.extend([str(script_path)] + args)
    
    try:
        if capture_output:
            # Режим захвата вывода (для парсинга: disk_usage, list_backups)
            result = subprocess.run(
                cmd,
                cwd=SCRIPTS_DIR,
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
            # Проксируем напрямую в терминал — pv сможет отрисовать прогресс
            process = subprocess.Popen(
                cmd,
                cwd=SCRIPTS_DIR,
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
                return {
                    "success": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"Timeout expired after {timeout}s"
                }
    
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e)
        }