#!/usr/bin/env python3
"""ib1c mon status — Статус сборщика сессий 1С"""

import subprocess, sys
from pathlib import Path

DB_PATH = Path("/opt/1cv8/scripts/monitoring/data/monitoring.db")
LOG_PATH = Path("/opt/1cv8/scripts/monitoring/logs/collector.log")

def main(args):
    print("📊 Статус мониторинга сессий 1С\n")
    
    # Статус systemd
    r = subprocess.run(["systemctl", "is-active", "1c-monitoring"], capture_output=True, text=True)
    status = "✅ Активен" if r.stdout.strip() == "active" else "❌ Не активен"
    print(f"Сервис: {status}")
    
    # PID
    r = subprocess.run(["systemctl", "show", "1c-monitoring", "--property=MainPID"], capture_output=True, text=True)
    pid = r.stdout.strip().replace("MainPID=", "")
    if pid and pid != "0":
        print(f"PID: {pid}")
    
    # Статистика из БД
    if DB_PATH.exists():
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        print("\n📈 Статистика:")
        cur.execute("SELECT COUNT(*) FROM sessions")
        print(f"   Всего записей: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(DISTINCT user_name) FROM sessions")
        print(f"   Пользователей: {cur.fetchone()[0]}")
        cur.execute("SELECT recorded_at FROM sessions ORDER BY recorded_at DESC LIMIT 1")
        last = cur.fetchone()
        print(f"   Последняя запись: {last[0] if last else 'нет'}")
        conn.close()
    else:
        print("\n⚠️  База данных не найдена")
    
    # Последние строки лога
    if LOG_PATH.exists():
        print("\n📋 Последние логи:")
        with open(LOG_PATH, 'r') as f:
            for line in f.readlines()[-3:]:
                print(f"   {line.strip()}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main(args))
