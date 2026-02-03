#!/bin/bash
# /opt/1cv8/scripts/engines/rm.sh
# Ручное удаление бэкапов
# ЕДИНСТВЕННАЯ ОТВЕТСТВЕННОСТЬ: только удаление файлов для ОДНОЙ ИБ
# Цикл по списку ИБ — на уровне admin1c.py

set -euo pipefail

# === Определение директории скрипта ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="$SCRIPT_DIR/db_config.sh"

[[ -f "$CONFIG_PATH" ]] || { echo "❌ Конфиг не найден: $CONFIG_PATH"; exit 1; }
source "$CONFIG_PATH"

# === Парсинг аргументов ===
DRY_RUN=false
IB_NAME=""
TIMESTAMP=""
OLDER_THAN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ib) IB_NAME="$2"; shift 2 ;;
    --timestamp) TIMESTAMP="$2"; shift 2 ;;
    --older-than) OLDER_THAN="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "❌ Неизвестный аргумент: $1"; exit 1 ;;
  esac
done

# === Валидация ===
[[ -z "$IB_NAME" ]] && { echo "❌ --ib не указан"; exit 1; }

BACKUP_PATH="$BACKUP_ROOT/$IB_NAME"
[[ -d "$BACKUP_PATH" ]] || { echo "❌ Директория не найдена: $BACKUP_PATH"; exit 1; }

# === Логика удаления ===
if [[ -n "$TIMESTAMP" ]]; then
    # Удалить конкретный бэкап
    TARGET_DIR="$BACKUP_PATH/$TIMESTAMP"
    [[ -d "$TARGET_DIR" ]] || { echo "❌ Бэкап не найден: $TARGET_DIR"; exit 1; }
    
    if [[ "$DRY_RUN" == true ]]; then
        echo "🧪 $TARGET_DIR"
    else
        rm -rf "$TARGET_DIR" && echo "✅ $TARGET_DIR"
    fi
    
elif [[ -n "$OLDER_THAN" ]]; then
    # Удалить бэкапы старше даты
    if [[ ! "$OLDER_THAN" =~ ^[0-9]{8}$ ]]; then
        echo "❌ Неверный формат даты: $OLDER_THAN (ожидается YYYYMMDD)"; exit 1
    fi
    
    COUNT=0
    while IFS= read -r -d '' dir; do
        DIR_NAME=$(basename "$dir")
        [[ "$DIR_NAME" =~ ^([0-9]{8})_[0-9]{6}$ ]] || continue
        BACKUP_DATE="${BASH_REMATCH[1]}"
        [[ "$BACKUP_DATE" < "$OLDER_THAN" ]] || continue
        
        if [[ "$DRY_RUN" == true ]]; then
            echo "🧪 $dir"
        else
            rm -rf "$dir" && echo "✅ $dir"
        fi
        ((COUNT++))
    done < <(find "$BACKUP_PATH" -maxdepth 1 -type d -name "20[0-9][0-9][0-1][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9]" -print0)
    
    [[ "$COUNT" -eq 0 ]] && echo "ℹ️  Нет бэкапов для удаления"
    
else
    # Удалить ВСЕ бэкапы ИБ
    COUNT=0
    while IFS= read -r -d '' dir; do
        if [[ "$DRY_RUN" == true ]]; then
            echo "🧪 $dir"
        else
            rm -rf "$dir" && echo "✅ $dir"
        fi
        ((COUNT++))
    done < <(find "$BACKUP_PATH" -maxdepth 1 -type d -name "20[0-9][0-9][0-1][0-9][0-3][0-9]_[0-2][0-9][0-5][0-9][0-5][0-9]" -print0)
    
    [[ "$COUNT" -eq 0 ]] && echo "ℹ️  Нет бэкапов для удаления"
fi

exit 0
