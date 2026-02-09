#!/usr/bin/env python3
"""
storage.py — мониторинг хранилища бэкапов 1С
Фильтрует артефакты: системные директории (lost+found), виртуальные ИБ (all), опечатки
"""

import sys
import argparse
import shutil
from datetime import datetime
from pathlib import Path
from utils.datetime_utils import machine_to_human

BACKUP_ROOT = Path("/var/backups/1c")

# Чёрный список: системные и виртуальные директории
IB_BLACKLIST = {
    "all", "ALL", "All",           # Виртуальная ИБ из скриптов
    "apral_2025",                  # Опечатка artel_2025
    "lost+found", ".snapshot",     # Системные директории
    ".", ".."                      # Специальные ссылки
}

def get_backups_for_ib(ib_name: str):
    """Получить список бэкапов ИБ с метаданными"""
    ib_dir = BACKUP_ROOT / ib_name
    if not ib_dir.exists():
        return []
    
    backups = []
    try:
        for entry in sorted(ib_dir.glob("20[0-9][0-9][01][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9]"), reverse=True):
            if entry.is_dir():
                total_size = sum(f.stat().st_size for f in entry.glob("*") if f.is_file())
                backups.append({
                    "timestamp": entry.name,
                    "human_time": machine_to_human(entry.name),
                    "size_bytes": total_size,
                    "path": entry
                })
    except PermissionError:
        pass  # Игнорируем директории без прав
    return backups

def is_valid_ib(ib_name: str) -> bool:
    """Проверить, является ли имя ИБ реальной базой 1С"""
    if ib_name in IB_BLACKLIST:
        return False
    if ib_name.startswith(".") and ib_name not in {".", ".."}:
        return False
    
    ib_dir = BACKUP_ROOT / ib_name
    if not ib_dir.is_dir():
        return False
    
    try:
        next(ib_dir.iterdir(), None)
    except PermissionError:
        return False
    
    valid_backups = list(ib_dir.glob("20[0-9][0-9][01][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9]"))
    if not valid_backups:
        has_files = any(f for f in ib_dir.iterdir() if f.is_file())
        return has_files
    
    return True

def format_size(bytes_size: int) -> str:
    if bytes_size == 0:
        return "0B"
    for unit in ["B", "K", "M", "G", "T"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f}P"

def format_age(timestamp: str) -> str:
    try:
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        age = datetime.now() - dt
        if age.days == 0:
            return "сегодня"
        elif age.days == 1:
            return "1 день"
        elif age.days < 7:
            return f"{age.days} дня"
        elif age.days < 30:
            weeks = age.days // 7
            return f"{weeks} нед."
        else:
            months = age.days // 30
            return f"{months} мес."
    except:
        return ""

def print_disk_usage():
    try:
        total, used, free = shutil.disk_usage(BACKUP_ROOT)
        pct = used / total * 100
        print(f"\n📁 Хранилище бэкапов: {BACKUP_ROOT}\n")
        print("┌────────────────┬──────────────┬────────────────────┬────────────────┐")
        print("│ Диск           │ Всего        │ Занято             │ Свободно       │")
        print("├────────────────┼──────────────┼────────────────────┼────────────────┤")
        used_str = f"{format_size(used)} ({pct:.0f}%)"
        print(f"│ /dev/vdb       │ {format_size(total):<12} │ {used_str:>18} │ {format_size(free):<14} │")
        print("└────────────────┴──────────────┴────────────────────┴────────────────┘\n")
    except Exception as e:
        print(f"⚠️  Ошибка получения информации о диске: {e}\n")

def print_summary_table(ibs_to_show):
    print("📊 Статистика по ИБ:")
    print("┌──────────────────────────┬─────────────┬──────────────────────────┬────────────────────┬──────────────┐")
    print("│ ИБ                       │ Бэкапов     │ Последний                │ Последний размер   │ Всего        │")
    print("├──────────────────────────┼─────────────┼──────────────────────────┼────────────────────┼──────────────┤")
    
    for ib_name in sorted(ibs_to_show):
        backups = get_backups_for_ib(ib_name)
        if not backups:
            continue
        
        last = backups[0]
        total_size = sum(b["size_bytes"] for b in backups)
        last_human = machine_to_human(last["timestamp"])
        
        print(f"│ {ib_name:<24} │ {len(backups):<11} │ {last_human:<24} │ {format_size(last['size_bytes']):<18} │ {format_size(total_size):<12} │")
    
    print("└──────────────────────────┴─────────────┴──────────────────────────┴────────────────────┴──────────────┘\n")

def print_detailed_backups(ib_name):
    backups = get_backups_for_ib(ib_name)
    if not backups:
        print(f"⚠️  ИБ '{ib_name}' не найдена или нет бэкапов\n")
        return 1
    
    print(f"📊 Бэкапы ИБ: {ib_name}")
    print("┌──────────────────────┬──────────────┬──────────────────────────┬──────────────┐")
    print("│ Метка (машиночит.)   │ Размер       │ Создано                  │ Возраст      │")
    print("├──────────────────────┼──────────────┼──────────────────────────┼──────────────┤")
    
    for b in backups:
        ts = b['timestamp']
        size = format_size(b['size_bytes'])
        human = b['human_time']
        age = format_age(ts)
        print(f"│ {ts:<20} │ {size:<12} │ {human:<24} │ {age:<12} │")
    
    print("└──────────────────────┴──────────────┴──────────────────────────┴──────────────┘\n")
    
    total_size = sum(b["size_bytes"] for b in backups)
    print(f"ℹ️  Всего: {len(backups)} бэкап(ов), общий размер: {format_size(total_size)}\n")
    return 0

def main(args=None):
    parser = argparse.ArgumentParser(description="Мониторинг хранилища бэкапов 1С")
    parser.add_argument("--ib", help="Показать детальный список бэкапов для указанной ИБ")
    parsed = parser.parse_args(args)
    
    try:
        all_entries = [d.name for d in BACKUP_ROOT.glob("*") if d.is_dir()]
        all_ibs = [name for name in all_entries if is_valid_ib(name)]
    except Exception as e:
        print(f"❌ Ошибка чтения каталога бэкапов: {e}", file=sys.stderr)
        return 1
    
    print_disk_usage()
    
    if parsed.ib:
        if parsed.ib not in all_ibs:
            print(f"❌ ИБ '{parsed.ib}' не найдена в {BACKUP_ROOT}", file=sys.stderr)
            print(f"   Доступные ИБ: {', '.join(sorted(all_ibs))}", file=sys.stderr)
            return 1
        return print_detailed_backups(parsed.ib)
    
    if not all_ibs:
        print("⚠️  Нет валидных ИБ для отображения\n")
        return 0
    
    print_summary_table(all_ibs)
    return 0

if __name__ == "__main__":
    sys.exit(main())
