#!/usr/bin/env bash
set -euo pipefail

BACKUP_ROOT="/var/backups/1c"
LOG_FILE="/var/backups/1c/rm.log"
DRY_RUN=false

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE" >&2
}

usage() {
    cat <<USAGE
Использование: $0 [ОПЦИИ]

Опции:
  --ib <имя_ИБ>        Удалить бэкапы указанной ИБ
  --timestamp <метка>  Удалить конкретный бэкап (ГГГГММДД_ЧЧММСС)
  --after <дата>       Удалить бэкапы новее даты (ГГГГММДД)
  --before <дата>      Удалить бэкапы старше даты (ГГГГММДД)
  --all                Удалить ВСЕ бэкапы всех ИБ
  --dry-run            Симуляция без фактического удаления
  --confirm            Разрешение на реальное удаление (гарантируется сервисом)
  --help               Показать эту справку

Примеры:
  $0 --ib test_ib --dry-run --confirm
  $0 --ib test_ib --timestamp 20260207_120000 --confirm
  $0 --ib test_ib --after 20260206 --before 20260208 --dry-run --confirm
USAGE
    exit 1
}

validate_ib_name() {
    [[ -d "$BACKUP_ROOT/$1" ]] || { log "❌ ИБ '$1' не найдена в $BACKUP_ROOT"; exit 1; }
}

# Парсинг аргументов
[[ $# -eq 0 ]] && usage
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ib) IB_NAME="$2"; shift 2 ;;
        --timestamp) TIMESTAMP="$2"; shift 2 ;;
        --after) AFTER="$2"; shift 2 ;;
        --before) BEFORE="$2"; shift 2 ;;
        --all) REMOVE_ALL=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --confirm) CONFIRMED=true; shift ;;
        --help) usage ;;
        *) log "❌ Неизвестный параметр: $1"; usage ;;
    esac
done

# Защита: реальное удаление требует --confirm
if [[ "${DRY_RUN}" == false ]] && [[ "${CONFIRMED:-false}" == false ]] && [[ "${REMOVE_ALL:-false}" == true || -z "${TIMESTAMP:-}" && -z "${AFTER:-}" && -z "${BEFORE:-}" ]]; then
    log "❌ Отказ: реальное удаление требует --confirm (проверка на уровне скрипта)"
    exit 1
fi

# Удаление всех ИБ
if [[ "${REMOVE_ALL:-false}" == true ]]; then
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
    [[ "$DRY_RUN" == true ]] && log "🔍 Симуляция: файлы НЕ будут удалены"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Целевой бэкап: $TARGET_DIR"
        find "$TARGET_DIR" -type f 2>/dev/null | while read -r f; do log "  → $f"; done
    else
        rm -rf "$TARGET_DIR" && log "✅ Удалён: $TARGET_DIR" || log "⚠️  Ошибка удаления (права?): $TARGET_DIR"
    fi
    exit 0
fi

# Удаление бэкапов с фильтрацией по дате
[[ "$DRY_RUN" == true ]] && log "🔍 Симуляция: файлы НЕ будут удалены"
log "Будут удалены директории в: $BACKUP_DIR"

# Собрать все кандидаты и применить фильтры
while IFS= read -r dir; do
    [[ -z "$dir" ]] && continue
    
    # Извлечь дату из имени директории (первые 8 символов: ГГГГММДД)
    dir_name=$(basename "$dir")
    backup_date="${dir_name:0:8}"
    
    # Фильтр --after: пропустить если дата НЕ больше AFTER (т.е. <= AFTER)
    if [[ -n "${AFTER:-}" ]]; then
        if ! [[ "$backup_date" > "$AFTER" ]]; then
            continue
        fi
    fi
    
    # Фильтр --before: пропустить если дата НЕ меньше BEFORE (т.е. >= BEFORE)
    if [[ -n "${BEFORE:-}" ]]; then
        if ! [[ "$backup_date" < "$BEFORE" ]]; then
            continue
        fi
    fi
    
    # Директория прошла все фильтры
    if [[ "$DRY_RUN" == true ]]; then
        log "  → $dir/"
    else
        rm -rf "$dir" && log "✅ Удалён: $dir/" || log "⚠️  Не удалён (права?): $dir/"
    fi
done < <(find "$BACKUP_DIR" -maxdepth 1 -type d -name "20[0-9][0-9][01][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9]" 2>/dev/null | sort)

log "✅ Операция завершена"
