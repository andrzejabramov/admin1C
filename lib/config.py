import os
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent

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

def get_backup_dir() -> Path:
    return BASE_DIR / "backups"

if __name__ == "__main__":
    print(f"Версия: {load_version()}")
    print(f"ИБ: {load_ib_list()}")
