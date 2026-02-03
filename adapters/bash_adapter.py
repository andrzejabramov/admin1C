# Адаптер для вызова bash-скриптов из engines/
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

class BashAdapter:
    """Адаптер для выполнения bash-скриптов"""
    
    def __init__(self, scripts_dir: str = "/opt/1cv8/scripts/engines"):
        self.scripts_dir = Path(scripts_dir)
    
    def execute(
        self,
        script_name: str,
        args: List[str],
        timeout: int = 300,
        user: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Выполнить bash-скрипт
        
        Args:
            script_name: имя скрипта (например, 'rm.sh')
            args: аргументы для скрипта
            timeout: таймаут выполнения в секундах
            user: пользователь для выполнения (если требуется)
        
        Returns:
            dict с ключами: returncode, stdout, stderr, success
        """
        script_path = self.scripts_dir / script_name
        
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
            result = subprocess.run(
                cmd,
                cwd=self.scripts_dir,
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
