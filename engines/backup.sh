#!/bin/bash
# /opt/1cv8/scripts/engines/backup.sh
# Создание бэкапа ИБ через pg_dump
# ЕДИНСТВЕННАЯ ОТВЕТСТВЕННОСТЬ: только создание нового бэкапа

set -euo pipefail

# === Определение директории скрипта ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="$SCRIPT_DIR/config/db_config.sh"

[[ -f "$CONFIG_PATH" ]] || { echo "❌ Конфиг не найден: $CONFIG_PATH"; exit 1; }
source "$CONFIG_PATH"

# === Логирование ===
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# === Парсинг аргументов ===
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ib) IB_NAME="$2"; shift 2 ;;
    --format) FORMAT="$2"; shift 2 ;;
    *) echo "❌ Неизвестный аргумент: $1"; exit 1 ;;
  esac
done

# === Валидация ===
[[ -z "${IB_NAME:-}" ]] && { echo "❌ --ib не указан"; exit 1; }
[[ -z "${FORMAT:-}" ]] && { echo "❌ --format не указан"; exit 1; }
[[ "$FORMAT" != "dump" && "$FORMAT" != "sql" ]] && { echo "❌ Формат должен быть: dump или sql"; exit 1; }

# === Создание директории бэкапа ===
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/$IB_NAME/$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
log "📁 Директория: $BACKUP_DIR"

# === Бэкап в формате .dump ===
if [[ "$FORMAT" == "dump" ]]; then
    log "💾 Бэкап ИБ: $IB_NAME (формат: dump)"
    
    # Получаем размер БД для прогресс-бара (игнорируем ошибки)
    DB_SIZE=$(ssh -o StrictHostKeyChecking=accept-new -i "$SSH_KEY" "$SSH_USER@$PG_HOST" \
        "PGPASSFILE=$REMOTE_PGPASS psql -h localhost -p $PG_PORT -U $PG_USER -d $IB_NAME -tAc \"SELECT pg_database_size('$IB_NAME');\"" 2>/dev/null || echo "")
    
    # Очистка от пробелов
    DB_SIZE="${DB_SIZE//[[:space:]]/}"
    [[ "$DB_SIZE" =~ ^[0-9]+$ ]] || DB_SIZE=""
    
    # Выполняем pg_dump с прогрессом (БЕЗ -n!)
    if [[ -n "$DB_SIZE" && "$DB_SIZE" -gt 0 ]]; then
        ssh -o StrictHostKeyChecking=accept-new -i "$SSH_KEY" "$SSH_USER@$PG_HOST" \
            "PGPASSFILE=$REMOTE_PGPASS pg_dump -Fc -h localhost -p $PG_PORT -U $PG_USER $IB_NAME" 2>/dev/null | \
            pv -f -s "$DB_SIZE" | \
            cat > "$BACKUP_DIR/backup.dump"
    else
        ssh -o StrictHostKeyChecking=accept-new -i "$SSH_KEY" "$SSH_USER@$PG_HOST" \
            "PGPASSFILE=$REMOTE_PGPASS pg_dump -Fc -h localhost -p $PG_PORT -U $PG_USER $IB_NAME" 2>/dev/null | \
            pv -f | \
            cat > "$BACKUP_DIR/backup.dump"
    fi
    
    echo ""
    SIZE=$(du -h "$BACKUP_DIR/backup.dump" 2>/dev/null | cut -f1 || echo "N/A")
    log "✅ Завершён: $BACKUP_DIR/backup.dump ($SIZE)"
    exit 0
fi

# === Бэкап в формате .sql.gz ===
if [[ "$FORMAT" == "sql" ]]; then
    log "💾 Бэкап ИБ: $IB_NAME (формат: sql.gz)"
    
    ssh -o StrictHostKeyChecking=accept-new -i "$SSH_KEY" "$SSH_USER@$PG_HOST" \
        "PGPASSFILE=$REMOTE_PGPASS pg_dump -h localhost -p $PG_PORT -U $PG_USER $IB_NAME --no-owner --no-privileges" 2>/dev/null | \
        gzip -c | \
        cat > "$BACKUP_DIR/backup.sql.gz"
    
    SIZE=$(du -h "$BACKUP_DIR/backup.sql.gz" 2>/dev/null | cut -f1 || echo "N/A")
    log "✅ Завершён: $BACKUP_DIR/backup.sql.gz ($SIZE)"
    exit 0
fi

echo "❌ Неизвестная ошибка"
exit 1
