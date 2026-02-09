"""
storage_service.py — бизнес-логика мониторинга хранилища резервных копий
Отвечает за агрегацию данных из движков уровня 0 и расчёт метрик.
"""
import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
from core.config import BACKUP_ROOT, load_ib_list


class StorageMonitor:
    """Сервис мониторинга хранилища бэкапов"""
    
    def __init__(self):
        self.backup_root = BACKUP_ROOT
        self.ib_list = load_ib_list()

    def _run_engine(self, script_name: str, args: List[str] = None) -> str:
        """Универсальный запуск движка уровня 0 через core.engine.run_engine"""
        try:
            from core.engine import run_engine
            cmd = [script_name]
            if args:
                cmd.extend(args)
            result = run_engine(script_name, args or [], user="usr1cv8")
            stdout = result["stdout"]
            stderr = result["stderr"]
            returncode = result["returncode"]
            if returncode != 0:
                raise RuntimeError(f"{script_name} failed: {stderr or stdout}")
            return stdout
        except ImportError:
            # Fallback для тестирования без полной структуры
            script_path = Path("/opt/1cv8/scripts/engines") / script_name
            if not script_path.exists():
                raise FileNotFoundError(f"Engine script not found: {script_path}")
            import subprocess
            cmd = [str(script_path)]
            if args:
                cmd.extend(args)
            result = subprocess.run(cmd, capture_output=True, text=True, cwd="/opt/1cv8/scripts")
            if result.returncode != 0:
                raise RuntimeError(f"{script_name} failed: {result.stderr or result.stdout}")
            return result.stdout
    
    def get_backups_list(self) -> List[Dict[str, Any]]:
        """Получить список всех бэкапов через list_backups.sh (TSV формат с Unix timestamp)"""
        output = self._run_engine("list_backups.sh", ["--path", str(self.backup_root)])
        backups = []
        lines = [l.strip() for l in output.strip().split("\n") if l.strip()]
        if not lines:
            return backups
        
        # Пропускаем заголовок
        for line in lines[1:]:
            if "\t" not in line:
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            try:
                ib_name = parts[0].strip()
                timestamp = int(parts[1].strip())  # Unix timestamp (уже число!)
                file_type = parts[2].strip()
                size_bytes = int(parts[3].strip())
                path = parts[4].strip() if len(parts) > 4 else ""
                
                backups.append({
                    "ib_name": ib_name,
                    "timestamp": timestamp,
                    "file_type": file_type,
                    "size_bytes": size_bytes,
                    "path": path
                })
            except (ValueError, IndexError):
                continue  # Пропускаем некорректные строки
        return backups
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """Получить статистику использования диска через disk_usage.sh (ключ=значение формат)"""
        output = self._run_engine("disk_usage.sh", ["--path", str(self.backup_root)])
        data = {}
        for line in output.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                try:
                    data[key] = int(value)
                except ValueError:
                    data[key] = value.strip()
        # Конвертируем кБ в ГБ для отображения
        if "total_kb" in data:
            data["total_gb"] = data["total_kb"] / (1024**2)
        if "used_kb" in data:
            data["used_gb"] = data["used_kb"] / (1024**2)
        if "free_kb" in data:
            data["free_gb"] = data["free_kb"] / (1024**2)
        return data   
    
    def get_stats(self) -> List[Dict[str, Any]]:
        """Получить агрегированную статистику по ИБ через count_backups.sh"""
        output = self._run_engine("count_backups.sh", ["--path", str(self.backup_root)])
        stats = []
        for line in output.strip().split("\n"):
            if not line.strip() or line.startswith("ИБ") or "\t" not in line:
                continue
            parts = line.strip().split("\t")
            if len(parts) < 3:
                continue
            try:
                ib_name = parts[0].strip()
                total_files = int(parts[1].strip())
                total_size_bytes = int(parts[2].strip())
                stats.append({
                    "ib_name": ib_name,
                    "total_files": total_files,
                    "total_size_bytes": total_size_bytes
                })
            except Exception as e:
                continue
        return stats
    
    def validate_storage(self) -> Dict[str, Any]:
        """Запустить валидацию хранилища через validate.sh"""
        try:
            output = self._run_engine("validate.sh", ["--path", str(self.backup_root)])
            errors = []
            warnings = []
            for line in output.strip().split("\n"):
                line = line.strip()
                if line.startswith("ERROR:") or line.startswith("❌"):
                    errors.append(line.replace("ERROR:", "").replace("❌", "").strip())
                elif line.startswith("WARNING:") or line.startswith("⚠️"):
                    warnings.append(line.replace("WARNING:", "").replace("⚠️", "").strip())
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "error_count": len(errors),
                "warnings": warnings,
                "warning_count": len(warnings)
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Ошибка запуска валидации: {str(e)}"],
                "error_count": 1,
                "warnings": [],
                "warning_count": 0
            }
    
    def calculate_growth_rate(self, backups: List[Dict[str, Any]], days: int = 7) -> float:
        """Рассчитать средний темп роста хранилища (ГБ/день) за последние N дней"""
        if not backups:
            return 0.0
        
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_ts = int(cutoff.timestamp())
        
        recent_backups = [b for b in backups if b["timestamp"] >= cutoff_ts]
        if len(recent_backups) < 2:
            return 0.0
        
        # Сортируем по времени
        recent_backups.sort(key=lambda x: x["timestamp"])
        
        # Берём первый и последний бэкап за период
        first = recent_backups[0]
        last = recent_backups[-1]
        
        size_diff_gb = (last["size_bytes"] - first["size_bytes"]) / (1024**3)
        time_diff_days = (last["timestamp"] - first["timestamp"]) / 86400.0
        
        if time_diff_days <= 0:
            return 0.0
        
        return max(0.0, size_diff_gb / time_diff_days)
    
    def get_full_report(self, ib_name: str = None) -> Dict[str, Any]:
        """Получить полный отчёт по хранилищу (все метрики)"""
        try:
            disk = self.get_disk_usage()
        except Exception as e:
            disk = {"error": f"Ошибка получения диска: {str(e)}"}
        
        try:
            all_backups = self.get_backups_list()
            if ib_name:
                all_backups = [b for b in all_backups if b["ib_name"] == ib_name]
        except Exception as e:
            all_backups = []
        
        try:
            stats = self.get_stats()
            if ib_name:
                stats = [s for s in stats if s["ib_name"] == ib_name]
        except Exception as e:
            stats = []
        
        try:
            validation = self.validate_storage()
        except Exception as e:
            validation = {
                "valid": False,
                "errors": [f"Ошибка валидации: {str(e)}"],
                "error_count": 1,
                "warnings": [],
                "warning_count": 0
            }
        
        try:
            growth_rate = self.calculate_growth_rate(all_backups)
        except Exception as e:
            growth_rate = 0.0
        
        return {
            "backup_root": str(self.backup_root),
            "disk": disk,
            "backups": all_backups,
            "stats": stats,
            "validation": validation,
            "growth_rate_gb_per_day": growth_rate,
            "timestamp": int(datetime.now().timestamp())
        }