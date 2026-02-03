#!/bin/bash
# /opt/1cv8/scripts/engines/prune.sh
# Автоматическая ротация старых бэкапов
# ЕДИНСТВЕННАЯ ОТВЕТСТВЕННОСТЬ: только удаление старых бэкапов

set -euo pipefail

# === Определение директории скрипта ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="$SCRIPT_DIR/db_config.sh"

[[ -f "$CONFIG_PATH" ]] || { echo "❌ Конфиг не найден: $CONFIG_PATH"; exit 1; }
source "$CONFIG_PATH"

# === Логирование ===
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# === Парсинг аргументов ===
KEEP_DAYS=3
DRY_RUN=false
IB_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ib) IB_NAME="$2"; shift 2 ;;
    --keep-days) KEEP_DAYS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "❌ Неизвестный аргумент: $1"; exit 1 ;;
  esac
done

# === Валидация ===
[[ "$KEEP_DAYS" =~ ^[0-9]+$ ]] || { echo "❌ --keep-days должен быть числом"; exit 1; }
[[ "$KEEP_DAYS" -ge 0 ]] || { echo "❌ --keep-days не может быть отрицательным"; exit 1; }

# === Функция удаления ===
delete_backup() {
    local dir="$1"
    if [[ "$DRY_RUN" == true ]]; then
        echo "  🧪 Симуляция: удалить $dir"
    else
        log "🗑️ Удаление: $dir"
        rm -rf "$dir" 2>/dev/null || echo "  ⚠️ Не удалось удалить: $dir"
    fi
}

# === Основная логика ===
if [[ -n "$IB_NAME" ]]; then
    # Ротация для одной ИБ
    BACKUP_PATH="$BACKUP_ROOT/$IB_NAME"
    [[ -d "$BACKUP_PATH" ]] || { echo "❌ Директория не найдена: $BACKUP_PATH"; exit 1; }
    
    log "🧹 Ротация ИБ: $IB_NAME (сохранять: $KEEP_DAYS дней)"
    
    if [[ "$DRY_RUN" == true ]]; then
        echo "  🧪 Симуляция режима (--dry-run)"
    fi
    
    find "$BACKUP_PATH" -maxdepth 1 -type d -name "20[0-9][0-9][0-1][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9]" -mtime +$KEEP_DAYS 2>/dev/null | \
    while IFS= read -r dir; do
        delete_backup "$dir"
    done
    
    log "✅ Ротация завершена для: $IB_NAME"
else
    # Ротация для всех ИБ в $BACKUP_ROOT
    log "�� Ротация ВСЕХ ИБ (сохранять: $KEEP_DAYS дней)"
    
    if [[ "$DRY_RUN" == true ]]; then
        echo "  🧪 Симуляция режима (--dry-run)"
    fi
    
    find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d ! -name 'lost+found' 2>/dev/null | \
    while IFS= read -r ib_dir; do
        IB_NAME=$(basename "$ib_dir")
        echo ""
        log "📦 ИБ: $IB_NAME"
        
        find "$ib_dir" -maxdepth 1 -type d -name "20[0-9][0-9][0-1][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9]" -mtime +$KEEP_DAYS 2>/dev/null | \
        while IFS= read -r dir; do
            delete_backup "$dir"
        done
    done
    
    log "✅ Ротация завершена для всех ИБ"
fi

exit 0
