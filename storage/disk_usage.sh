#!/bin/bash
# /opt/1cv8/scripts/storage/disk_usage.sh
# Вывод: парсимый формат для Python (ключ=значение)
set -euo pipefail

BACKUP_DIR="/var/backups/1c"

if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "error=Каталог $BACKUP_DIR не существует" >&2
  exit 1
fi

# Получаем данные от df (в килобайтах для точности)
read -r fs blocks used avail pcent mount <<< $(df "$BACKUP_DIR" | awk 'NR==2 {print $1, $2, $3, $4, $5, $6}')

# Преобразуем процент в число (убираем %)
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
