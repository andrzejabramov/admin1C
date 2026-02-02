#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh" 2>/dev/null || {
  log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
  error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ $*" >&2; exit 1; }
}
CONFIG_FILE="$SCRIPT_DIR/db_config.sh"
[ -f "$CONFIG_FILE" ] || error "Файл конфигурации не найден: $CONFIG_FILE"
source "$CONFIG_FILE"

# Проверка наличия pv
HAS_PV=$(command -v pv >/dev/null && echo 1 || echo 0)

# Парсинг аргументов
IB_NAME=""
FORMAT=""
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ib) IB_NAME="$2"; shift 2 ;;
    --format) FORMAT="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) error "Неизвестный параметр: $1";;
  esac
done

[ -z "$IB_NAME" ] && error "Укажите ИБ: --ib <имя_ИБ>"
[[ ! "$FORMAT" =~ ^(dump|sql)$ ]] && error "Формат: --format dump|sql"

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_DIR="$BACKUP_ROOT/$IB_NAME/$TIMESTAMP"
BACKUP_FILE="$BACKUP_DIR/backup.$FORMAT"

log "Начало бэкапа ИБ: $IB_NAME, формат: $FORMAT"
[ "$DRY_RUN" = true ] && {
  log "[DRY-RUN] Директория: $BACKUP_DIR"
  log "[DRY-RUN] Команда pg_dump будет выполнена на $PG_HOST"
  log "[DRY-RUN] Файл не будет создан"
  exit 0
}

# Проверка свободного места (минимум 2 ГБ)
FREE_SPACE=$(df -BG "$BACKUP_ROOT" | awk 'NR==2 {print $4}' | sed 's/G//')
[ "$FREE_SPACE" -lt 2 ] && error "Недостаточно места на диске: $FREE_SPACE ГБ (требуется ≥2 ГБ)"

log "Создание директории: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Функция мониторинга (если нет pv)
monitor_progress() {
  local file="$1" name="$2"
  echo -e "\n📦 Мониторинг: $name (обновление каждые 10 сек)\n"
  while true; do
    [ -f "$file" ] || { sleep 2; continue; }
    SIZE=$(du -h "$file" 2>/dev/null | cut -f1 || echo "0B")
    echo -ne "\rТекущий размер: $SIZE"
    sleep 10
  done
}

if [ "$FORMAT" = "dump" ]; then
  log "Выполняю pg_dump -Fc на $PG_HOST..."
  if [ "$HAS_PV" = "1" ]; then
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
      "$SSH_USER@$PG_HOST" \
      "PGPASSFILE=$REMOTE_PGPASS pg_dump -Fc -h localhost -p $PG_PORT -U $PG_USER -d $IB_NAME" \
      | pv -pterab -N "$IB_NAME.dump" > "$BACKUP_FILE"
  else
    monitor_progress "$BACKUP_FILE" "$IB_NAME.dump" &
    MONITOR_PID=$!
    trap "kill $MONITOR_PID 2>/dev/null; wait $MONITOR_PID 2>/dev/null" EXIT
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
      "$SSH_USER@$PG_HOST" \
      "PGPASSFILE=$REMOTE_PGPASS pg_dump -Fc -h localhost -p $PG_PORT -U $PG_USER -d $IB_NAME" \
      > "$BACKUP_FILE"
    kill $MONITOR_PID 2>/dev/null; wait $MONITOR_PID 2>/dev/null; trap - EXIT
    echo -e "\n✅ Завершено"
  fi
else
  log "Выполняю pg_dump | gzip на $PG_HOST..."
  if [ "$HAS_PV" = "1" ]; then
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
      "$SSH_USER@$PG_HOST" \
      "PGPASSFILE=$REMOTE_PGPASS pg_dump -h localhost -p $PG_PORT -U $PG_USER -d $IB_NAME" \
      | pv -pterab -N "$IB_NAME.sql" | gzip > "$BACKUP_FILE"
  else
    monitor_progress "$BACKUP_FILE" "$IB_NAME.sql" &
    MONITOR_PID=$!
    trap "kill $MONITOR_PID 2>/dev/null; wait $MONITOR_PID 2>/dev/null" EXIT
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
      "$SSH_USER@$PG_HOST" \
      "PGPASSFILE=$REMOTE_PGPASS pg_dump -h localhost -p $PG_PORT -U $PG_USER -d $IB_NAME" \
      | gzip > "$BACKUP_FILE"
    kill $MONITOR_PID 2>/dev/null; wait $MONITOR_PID 2>/dev/null; trap - EXIT
    echo -e "\n✅ Завершено"
  fi
fi

[ -s "$BACKUP_FILE" ] || error "Файл бэкапа пустой или не создан: $BACKUP_FILE"
SIZE=$(du -h "$BACKUP_FILE" 2>/dev/null | cut -f1)
log "✅ Бэкап завершён: $BACKUP_FILE ($SIZE)"

# Ротация: удалить бэкапы старше 30 дней для этой ИБ
log "Очистка старых бэкапов (старше 5 дней)..."
find "$BACKUP_ROOT/$IB_NAME" -maxdepth 1 -type d -mtime +5 -print0 2>/dev/null | \
  while IFS= read -r -d '' dir; do
    log "Удаление: $dir"
    rm -rf "$dir"
  done
