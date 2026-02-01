#!/bin/bash
# engines/backup.sh — бэкап ИБ 1С через выполнение pg_dump на сервере БД (версия 15.10)
# Архитектура: локальный скрипт → SSH → pg_dump 15.10 на сервере БД → передача результата обратно

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils.sh"

CONFIG_FILE="$SCRIPT_DIR/db_config.sh"
[ -f "$CONFIG_FILE" ] || error "Файл конфигурации не найден: $CONFIG_FILE" "$BACKUP_LOG"
source "$CONFIG_FILE"
log "Конфигурация загружена: $CONFIG_FILE" "$BACKUP_LOG"

# Проверка обязательных параметров
[ -z "$PG_HOST" ] && error "Не задан PG_HOST" "$BACKUP_LOG"
[ -z "$PG_PORT" ] && error "Не задан PG_PORT" "$BACKUP_LOG"
[ -z "$PG_USER" ] && error "Не задан PG_USER" "$BACKUP_LOG"
[ -z "$BACKUP_ROOT" ] && error "Не задан BACKUP_ROOT" "$BACKUP_LOG"
[ -z "$SSH_KEY" ] && export SSH_KEY="/home/andrey/.ssh/id_ed25519_backup"
[ -z "$SSH_USER" ] && export SSH_USER="andrey"
[ -z "$REMOTE_PGPASS" ] && export REMOTE_PGPASS="/home/andrey/.pgpass"

# Парсинг аргументов
IB_NAME=""
FORMAT=""
DRY_RUN=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ib) IB_NAME="$2"; shift 2 ;;
        --format) FORMAT="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        *) error "Неизвестный параметр: $1" "$BACKUP_LOG" ;;
    esac
done

[ -z "$IB_NAME" ] && error "Не указано имя ИБ (--ib <имя>)" "$BACKUP_LOG"
[[ ! "$FORMAT" =~ ^(dump|sql)$ ]] && error "Неверный формат (--format dump|sql)" "$BACKUP_LOG"

init_logs
log "Бэкап ИБ: $IB_NAME, формат: $FORMAT" "$BACKUP_LOG"
log "Сервер БД: $SSH_USER@$PG_HOST (pg_dump 15.10)" "$BACKUP_LOG"

# Создание директории бэкапа
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_DIR="$BACKUP_ROOT/$IB_NAME/$TIMESTAMP"
BACKUP_FILE="$BACKUP_DIR/backup.$FORMAT"

if [ "$DRY_RUN" = false ]; then
    sudo mkdir -p "$BACKUP_DIR"
    sudo chown usr1cv8:grp1cv8 "$BACKUP_DIR"
    check_free_space "$BACKUP_ROOT" 1048576 "$BACKUP_LOG"
else
    log "[DRY-RUN] Директория: $BACKUP_DIR" "$BACKUP_LOG"
fi

# Выполнение бэкапа НА СЕРВЕРЕ БД через SSH (без туннеля!)
if [ "$FORMAT" = "dump" ]; then
    log "Формат: .dump (pg_dump -Fc) — НЕ блокирует ИБ" "$BACKUP_LOG"
    
    if [ "$DRY_RUN" = false ]; then
        # Выполняем pg_dump на сервере БД, передаём результат напрямую в локальный файл
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
            "$SSH_USER@$PG_HOST" \
            "PGPASSFILE=$REMOTE_PGPASS pg_dump -Fc -h localhost -p $PG_PORT -U $PG_USER -d $IB_NAME" \
            | sudo -u usr1cv8 tee "$BACKUP_FILE" > /dev/null 2>&1
        
        [ ! -f "$BACKUP_FILE" ] && error "Файл бэкапа не создан: $BACKUP_FILE" "$BACKUP_LOG"
        sudo chmod 640 "$BACKUP_FILE"
        SIZE=$(du -h "$BACKUP_FILE" 2>/dev/null | cut -f1)
        log "✅ Бэкап создан: $BACKUP_FILE ($SIZE)" "$BACKUP_LOG"
    else
        log "[DRY-RUN] ssh $SSH_USER@$PG_HOST \"pg_dump -Fc -h localhost -p $PG_PORT -U $PG_USER -d $IB_NAME\" > $BACKUP_FILE" "$BACKUP_LOG"
    fi

elif [ "$FORMAT" = "sql" ]; then
    log "Формат: .sql.gz — МОЖЕТ блокировать ИБ" "$BACKUP_LOG"
    
    if [ "$DRY_RUN" = false ]; then
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
            "$SSH_USER@$PG_HOST" \
            "PGPASSFILE=$REMOTE_PGPASS pg_dump -h localhost -p $PG_PORT -U $PG_USER -d $IB_NAME" \
            | gzip | sudo -u usr1cv8 tee "$BACKUP_FILE" > /dev/null 2>&1
        
        [ ! -f "$BACKUP_FILE" ] && error "Файл бэкапа не создан: $BACKUP_FILE" "$BACKUP_LOG"
        sudo chmod 640 "$BACKUP_FILE"
        SIZE=$(du -h "$BACKUP_FILE" 2>/dev/null | cut -f1)
        log "✅ Бэкап создан: $BACKUP_FILE ($SIZE)" "$BACKUP_LOG"
    else
        log "[DRY-RUN] ssh $SSH_USER@$PG_HOST \"pg_dump -h localhost -p $PG_PORT -U $PG_USER -d $IB_NAME\" | gzip > $BACKUP_FILE" "$BACKUP_LOG"
    fi
fi

log "✅ Бэкап ИБ '$IB_NAME' завершён успешно" "$BACKUP_LOG"
