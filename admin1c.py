#!/usr/local/bin/python3
"""
admin1c.py — централизованный инструмент администрирования 1С
"""
import subprocess, sys, argparse, os
from pathlib import Path
from datetime import datetime

# admin1c.py — заготовка для интеграции исключений
from core.exceptions import (
    OrchestratorError,
    BackupError,
    RmError,
    NotFoundError,
    PermissionError
)

IB_LIST_PATH = "/opt/1cv8/scripts/ib_list.conf"
BACKUP_SCRIPT = "/opt/1cv8/scripts/engines/backup.sh"
LOG_DIR = "/var/log/1c-admin"

def safe_call(func):
    """Декоратор для централизованной обработки ошибок"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OrchestratorError as e:
            print(f"❌ {e.message}", file=sys.stderr)
            if e.details:
                print(f"   Подробности: {e.details}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"❌ {type(e).__name__}: {str(e)}", file=sys.stderr)
            sys.exit(1)
    return wrapper

class Colors:
    GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"
    BLUE = "\033[94m"; BOLD = "\033[1m"; END = "\033[0m"

def color(text, col):
    return f"{col}{text}{Colors.END}" if sys.stdout.isatty() else text

def load_ib_list(path=IB_LIST_PATH):
    if not Path(path).exists():
        print(color(f"❌ Файл не найден: {path}", Colors.RED)); sys.exit(1)
    with open(path) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def run_backup(ib_name, format_type):
    cmd = ["sudo", "-u", "usr1cv8", BACKUP_SCRIPT, "--ib", ib_name, "--format", format_type]
    try:
        result = subprocess.run(cmd, stdout=None, stderr=None, timeout=3600)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(color(f"\n❌ Таймаут: {ib_name} (>60 мин)", Colors.RED)); return False
    except KeyboardInterrupt:
        print(color(f"\n⚠️ Прервано: {ib_name}", Colors.YELLOW)); raise
    except Exception as e:
        print(color(f"\n❌ Ошибка: {ib_name} — {e}", Colors.RED)); return False

def main():
    parser = argparse.ArgumentParser(description=color("Администрирование 1С", Colors.BOLD))
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup_parser = subparsers.add_parser("backup", help="Создать резервные копии")
    backup_parser.add_argument("--format", choices=["dump", "sql"], required=True)
    group = backup_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ib", nargs="+", metavar="ИБ")
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()

    if args.command == "backup":
        os.makedirs(LOG_DIR, exist_ok=True)
        ib_list = args.ib if args.ib else load_ib_list()
        if not ib_list: print(color("❌ Список ИБ пуст", Colors.RED)); sys.exit(1)
        
        print(color(f"\n📦 Начало бэкапа {len(ib_list)} ИБ (формат: {args.format})", Colors.BLUE))
        print(color("=" * 70, Colors.BLUE))
        
        success, failed = [], []
        for i, ib in enumerate(ib_list, 1):
            print(color(f"\n[{i}/{len(ib_list)}] 🔄 {ib}", Colors.YELLOW))
            print(color("-" * 70, Colors.BLUE))
            try:
                if run_backup(ib, args.format): success.append(ib)
                else: failed.append(ib)
            except KeyboardInterrupt:
                print(color("\n\n⚠️ Прервано пользователем", Colors.YELLOW)); sys.exit(130)

        print(color("\n" + "=" * 70, Colors.BLUE))
        print(color(f"✅ Успешно: {len(success)}/{len(ib_list)}", Colors.GREEN))
        if failed:
            print(color(f"❌ Ошибки: {len(failed)}", Colors.RED))
            for ib in failed: print(f"   - {ib}")
        print(color("=" * 70, Colors.BLUE))
        sys.exit(0 if not failed else 1)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt:
        print(color("\n\n⚠️ Прервано пользователем", Colors.YELLOW)); sys.exit(130)
