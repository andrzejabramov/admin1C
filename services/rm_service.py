# Сервис удаления бэкапов
from adapters.bash_adapter import BashAdapter

class RmService:
    def __init__(self):
        self.bash = BashAdapter()
    
    def remove_backup(self, ib_name: str, timestamp: str = None, dry_run: bool = False):
        cmd = ['./rm.sh', '--ib', ib_name]
        if timestamp: cmd += ['--timestamp', timestamp]
        if dry_run: cmd.append('--dry-run')
        return self.bash.execute(cmd)

