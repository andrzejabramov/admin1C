# core/engine.py
from pathlib import Path
import subprocess
from typing import List, Dict, Optional

SCRIPTS_DIR = Path("/opt/1cv8/scripts/engines")

def run_engine(
    script_name: str,
    args: List[str],
    timeout: int = 300,
    user: Optional[str] = None
) -> Dict[str, any]:
    """Универсальный запуск bash-скрипта из engines/"""
    script_path = SCRIPTS_DIR / script_name
    
    if not script_path.exists():
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Скрипт не найден: {script_path}"
        }
    
    cmd = []
    if user:
        cmd.extend(["sudo", "-u", user])
    cmd.extend([str(script_path)] + args)
    
    try:
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
    except subprocess.TimeoutExpired:
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