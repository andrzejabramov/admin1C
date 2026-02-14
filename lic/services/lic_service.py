from pathlib import Path
from core.engine import run_engine
from typing import List, Dict, Any, Optional
import glob

class LicenseMonitor:
    """Сервис мониторинга лицензий 1С"""
    
    def __init__(self):
        from core.config import Config
        self.config = Config.load()
        self.license_dir = Path("/var/1C/licenses")

    def _run_engine(self, script_name: str, args: List[str] = None) -> str:
        """Универсальный запуск движка уровня 0 через core.engine.run_engine"""
        try:
            return run_engine(
                script_path=f"lic/engines/{script_name}",
                args=args or [],
                user="usr1cv8",
                capture_output=True
            )["stdout"]
        except Exception as e:
            raise RuntimeError(f"Ошибка запуска {script_name}: {str(e)}") from e

    def get_license_list(self) -> List[Dict[str, str]]:
        """Получить список лицензий через движок license_list.sh (TSV формат)"""
        output = self._run_engine("license_list.sh")
        licenses = []
        for line in output.strip().split("\n"):
            if not line.strip() or line.startswith("regnum"):
                continue
            parts = [p.strip() for p in line.split("\t")]
            if len(parts) >= 5:
                licenses.append({
                    "regnum": parts[0],
                    "filename": parts[1],
                    "type": parts[2],
                    "users": parts[3],
                    "status": parts[4]
                })
        return licenses

    def get_license_info(self, regnum: str) -> Optional[Dict[str, str]]:
        """Получить детали лицензии через движок license_detail.sh"""
        try:
            output = self._run_engine("license_detail.sh", [regnum.strip()])
            info = {}
            for line in output.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    info[key.strip()] = value.strip()
            return info if info else None
        except Exception:
            return None

    def get_monitoring(self) -> Dict[str, Any]:
        """Получить данные мониторинга через движок monitor.sh"""
        output = self._run_engine("monitor.sh")
        stats = {}
        for line in output.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                stats[key] = value
        return stats

    def create_backup(self) -> Dict[str, str]:
        """Создать резервную копию лицензий"""
        output = self._run_engine("backup.sh")
        backup_path = output.split("BACKUP_PATH=")[1].split("\n")[0]
        backup_count = output.split("BACKUP_COUNT=")[1].split("\n")[0]
        
        return {
            "backup_path": backup_path,
            "backup_count": backup_count,
            "timestamp": Path(backup_path).name
        }

    def get_full_report(self) -> Dict[str, Any]:
        """Получить полный отчёт по лицензиям"""
        licenses = self.get_license_list()
        monitoring = self.get_monitoring()
        
        total_users = 0
        total_servers = 0
        for lic in licenses:
            users = int(lic["users"])
            if "сервер" in lic["type"].lower():
                total_servers += 1
            else:
                total_users += users
        
        return {
            "total_licenses": len(licenses),
            "total_users": total_users,
            "total_servers": total_servers,
            "active_sessions": monitoring.get("ACTIVE_SESSIONS", "0"),
            "licenses": licenses
        }
