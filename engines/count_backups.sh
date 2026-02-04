#!/bin/bash
set -euo pipefail

# Определяем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Подключаем конфиг
CONFIG="$SCRIPT_DIR/config/storage.conf"
[[ ! -f "$CONFIG" ]] && { echo "error=Конфиг $CONFIG не найден" >&2; exit 1; }
source "$CONFIG"

# Проверяем существование каталога
[[ ! -d "$BACKUP_DIR" ]] && { echo "error=Каталог $BACKUP_DIR не существует" >&2; exit 1; }

# Заголовок (TSV)
echo -e "ib_name\ttotal_files\ttotal_size_bytes"

# Проходим по подкаталогам ИБ
for ib_dir in "$BACKUP_DIR"/*/; do
  [[ -L "$ib_dir" || ! -d "$ib_dir" ]] && continue
  
  ib_name=$(basename "$ib_dir")
  [[ "$ib_name" == "lost+found" ]] && continue
  
  # Считаем файлы бэкапов
  files=$(find "$ib_dir" -type f \( \
    -name "*.dump" -o \
    -name "*.dt" -o \
    -name "*.sql.gz" -o \
    -name "backup.dump" -o \
    -name "backup.sql*" \
  \) 2>/dev/null | wc -l)
  
  # Пропускаем ИБ без бэкапов
  [[ "$files" -eq 0 ]] && continue
  
  # Суммируем размеры
  size_bytes=$(find "$ib_dir" -type f \( \
    -name "*.dump" -o \
    -name "*.dt" -o \
    -name "*.sql.gz" -o \
    -name "backup.dump" -o \
    -name "backup.sql*" \
  \) -exec stat -c %s {} + 2>/dev/null | awk '{s+=$1} END {print s+0}')
  
  echo -e "${ib_name}\t${files}\t${size_bytes}"
done
