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

# Заголовок (TSV)
echo -e "ib_name\ttimestamp\tfile_type\tsize_bytes\tpath"

# Ищем файлы бэкапов
find "$BACKUP_DIR" -type f \( \
  -name "*.dump" -o \
  -name "*.dt" -o \
  -name "*.sql.gz" -o \
  -name "backup.dump" -o \
  -name "backup.sql*" \
\) 2>/dev/null | while IFS= read -r filepath; do
  # Извлекаем имя ИБ из пути
  ib_name=$(echo "$filepath" | sed -n "s|^$BACKUP_DIR/\([^/]*\)/.*|\1|p")
  [[ -z "$ib_name" || "$ib_name" == "lost+found" ]] && continue
  
  # Временная метка (секунды с эпохи)
  timestamp=$(stat -c %Y "$filepath" 2>/dev/null || echo "0")
  
  # Определяем тип файла
  filename=$(basename "$filepath")
  if [[ "$filename" == *.dump || "$filename" == backup.dump ]]; then
    file_type="postgres_dump"
  elif [[ "$filename" == *.dt ]]; then
    file_type="1c_dt"
  elif [[ "$filename" == *.sql.gz || "$filename" == backup.sql* ]]; then
    file_type="sql_gz"
  else
    file_type="unknown"
  fi
  
  # Размер в байтах
  size_bytes=$(stat -c %s "$filepath" 2>/dev/null || echo "0")
  
  # Вывод в TSV
  echo -e "${ib_name}\t${timestamp}\t${file_type}\t${size_bytes}\t${filepath}"
done
