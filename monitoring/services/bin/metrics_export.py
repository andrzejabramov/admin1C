#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Metrics Export — выгрузка метрик из SQLite в JSON"""

import json, sqlite3, sys
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("/opt/1cv8/scripts/monitoring/data/monitoring.db")

def get_db_connection():
    if not DB_PATH.exists():
        print(json.dumps({"error": "База данных не найдена"}))
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def get_summary(conn, days=7):
    """Общая сводка за период"""
    cur = conn.cursor()
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    cur.execute("""SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT user_name) as unique_users,
        COUNT(DISTINCT DATE(recorded_at)) as active_days,
        SUM(cpu_time_total) / 1000000 as total_cpu_sec,
        SUM(memory_total) / 1024 / 1024 / 1024 as total_memory_gb,
        MIN(recorded_at) as first_record,
        MAX(recorded_at) as last_record
        FROM sessions WHERE DATE(recorded_at) >= ?""", (date_from,))
    
    row = cur.fetchone()
    return {
        "period_days": days,
        "total_records": row[0] or 0,
        "unique_users": row[1] or 0,
        "active_days": row[2] or 0,
        "total_cpu_sec": round(row[3] or 0, 2),
        "total_memory_gb": round(row[4] or 0, 2),
        "first_record": row[5],
        "last_record": row[6]
    }

def get_user_load(conn, days=7):
    """Нагрузка по пользователям (для консолидированного графика)"""
    cur = conn.cursor()
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    cur.execute("""SELECT user_name, 
        COUNT(*) as sessions_count,
        SUM(cpu_time_total) / 1000000 as cpu_sec,
        SUM(memory_total) / 1024 / 1024 / 1024 as memory_gb,
        SUM(duration_all) / 60 as total_minutes
        FROM sessions WHERE DATE(recorded_at) >= ?
        GROUP BY user_name ORDER BY cpu_sec DESC""", (date_from,))
    
    return [{"user": row[0], "sessions": row[1], "cpu_sec": round(row[2], 2), 
             "memory_gb": round(row[3], 2), "total_minutes": round(row[4], 0)} 
            for row in cur.fetchall()]

def get_daily_stats(conn, days=7):
    """Статистика по дням (для временных графиков)"""
    cur = conn.cursor()
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    cur.execute("""SELECT DATE(recorded_at) as day,
        COUNT(*) as sessions,
        COUNT(DISTINCT user_name) as users,
        SUM(cpu_time_total) / 1000000 as cpu_sec,
        SUM(memory_total) / 1024 / 1024 / 1024 as memory_gb
        FROM sessions WHERE DATE(recorded_at) >= ?
        GROUP BY DATE(recorded_at) ORDER BY day""", (date_from,))
    
    return [{"date": row[0], "sessions": row[1], "users": row[2], 
             "cpu_sec": round(row[3], 2), "memory_gb": round(row[4], 2)} 
            for row in cur.fetchall()]

def get_top_users(conn, days=7, limit=10):
    """Топ пользователей по CPU"""
    cur = conn.cursor()
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    cur.execute("""SELECT user_name, 
        SUM(cpu_time_total) / 1000000 as cpu_sec,
        SUM(memory_total) / 1024 / 1024 / 1024 as memory_gb,
        COUNT(*) as sessions
        FROM sessions WHERE DATE(recorded_at) >= ?
        GROUP BY user_name ORDER BY cpu_sec DESC LIMIT ?""", (date_from, limit))
    
    return [{"rank": i+1, "user": row[0], "cpu_sec": round(row[1], 2), 
             "memory_gb": round(row[2], 2), "sessions": row[3]} 
            for i, row in enumerate(cur.fetchall())]

def get_disk_metrics():
    """Метрики дисков (из последнего запуска disk_monitor)"""
    import shutil
    metrics = []
    for path, name in [("/", "vda1"), ("/var/backups/1c", "vdb")]:
        try:
            u = shutil.disk_usage(path)
            metrics.append({
                "disk": name,
                "path": path,
                "total_gb": round(u.total/1024**3, 2),
                "used_gb": round(u.used/1024**3, 2),
                "free_gb": round(u.free/1024**3, 2),
                "percent": round((u.used/u.total)*100, 1)
            })
        except: pass
    return metrics

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Экспорт метрик мониторинга 1С")
    parser.add_argument("--days", type=int, default=7, help="Период в днях")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Формат вывода")
    parser.add_argument("--metric", choices=["summary", "users", "daily", "top", "disk", "all"], 
                        default="all", help="Тип метрики")
    args = parser.parse_args()
    
    conn = get_db_connection()
    
    result = {"timestamp": datetime.now().isoformat(), "period_days": args.days}
    
    if args.metric in ["summary", "all"]:
        result["summary"] = get_summary(conn, args.days)
    if args.metric in ["users", "all"]:
        result["user_load"] = get_user_load(conn, args.days)
    if args.metric in ["daily", "all"]:
        result["daily_stats"] = get_daily_stats(conn, args.days)
    if args.metric in ["top", "all"]:
        result["top_users"] = get_top_users(conn, args.days)
    if args.metric in ["disk", "all"]:
        result["disk_metrics"] = get_disk_metrics()
    
    conn.close()
    
    if args.format == "csv":
        # Простой CSV для summary
        if "summary" in result:
            s = result["summary"]
            print("metric,value")
            for k, v in s.items(): print(f"{k},{v}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
