#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Metrics API — JSON API для дашборда (только для доверенного хоста)"""

import json, sqlite3, shutil, sys
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

DB_PATH = Path("/opt/1cv8/scripts/monitoring/data/monitoring.db")
API_PORT = 8001

# 🔐 ДОБАВЬ СЮДА IP твоего Ubuntu 22 сервера
TRUSTED_CLIENT = "10.129.0.25"  # <--- ЗАМЕНИ НА РЕАЛЬНЫЙ IP

def get_db():
    if not DB_PATH.exists(): return None
    return sqlite3.connect(DB_PATH)

def get_summary(days=7):
    conn = get_db()
    if not conn: return None
    cur = conn.cursor()
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    cur.execute("""SELECT COUNT(*), COUNT(DISTINCT user_name), 
        SUM(cpu_time_total)/1000000, SUM(memory_total)/1024/1024/1024
        FROM sessions WHERE DATE(recorded_at) >= ?""", (date_from,))
    row = cur.fetchone()
    conn.close()
    return {"records": row[0], "users": row[1], "cpu_sec": round(row[2] or 0, 2), "memory_gb": round(row[3] or 0, 2)} if row else None

def get_user_load(days=7, user_filter=None):
    conn = get_db()
    if not conn: return []
    cur = conn.cursor()
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    query = """SELECT user_name, SUM(cpu_time_total)/1000000, SUM(memory_total)/1024/1024/1024, COUNT(*)
        FROM sessions WHERE DATE(recorded_at) >= ?"""
    params = [date_from]
    if user_filter:
        query += " AND user_name = ?"
        params.append(user_filter)
    query += " GROUP BY user_name ORDER BY cpu_time_total DESC"
    cur.execute(query, params)
    result = [{"user": r[0], "cpu_sec": round(r[1] or 0, 2), "memory_gb": round(r[2] or 0, 2), "sessions": r[3]} for r in cur.fetchall()]
    conn.close()
    return result

def get_daily_stats(days=7):
    conn = get_db()
    if not conn: return []
    cur = conn.cursor()
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    cur.execute("""SELECT DATE(recorded_at), COUNT(*), COUNT(DISTINCT user_name), SUM(cpu_time_total)/1000000
        FROM sessions WHERE DATE(recorded_at) >= ? GROUP BY DATE(recorded_at) ORDER BY DATE(recorded_at)""", (date_from,))
    result = [{"date": r[0], "sessions": r[1], "users": r[2], "cpu_sec": round(r[3] or 0, 2)} for r in cur.fetchall()]
    conn.close()
    return result

def get_disk_metrics():
    metrics = []
    for path, name in [("/", "vda1"), ("/var/backups/1c", "vdb")]:
        try:
            u = shutil.disk_usage(path)
            metrics.append({"disk": name, "path": path, "used_gb": round(u.used/1024**3, 2), 
                           "free_gb": round(u.free/1024**3, 2), "percent": round((u.used/u.total)*100, 1)})
        except: pass
    return metrics

class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.client_address[0]} - {args[0]}")
    
    def do_GET(self):
        # 🔐 Проверка: только доверенный хост
        if self.client_address[0] != TRUSTED_CLIENT and not self.client_address[0].startswith("127."):
            print(f"❌ Запрос отклонён: {self.client_address[0]}")
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'Forbidden')
            return
        
        if self.path.startswith('/api/metrics'):
            # Парсим параметры
            from urllib.parse import urlparse, parse_qs
            params = parse_qs(urlparse(self.path).query)
            days = int(params.get('days', [7])[0])
            user = params.get('user', [None])[0]
            
            data = {
                "timestamp": datetime.now().isoformat(),
                "period_days": days,
                "summary": get_summary(days),
                "user_load": get_user_load(days, user),
                "daily_stats": get_daily_stats(days),
                "disk_metrics": get_disk_metrics()
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            print(f"✅ Отправлено {len(json.dumps(data))} байт")
        
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        
        else:
            self.send_response(404)
            self.end_headers()

def main():
    print(f"🔐 Metrics API запущен на порту {API_PORT}")
    print(f"   Доверенный хост: {TRUSTED_CLIENT}")
    print(f"   Эндпоинт: http://serv1:{API_PORT}/api/metrics?days=7")
    
    server = HTTPServer(('0.0.0.0', API_PORT), APIHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 API остановлен")
        server.shutdown()

if __name__ == "__main__":
    main()
