# /opt/1cv8/scripts/core/config.py
"""
Конфигурация системы — единая точка доступа к путям, версиям и списку ИБ.
"""

import os
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent

# === SSL Configuration ===
SSL_DOMAIN = "bases.atotx.ru"
SSL_CERT_PATH = f"/etc/letsencrypt/live/{SSL_DOMAIN}"
SSL_LOG_PATH = "/var/log/1c-admin/ssl.log"

# === Backup Configuration ===
BACKUP_ROOT = Path(os.getenv("BACKUP_ROOT", "/var/backups/1c"))
BACKUP_LOG = Path("/var/log/1c-admin/backup.log")
SCRIPTS_DIR = Path("/opt/1cv8/scripts/engines")
LOG_FILE = Path("/var/log/1c_orchestrator.log")
BACKUP_USER = os.getenv("BACKUP_USER", "usr1cv8")


# === Функции загрузки ===
def load_version() -> str:
    """Загрузить версию из .version"""
    version_file = BASE_DIR / ".version"
    try:
        return version_file.read_text().strip()
    except FileNotFoundError:
        return "unknown"


def load_ib_list() -> List[str]:
    """Загрузить список ИБ из ib_list.conf"""
    ib_file = BASE_DIR / "ib_list.conf"
    ib_list = []
    try:
        with open(ib_file, "r", encoding="utf-8") as f:
            for line in f:
                ib_name = line.strip()
                if ib_name and not ib_name.startswith("#"):
                    ib_list.append(ib_name)
    except FileNotFoundError:
        pass
    return ib_list


def get_backup_dir(ib_name: str) -> Path:
    """Путь к директории бэкапов для ИБ"""
    return BACKUP_ROOT / ib_name


def get_ssl_domain() -> str:
    """Домен для SSL-сертификатов"""
    return SSL_DOMAIN


def get_ssl_cert_path() -> Path:
    """Путь к сертификатам"""
    return Path(SSL_CERT_PATH)


# === Класс для обратной совместимости (rm_service.py) ===
class Config:
    """Заглушка для совместимости с существующим кодом"""
    
    BACKUP_ROOT = BACKUP_ROOT
    SCRIPTS_DIR = SCRIPTS_DIR
    LOG_FILE = LOG_FILE
    BACKUP_USER = BACKUP_USER
    
    @classmethod
    def load(cls):
        return cls()