#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1С Session Collector — сбор метрик сессий в SQLite"""

import subprocess, re, sqlite3, json, sys, os, signal, time
from datetime import datetime
from pathlib import Path

# Пути
SCRIPT_DIR = Path(__file__).resolve().parent  # .../services/bin
SERVICES_DIR = SCRIPT_DIR.parent              # .../services
MONITORING_DIR = SERVICES_DIR.parent          # .../monitoring

CONFIG_FILE = SERVICES_DIR / "config" / "config.json"
DB_PATH = MONITORING_DIR / "data" / "monitoring.db"
LOG_PATH = MONITORING_DIR / "logs" / "collector.log"
PID_FILE = MONITORING_DIR / "data" / "collector.pid"

DEFAULT_CONFIG = {
    "rac_path": "/opt/1cv8/x86_64/8.3.27.1989/rac",
    "cluster_uuid": "60191967-9ef6-4a40-9d45-321bc9ca9e2f",
    "ras_server": "localhost:1545",
    "interval_seconds": 30
}

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f: f.write(line + "\n")
    except: pass

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        DEFAULT_CONFIG.update(cfg)
    return DEFAULT_CONFIG

def init_db():
    # Проверка пути перед подключением
    print(f"DB_PATH: {DB_PATH}")
    print(f"Real path: {DB_PATH.resolve()}")
    print(f"Parent exists: {DB_PATH.parent.exists()}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        session_uuid TEXT NOT NULL, session_id INTEGER, user_name TEXT,
        infobase_uuid TEXT, host TEXT, client_ip TEXT, app_id TEXT,
        started_at TEXT, last_active_at TEXT, is_hibernated INTEGER,
        cpu_time_total INTEGER, cpu_time_last_5min INTEGER,
        memory_total INTEGER, memory_last_5min INTEGER,
        duration_all INTEGER, duration_last_5min INTEGER,
        bytes_all INTEGER, bytes_last_5min INTEGER,
        calls_all INTEGER, calls_last_5min INTEGER,
        dbms_bytes_all INTEGER, dbms_bytes_last_5min INTEGER,
        read_total INTEGER, write_total INTEGER,
        UNIQUE(recorded_at, session_uuid))""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_rec ON sessions(recorded_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_usr ON sessions(user_name)")
    conn.commit()
    conn.close()
    log("БД инициализирована")

def save_session(conn, s, recorded_at):
    def si(v, d=0):
        try: return int(v) if v else d
        except: return d
    def sb(v): return 1 if (v and v.lower() == 'yes') else 0
    c = conn.cursor()
    c.execute("""INSERT OR IGNORE INTO sessions (
        recorded_at, session_uuid, session_id, user_name, infobase_uuid,
        host, client_ip, app_id, started_at, last_active_at, is_hibernated,
        cpu_time_total, cpu_time_last_5min, memory_total, memory_last_5min,
        duration_all, duration_last_5min, bytes_all, bytes_last_5min,
        calls_all, calls_last_5min, dbms_bytes_all, dbms_bytes_last_5min,
        read_total, write_total) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        recorded_at, s.get('session'), si(s.get('session-id')),
        s.get('user-name', 'Unknown'), s.get('infobase'),
        s.get('host'), s.get('client-ip'), s.get('app-id'),
        s.get('started-at'), s.get('last-active-at'), sb(s.get('hibernate')),
        si(s.get('cpu-time-total')), si(s.get('cpu-time-last-5min')),
        si(s.get('memory-total')), si(s.get('memory-last-5min')),
        si(s.get('duration-all')), si(s.get('duration-last-5min')),
        si(s.get('bytes-all')), si(s.get('bytes-last-5min')),
        si(s.get('calls-all')), si(s.get('calls-last-5min')),
        si(s.get('dbms-bytes-all')), si(s.get('dbms-bytes-last-5min')),
        si(s.get('read-total')), si(s.get('write-total'))))
    conn.commit()

def parse_rac(out):
    sessions, cur = [], {}
    for line in out.strip().split('\n'):
        if not line.strip(): continue
        if line.startswith('session') and ':' in line and 'session-id' not in line:
            if cur: sessions.append(cur)
            cur = {}
        m = re.match(r'^(\S+)\s*:\s*(.*)$', line)
        if m:
            k, v = m.group(1).strip(), m.group(2).strip()
            if v.startswith('"') and v.endswith('"'): v = v[1:-1]
            cur[k] = v
    if cur: sessions.append(cur)
    return sessions

def collect_sessions(cfg):
    cmd = [cfg["rac_path"], "session", "list", cfg["ras_server"], f"--cluster={cfg['cluster_uuid']}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            log(f"rac error: {r.stderr}", "ERROR")
            return []
        return parse_rac(r.stdout)
    except Exception as e:
        log(f"Ошибка сбора: {e}", "ERROR")
        return []

running = True
def sig_h(sig, frame):
    global running
    log("Сигнал остановки")
    running = False

def main():
    global running
    signal.signal(signal.SIGTERM, sig_h)
    signal.signal(signal.SIGINT, sig_h)
    cfg = load_config()
    log(f"Запуск. Интервал: {cfg['interval_seconds']} сек, Кластер: {cfg['cluster_uuid']}")
    init_db()
    with open(PID_FILE, "w") as f: f.write(str(os.getpid()))
    while running:
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log(f"Сбор [{ts}]...")
            sessions = collect_sessions(cfg)
            log(f"Найдено сессий: {len(sessions)}")
            if sessions:
                conn = sqlite3.connect(DB_PATH)
                try:
                    for s in sessions: save_session(conn, s, ts)
                    log(f"✅ Записано {len(sessions)} сессий")
                finally: conn.close()
        except Exception as e:
            log(f"Ошибка в цикле: {e}", "ERROR")
        for _ in range(cfg['interval_seconds']):
            if not running: break
            time.sleep(1)
    if PID_FILE.exists(): PID_FILE.unlink()
    log("Остановлен")

if __name__ == "__main__":
    main()
