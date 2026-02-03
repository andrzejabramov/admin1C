#!/usr/bin/env bash
set -euo pipefail

BACKUP_ROOT="/var/backups/1c"
LOG_FILE="/var/backups/1c/rm.log"
DRY_RUN=false
CONFIRMED=false

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE" >&2
}

usage() {
    cat <<USAGE
Использование: $0 [ОПЦИИ]

Опции:
  --ib <имя_ИБ>        Удалить ВСЕ бэкапы указанной ИБ
  --timestamp <метка>  Удалить конкретный бэкап (формат: ГГГГММДД_ЧЧММСС)
  --older-than <дата>  Удалить бэкапы старше даты (формат: ГГГГММДД)
  --all                Удалить ВСЕ бэкапы всех ИБ
  --dry-run            Симуляция без фактического удаления (без подтверждения!)
  --confirm            Обязательное подтверждение перед удалением (только для реальных операций)
  --help               Показать эту справку

Примеры:
  $0 --ib artel_2025 --dry-run
  $0 --ib artel_2025 --timestamp 20260203_205027 --confirm
USAGE
    exit 1
}

validate_ib_name() {
    [[ -d "$BACKUP_ROOT/$1" ]] || { log "❌ ИБ '$1' не найдена в $BACKUP_ROOT"; exit 1; }
}

confirm_action() {
    # В dry-run подтверждение НЕ требуется
    [[ "$DRY_RUN" == true ]] && return
    
    [[ "$CONFIRMED" == true ]] && return
    log "⚠️  Требуется подтверждение: $1"
    read -p "Подтвердите действие (yes/no): " answer
    [[ "$answer" == "yes" ]] || { log "❌ Отменено"; exit 0; }
}

# Парсинг аргументов
[[ $# -eq 0 ]] && usage
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ib) IB_NAME="$2"; shift 2 ;;
        --timestamp) TIMESTAMP="$2"; shift 2 ;;
        --older-than) OLDER_THAN="$2"; shift 2 ;;
        --all) REMOVE_ALL=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --confirm) CONFIRMED=true; shift ;;
        --help) usage ;;
        *) log "❌ Неизвестный параметр: $1"; usage ;;
    esac
done

# Удаление всех ИБ
if [[ "${REMOVE_ALL:-false}" == true ]]; then
    confirm_action "УДАЛЕНИЕ ВСЕХ БЭКАПОВ ВСЕХ ИБ из $BACKUP_ROOT"
    [[ "$DRY_RUN" == true ]] && log "🔍 Симуляция: файлы НЕ будут удалены"
    
    find "$BACKUP_ROOT" -mindepth 2 -maxdepth 2 -type d -name "20[0-9][0-9][01][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9]" 2>/dev/null | sort | while read -r dir; do
        if [[ "$DRY_RUN" == true ]]; then
            log "  → $dir/"
        else
            rm -rf "$dir" && log "✅ Удалён: $dir/" || log "⚠️  Не удалён (права?): $dir/"
        fi
    done
    exit 0
fi

[[ -z "${IB_NAME:-}" ]] && { log "❌ Требуется --ib <имя_ИБ>"; usage; }
validate_ib_name "$IB_NAME"
BACKUP_DIR="$BACKUP_ROOT/$IB_NAME"

# Удаление конкретного бэкапа
if [[ -n "${TIMESTAMP:-}" ]]; then
    TARGET_DIR="$BACKUP_DIR/$TIMESTAMP"
    [[ -d "$TARGET_DIR" ]] || {
        log "❌ Бэкап '$TIMESTAMP' не найден в $BACKUP_DIR"
        log "Доступные бэкапы:"
        ls -1d "$BACKUP_DIR"/20[0-9][0-9][01][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9] 2>/dev/null || echo "  (нет)"
        exit 1
    }
    confirm_action "Удаление бэкапа '$IB_NAME' с меткой '$TIMESTAMP'"
    [[ "$DRY_RUN" == true ]] && log "🔍 Симуляция: файлы НЕ будут удалены"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Целевой бэкап: $TARGET_DIR"
        find "$TARGET_DIR" -type f 2>/dev/null | while read -r f; do log "  → $f"; done
    else
        rm -rf "$TARGET_DIR" && log "✅ Удалён: $TARGET_DIR" || log "⚠️  Ошибка удаления (права?): $TARGET_DIR"
    fi
    exit 0
fi

# Удаление всех бэкапов ИБ
confirm_action "УДАЛЕНИЕ ВСЕХ бэкапов ИБ '$IB_NAME'"
[[ "$DRY_RUN" == true ]] && log "🔍 Симуляция: файлы НЕ будут удалены"

if [[ "$DRY_RUN" == true ]]; then
    log "Будут удалены директории в: $BACKUP_DIR"
    find "$BACKUP_DIR" -maxdepth 1 -type d -name "20[0-9][0-9][01][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9]" 2>/dev/null | sort | while read -r dir; do
        log "  → $dir/"
    done
else
    find "$BACKUP_DIR" -maxdepth 1 -type d -name "20[0-9][0-9][01][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9]" 2>/dev/null | sort | while read -r dir; do
        rm -rf "$dir" && log "✅ Удалён: $dir/" || log "⚠️  Не удалён (права?): $dir/"
    done
fi

log "✅ Операция завершена"
