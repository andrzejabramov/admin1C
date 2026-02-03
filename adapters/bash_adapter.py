# Адаптер для вызова bash-скриптов
import subprocess
from pathlib import Path

class BashAdapter:
    def __init__(self, scripts_dir='/opt/1cv8/scripts/engines'):
        self.scripts_dir = Path(scripts_dir)
    
    def execute(self, cmd: list, timeout=300):
        try:
            result = subprocess.run(
                cmd,
                cwd=self.scripts_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except subprocess.TimeoutExpired:
            return {'returncode': -1, 'stdout': '', 'stderr': 'Timeout'}

