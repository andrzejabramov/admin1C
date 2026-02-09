#!/bin/bash
set -euo pipefail

# Определяем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Подключаем конфиг
CONFIG="$SCRIPT_DIR/config/storage.sh"
[[ ! -f "$CONFIG" ]] && { echo "error=Конфиг $CONFIG не найден" >&2; exit 1; }
source "$CONFIG"

# Проверяем существование каталога
[[ ! -d "$BACKUP_DIR" ]] && { echo "error=Каталог $BACKUP_DIR не существует" >&2; exit 1; }

# Получаем данные df
read -r fs blocks used avail pcent mount <<< $(df "$BACKUP_DIR" | awk 'NR==2 {print $1, $2, $3, $4, $5, $6}')
pcent_num="${pcent%\%}"

# Вывод в парсимом формате
cat <<EOF
filesystem=$fs
mount_point=$mount
total_kb=$((blocks * 1024))
used_kb=$((used * 1024))
free_kb=$((avail * 1024))
used_percent=$pcent_num
EOF
