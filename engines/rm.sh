#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# rm.sh — безопасное удаление бэкапов информационных баз 1С
# ==============================================================================

BACKUP_ROOT="/var/backups/1c"
LOG_FILE="/var/log/1c_backup_rm.log"
DRY_RUN=false
CONFIRMED=false

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE" >&2
}

usage() {
    cat <<EOF
Использование: $0 [ОПЦИИ]

Опции:
  --ib <имя_ИБ>        Удалить ВСЕ бэкапы указанной ИБ
  --timestamp <метка>  Удалить конкретный бэкап (формат: ГГГГММДД_ЧЧММСС)
  --older-than <дата>  Удалить бэкапы старше даты (формат: ГГГГММДД)
  --all                Удалить ВСЕ бэкапы всех ИБ
  --dry-run            Симуляция без фактического удаления
  --confirm            Обязательное подтверждение перед удалением
  --help               Показать эту справку

Примеры:
  $0 --ib artel_2025 --confirm
  $0 --ib artel_2025 --timestamp 20260202_182603 --confirm
  $0 --ib artel_2025 --older-than 20260201 --dry-run
  $0 --all --confirm
EOF
    exit 1
}

validate_ib_name() {
    local ib_name="$1"
    if [[ ! -d "$BACKUP_ROOT/$ib_name" ]]; then
        log "❌ Ошибка: ИБ '$ib_name' не найдена в $BACKUP_ROOT"
        exit 1
    fi
}

confirm_action() {
    local msg="$1"
    if [[ "$CONFIRMED" == false ]]; then
        log "⚠️  Требуется подтверждение: $msg"
        read -p "Подтвердите действие (yes/no): " answer
        if [[ "$answer" != "yes" ]]; then
            log "❌ Действие отменено пользователем"
            exit 0
        fi
    fi
}

# ==============================================================================
# Парсинг аргументов
# ==============================================================================

if [[ $# -eq 0 ]]; then usage; fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ib)
            IB_NAME="$2"
            shift 2
            ;;
        --timestamp)
            TIMESTAMP="$2"
            shift 2
            ;;
        --older-than)
            OLDER_THAN="$2"
            shift 2
            ;;
        --all)
            REMOVE_ALL=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            log "🔍 Режим симуляции (dry-run): файлы НЕ будут удалены"
            shift
            ;;
        --confirm)
            CONFIRMED=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            log "❌ Неизвестный параметр: $1"
            usage
            ;;
    esac
done

# ==============================================================================
# Валидация и выполнение
# ==============================================================================

if [[ "${REMOVE_ALL:-false}" == true ]]; then
    confirm_action "УДАЛЕНИЕ ВСЕХ БЭКАПОВ ВСЕХ ИБ из $BACKUP_ROOT"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Симуляция удаления всех ИБ:"
        find "$BACKUP_ROOT" -type f \( -name "*.dump" -o -name "*.sql.gz" -o -name "*.dt" \) | while read -r file; do
            log "  → $file"
        done
    else
        log "Удаление всех бэкапов..."
        find "$BACKUP_ROOT" -type f \( -name "*.dump" -o -name "*.sql.gz" -o -name "*.dt" \) -print -delete | while read -r file; do
            log "✅ Удалён: $file"
        done
    fi
    exit 0
fi

if [[ -z "${IB_NAME:-}" ]]; then
    log "❌ Ошибка: требуется указать --ib <имя_ИБ> или --all"
    usage
fi

validate_ib_name "$IB_NAME"
BACKUP_DIR="$BACKUP_ROOT/$IB_NAME"

if [[ -n "${TIMESTAMP:-}" ]]; then
    # Удаление конкретного бэкапа по метке времени
    pattern="${IB_NAME}_${TIMESTAMP}.*"
    files=("$BACKUP_DIR"/$pattern)
    
    if [[ ! -e "${files[0]}" ]]; then
        log "❌ Бэкапы с меткой '$TIMESTAMP' не найдены"
        exit 1
    fi
    
    confirm_action "Удаление бэкапа '$IB_NAME' с меткой '$TIMESTAMP'"
    
    for file in "${files[@]}"; do
        [[ -e "$file" ]] || continue
        if [[ "$DRY_RUN" == true ]]; then
            log "🔍 Симуляция: $file"
        else
            rm -f "$file"
            log "✅ Удалён: $file"
        fi
    done
    
elif [[ -n "${OLDER_THAN:-}" ]]; then
    # Удаление бэкапов старше даты
    cutoff=$(date -d "${OLDER_THAN} 00:00:00" +%s 2>/dev/null || date -j -f "%Y%m%d" "$OLDER_THAN" +%s 2>/dev/null || { log "❌ Неверный формат даты"; exit 1; })
    
    confirm_action "Удаление бэкапов '$IB_NAME' старше $OLDER_THAN"
    
    find "$BACKUP_DIR" -type f \( -name "*.dump" -o -name "*.sql.gz" -o -name "*.dt" \) | while read -r file; do
        file_time=$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null)
        if [[ $file_time -lt $cutoff ]]; then
            if [[ "$DRY_RUN" == true ]]; then
                log "🔍 Симуляция: $file (старше $OLDER_THAN)"
            else
                rm -f "$file"
                log "✅ Удалён: $file"
            fi
        fi
    done
    
else
    # Удаление ВСЕХ бэкапов ИБ
    confirm_action "УДАЛЕНИЕ ВСЕХ бэкапов ИБ '$IB_NAME'"
    
    if [[ "$DRY_RUN" == true ]]; then
        log "Симуляция удаления всех бэкапов '$IB_NAME':"
        find "$BACKUP_DIR" -type f \( -name "*.dump" -o -name "*.sql.gz" -o -name "*.dt" \) | while read -r file; do
            log "  → $file"
        done
    else
        log "Удаление всех бэкапов '$IB_NAME'..."
        find "$BACKUP_DIR" -type f \( -name "*.dump" -o -name "*.sql.gz" -o -name "*.dt" \) -print -delete | while read -r file; do
            log "✅ Удалён: $file"
        done
    fi
fi

log "✅ Операция завершена"