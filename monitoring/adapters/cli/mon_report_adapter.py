#!/usr/bin/env python3
"""ib1c mon report — Отчёт по потреблению ресурсов"""

import argparse, sqlite3, sys
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path("/opt/1cv8/scripts/monitoring/data/monitoring.db")

def main(args):
    parser = argparse.ArgumentParser(description="Отчёт по ресурсам 1С")
    parser.add_argument("--user", type=str, help="Фильтр по пользователю")
    parser.add_argument("--days", type=int, default=7, help="Период в днях (по умолчанию 7)")
    parser.add_argument("--format", choices=["table", "csv"], default="table", help="Формат вывода")
    parsed = parser.parse_args(args)
    
    if not DB_PATH.exists():
        print("❌ База данных не найдена")
        return 1
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    date_from = (datetime.now() - timedelta(days=parsed.days)).strftime("%Y-%m-%d")
    
    query = """SELECT user_name, COUNT(DISTINCT DATE(recorded_at)) as days_active,
        SUM(cpu_time_total) / 1000000 as cpu_seconds,
        SUM(memory_total) / 1024 / 1024 / 1024 as memory_gb,
        SUM(duration_all) / 60 as session_minutes
        FROM sessions WHERE DATE(recorded_at) >= ?"""
    params = [date_from]
    
    if parsed.user:
        query += " AND user_name = ?"
        params.append(parsed.user)
    
    query += " GROUP BY user_name ORDER BY cpu_seconds DESC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    if parsed.format == "csv":
        print("user_name,days_active,cpu_seconds,memory_gb,session_minutes")
        for row in rows:
            print(f"{row[0]},{row[1]},{row[2]:.2f},{row[3]:.2f},{row[4]:.0f}")
    else:
        print(f"\n📊 Отчёт за последние {parsed.days} дн. (с {date_from})\n")
        print(f"{'Пользователь':<25} {'Дней':<6} {'CPU (сек)':<12} {'RAM (ГБ)':<10} {'Время (мин)':<12}")
        print("-" * 70)
        for row in rows:
            print(f"{row[0]:<25} {row[1]:<6} {row[2]:<12.2f} {row[3]:<10.2f} {row[4]:<12.0f}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main(args))
