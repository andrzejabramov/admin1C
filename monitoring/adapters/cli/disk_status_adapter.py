#!/usr/bin/env python3
"""ib1c disk status — Статус дискового пространства"""

import subprocess, sys
from pathlib import Path

LOG_PATH = Path("/opt/1cv8/scripts/monitoring/logs/disk_monitor.log")

def main(args):
    print("💿 Статус дискового пространства\n")
    
    # df вывод
    r = subprocess.run(["df", "-h", "/", "/var/backups/1c"], capture_output=True, text=True)
    print(r.stdout)
    
    # Статус таймера
    r = subprocess.run(["systemctl", "is-active", "disk-monitor.timer"], capture_output=True, text=True)
    status = "✅ Активен" if r.stdout.strip() == "active" else "❌ Не активен"
    print(f"Мониторинг: {status}")
    
    # Последний запуск таймера
    r = subprocess.run(["systemctl", "list-timers", "disk-monitor.timer", "--no-pager"], capture_output=True, text=True)
    for line in r.stdout.split('\n'):
        if 'disk-monitor.timer' in line:
            print(f"Таймер: {line.strip()}")
    
    # Последние строки лога
    if LOG_PATH.exists():
        print("\n📋 Последние проверки:")
        with open(LOG_PATH, 'r') as f:
            for line in f.readlines()[-5:]:
                print(f"   {line.strip()}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main(args))
