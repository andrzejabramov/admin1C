#!/bin/bash
# backup/engines/backup.sh
# Создание бэкапа ИБ через pg_dump (удалённое подключение к кластеру БД)
set -euo pipefail

# === Загрузка глобальной конфигурации ===
GLOBAL_CONFIG="/opt/1cv8/scripts/engines/config/global.sh"
[[ -f "$GLOBAL_CONFIG" ]] || { echo "❌ Глобальный конфиг не найден: $GLOBAL_CONFIG" >&2; exit 1; }
source "$GLOBAL_CONFIG"

# === Явные пути к утилитам PostgreSQL 15 ===
PG_DUMP="/usr/lib/postgresql/15/bin/pg_dump"
PSQL="/usr/lib/postgresql/15/bin/psql"

# === Логирование ===
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# === Парсинг аргументов ===
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ib) IB_NAME="$2"; shift 2 ;;
    --format) FORMAT="$2"; shift 2 ;;
    *) echo "❌ Неизвестный аргумент: $1" >&2; exit 1 ;;
  esac
done

# === Валидация обязательных параметров ===
[[ -z "${IB_NAME:-}" ]] && { echo "❌ --ib не указан" >&2; exit 1; }
[[ -z "${FORMAT:-}" ]] && { echo "❌ --format не указан" >&2; exit 1; }
[[ "$FORMAT" != "dump" && "$FORMAT" != "sql" ]] && { echo "❌ Формат должен быть: dump или sql" >&2; exit 1; }

# === Валидация существования ИБ в PostgreSQL (ДО создания директории!) ===
if ! PGPASSFILE="$PGPASS_FILE" $PSQL -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -tAc "SELECT 1 FROM pg_database WHERE datname = '$IB_NAME'" 2>/dev/null | grep -q "1"; then
  echo "❌ ИБ '$IB_NAME' не найдена в кластере БД $PG_HOST:$PG_PORT" >&2
  echo "   → Проверьте имя в ib_list.conf или выполните: ib_1c storage list-ibs" >&2
  exit 1
fi

# === Создание директории бэкапа ===
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/$IB_NAME/$TIMESTAMP"
mkdir -p "$BACKUP_DIR" || { echo "❌ Не удалось создать $BACKUP_DIR" >&2; exit 1; }
log "📁 Директория: $BACKUP_DIR"

# === Функция очистки при ошибке ===
cleanup_on_error() {
  local exit_code=$?
  if [[ $exit_code -ne 0 ]] && [[ -n "${BACKUP_DIR:-}" ]] && [[ -d "$BACKUP_DIR" ]]; then
    # Удаляем ТОЛЬКО если директория пустая или содержит только неполный бэкап
    if [[ -z "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]] || [[ ! -s "$BACKUP_DIR/backup.dump" 2>/dev/null && ! -s "$BACKUP_DIR/backup.sql.gz" 2>/dev/null ]]; then
      log "🧹 Очистка временной директории после ошибки: $BACKUP_DIR"
      rm -rf "$BACKUP_DIR" 2>/dev/null || true
    fi
  fi
  exit $exit_code
}
trap cleanup_on_error EXIT

# === Бэкап в формате .dump ===
if [[ "$FORMAT" == "dump" ]]; then
  log "💾 Бэкап ИБ: $IB_NAME (формат: dump)"
  
  # Получаем размер БД для прогресс-бара
  DB_SIZE=$(PGPASSFILE="$PGPASS_FILE" $PSQL -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$IB_NAME" -tAc "SELECT pg_database_size('$IB_NAME');" 2>/dev/null || echo "")
  DB_SIZE="${DB_SIZE//[[:space:]]/}"
  [[ "$DB_SIZE" =~ ^[0-9]+$ ]] || DB_SIZE=""
  
  # Выполняем pg_dump с прогрессом
  if [[ -n "$DB_SIZE" && "$DB_SIZE" -gt 0 ]]; then
    if ! PGPASSFILE="$PGPASS_FILE" $PG_DUMP -Fc -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" "$IB_NAME" 2>/dev/null | \
      pv -f -s "$DB_SIZE" | \
      tee "$BACKUP_DIR/backup.dump" > /dev/null; then
      log "❌ Ошибка при создании бэкапа ИБ '$IB_NAME'"
      exit 1
    fi
  else
    if ! PGPASSFILE="$PGPASS_FILE" $PG_DUMP -Fc -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" "$IB_NAME" 2>/dev/null | \
      pv -f | \
      tee "$BACKUP_DIR/backup.dump" > /dev/null; then
      log "❌ Ошибка при создании бэкапа ИБ '$IB_NAME'"
      exit 1
    fi
  fi
  
  echo ""
  
  # === Проверка целостности файла ===
  if [[ ! -f "$BACKUP_DIR/backup.dump" ]] || [[ ! -s "$BACKUP_DIR/backup.dump" ]]; then
    log "❌ Фатальная ошибка: файл бэкапа отсутствует или пустой"
    exit 1
  fi
  
  SIZE=$(du -h "$BACKUP_DIR/backup.dump" 2>/dev/null | cut -f1 || echo "N/A")
  log "✅ Завершён: $BACKUP_DIR/backup.dump ($SIZE)"
  exit 0
fi

# === Бэкап в формате .sql.gz ===
if [[ "$FORMAT" == "sql" ]]; then
  log "💾 Бэкап ИБ: $IB_NAME (формат: sql.gz)"
  
  if ! PGPASSFILE="$PGPASS_FILE" $PG_DUMP -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" "$IB_NAME" --no-owner --no-privileges 2>/dev/null | \
    gzip -c | \
    tee "$BACKUP_DIR/backup.sql.gz" > /dev/null; then
    log "❌ Ошибка при создании бэкапа ИБ '$IB_NAME'"
    exit 1
  fi
  
  # Проверка целостности
  if [[ ! -f "$BACKUP_DIR/backup.sql.gz" ]] || [[ ! -s "$BACKUP_DIR/backup.sql.gz" ]]; then
    log "❌ Фатальная ошибка: файл бэкапа отсутствует или пустой"
    exit 1
  fi
  
  SIZE=$(du -h "$BACKUP_DIR/backup.sql.gz" 2>/dev/null | cut -f1 || echo "N/A")
  log "✅ Завершён: $BACKUP_DIR/backup.sql.gz ($SIZE)"
  exit 0
fi

echo "❌ Неизвестная ошибка" >&2
exit 1
