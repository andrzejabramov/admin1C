#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Disk Monitor — проверка места на дисках + email алерты"""

import json, smtplib, shutil, sys, logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SERVICES_DIR = SCRIPT_DIR.parent
MONITORING_DIR = SERVICES_DIR.parent

CONFIG_FILE = SERVICES_DIR / "config" / "disk_monitor.json"
LOG_FILE = MONITORING_DIR / "logs" / "disk_monitor.log"
STATE_FILE = MONITORING_DIR / "data" / "disk_state.json"

DEFAULT_CONFIG = {
    "mount_points": [
        {"path": "/", "name": "vda1 (загрузочный)", "warn_threshold": 75, "critical_threshold": 85},
        {"path": "/var/backups/1c", "name": "vdb (архивы 1С)", "warn_threshold": 80, "critical_threshold": 90}
    ],
    "email": {
        "enabled": False,
        "smtp_server": "smtp.yandex.ru",
        "smtp_port": 465,
        "use_ssl": True,
        "login": "your_email@yandex.ru",
        "password": "your_app_password",
        "recipients": ["your_email@yandex.ru"]
    },
    "cooldown_hours": 24
}

def setup_logging():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler(sys.stdout)])
    return logging.getLogger(__name__)

logger = setup_logging()

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        logger.warning(f"Конфиг не найден: {CONFIG_FILE}")
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
        return DEFAULT_CONFIG.copy()

def get_disk_usage(path):
    try:
        u = shutil.disk_usage(path)
        return {"path": path, "total_gb": round(u.total/1024**3, 2), "used_gb": round(u.used/1024**3, 2),
                "free_gb": round(u.free/1024**3, 2), "percent": round((u.used/u.total)*100, 1),
                "timestamp": datetime.now().isoformat()}
    except FileNotFoundError:
        logger.error(f"Точка не найдена: {path}")
        return None

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_alert": {}}

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def should_send_alert(state, key, cooldown):
    last = state.get("last_alert", {}).get(key)
    if not last: return True
    hours = (datetime.now() - datetime.fromisoformat(last)).total_seconds() / 3600
    return hours >= cooldown

def send_email(config, alerts):
    cfg = config["email"]
    if not cfg.get("enabled"):
        logger.info("Email отключён")
        return False
    subj = f"⚠️ Алерт дисков: {len(alerts)} проблем"
    body = "Проблемы с дисками:\n\n"
    for a in alerts:
        body += f"{a['name']} ({a['path']}): {a['percent']}% заполнено, свободно {a['free_gb']} ГБ\n"
    body += f"\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    try:
        msg = MIMEMultipart()
        msg['From'] = cfg['login']
        msg['To'] = ', '.join(cfg['recipients'])
        msg['Subject'] = subj
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        srv = smtplib.SMTP_SSL(cfg['smtp_server'], cfg['smtp_port']) if cfg.get('use_ssl') else smtplib.SMTP(cfg['smtp_server'], cfg['smtp_port'])
        if not cfg.get('use_ssl'): srv.starttls()
        srv.login(cfg['login'], cfg['password'])
        srv.send_message(msg)
        srv.quit()
        logger.info(f"✅ Email отправлен")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка email: {e}")
        return False

def main():
    logger.info("🔍 Проверка дисков...")
    config = load_config()
    alerts, state = [], load_state()
    cooldown = config.get("cooldown_hours", 24)
    for mp in config.get("mount_points", DEFAULT_CONFIG["mount_points"]):
        usage = get_disk_usage(mp["path"])
        if not usage: continue
        logger.info(f"📊 {mp['name']}: {usage['percent']}% ({usage['free_gb']} ГБ свободно)")
        level, threshold = None, None
        if usage['percent'] >= mp.get("critical_threshold", 90):
            level, threshold = "critical", mp.get("critical_threshold", 90)
        elif usage['percent'] >= mp.get("warn_threshold", 80):
            level, threshold = "warning", mp.get("warn_threshold", 80)
        if level:
            key = f"{mp['path']}:{level}"
            if should_send_alert(state, key, cooldown):
                logger.warning(f"🚨 {level.upper()} для {mp['name']}: {usage['percent']}%")
                alerts.append({**usage, "name": mp['name'], "level": level, "threshold": threshold})
                state.setdefault("last_alert", {})[key] = datetime.now().isoformat()
            else:
                logger.info(f"⏳ Алерт {key} в cooldown")
    if alerts:
        save_state(state)
        send_email(config, alerts)
    else:
        logger.info("✅ Все диски в норме")
    return 0

if __name__ == "__main__":
    sys.exit(main())
