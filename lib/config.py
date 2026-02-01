import os
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent

# SSL Configuration
SSL_DOMAIN = "bases.atotx.ru"
SSL_CERT_PATH = f"/etc/letsencrypt/live/{SSL_DOMAIN}"
SSL_LOG_PATH = "/var/log/1c-admin/ssl.log"

# Backup Configuration
BACKUP_ROOT = Path("/var/backups/1c")
BACKUP_LOG = Path("/var/log/1c-admin/backup.log")

def load_version() -> str:
    version_file = BASE_DIR / ".version"
    try:
        return version_file.read_text().strip()
    except FileNotFoundError:
        return "unknown"

def load_ib_list() -> List[str]:
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
    """Возвращает путь к директории бэкапов для конкретной ИБ"""
    return BACKUP_ROOT / ib_name

def get_ssl_domain() -> str:
    """Возвращает домен для SSL-сертификатов"""
    return SSL_DOMAIN

def get_ssl_cert_path() -> Path:
    """Возвращает путь к сертификатам"""
    return Path(SSL_CERT_PATH)

if __name__ == "__main__":
    print(f"Версия: {load_version()}")
    print(f"ИБ: {load_ib_list()}")
    print(f"SSL домен: {get_ssl_domain()}")
    print(f"Корень бэкапов: {BACKUP_ROOT}")
