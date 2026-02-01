#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh" 2>/dev/null || { echo "⚠️ utils.sh не найден, продолжаем без логирования"; }
CONFIG_FILE="$SCRIPT_DIR/db_config.sh"
[ -f "$CONFIG_FILE" ] || { echo "❌ Файл конфигурации не найден: $CONFIG_FILE"; exit 1; }
source "$CONFIG_FILE"

# Парсинг аргументов (упрощённо для теста)
IB_NAME="$1"
FORMAT="$2"
[ -z "$IB_NAME" ] && { echo "❌ Укажите ИБ: $0 <имя_ИБ> dump|sql"; exit 1; }
[[ ! "$FORMAT" =~ ^(dump|sql)$ ]] && { echo "❌ Формат: dump или sql"; exit 1; }

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_DIR="$BACKUP_ROOT/$IB_NAME/$TIMESTAMP"
BACKUP_FILE="$BACKUP_DIR/backup.$FORMAT"

echo "📁 Директория: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

if [ "$FORMAT" = "dump" ]; then
  echo "📦 Выполняю pg_dump -Fc на $PG_HOST..."
  ssh -i "$SSH_KEY" -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
    "$SSH_USER@$PG_HOST" \
    "PGPASSFILE=$REMOTE_PGPASS pg_dump -Fc -h localhost -p $PG_PORT -U $PG_USER -d $IB_NAME" \
    > "$BACKUP_FILE"
else
  echo "📦 Выполняю pg_dump | gzip на $PG_HOST..."
  ssh -i "$SSH_KEY" -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
    "$SSH_USER@$PG_HOST" \
    "PGPASSFILE=$REMOTE_PGPASS pg_dump -h localhost -p $PG_PORT -U $PG_USER -d $IB_NAME" \
    | gzip > "$BACKUP_FILE"
fi

if [ -f "$BACKUP_FILE" ]; then
  SIZE=$(du -h "$BACKUP_FILE" 2>/dev/null | cut -f1)
  echo "✅ Бэкап создан: $BACKUP_FILE ($SIZE)"
else
  echo "❌ Файл не создан!"
  exit 1
fi
