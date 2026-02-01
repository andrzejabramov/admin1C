#!/bin/bash
# engines/utils.sh — общие утилиты для всех движков

# Конфигурация путей логов
SSL_LOG="/var/log/1c-admin/ssl.log"
BACKUP_LOG="/var/log/1c-admin/backup.log"
SESSIONS_LOG="/var/log/1c-admin/sessions.log"

# Создание директории логов (вызывается один раз при инициализации)
init_logs() {
    local log_dir="/var/log/1c-admin"
    sudo mkdir -p "$log_dir" 2>/dev/null || true
    sudo chown usr1cv8:grp1cv8 "$log_dir" 2>/dev/null || true
}

# Универсальное логирование
# Использование: log "сообщение" "$лог_файл"
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    local log_file="${2:-/dev/null}"
    
    echo "$msg" >&2
    if [ "$log_file" != "/dev/null" ]; then
        echo "$msg" | sudo tee -a "$log_file" > /dev/null
    fi
}

# Универсальная обработка ошибок
# Использование: error "сообщение" "$лог_файл"
error() {
    local msg="❌ ОШИБКА: $1"
    local log_file="${2:-/dev/null}"
    
    log "$msg" "$log_file"
    exit 1
}

# Получение cluster-id (кэшируется для повторных вызовов)
get_cluster_id() {
    if [ -z "$_CLUSTER_ID_CACHE" ]; then
        _CLUSTER_ID_CACHE=$(sudo -u usr1cv8 rac cluster list 2>/dev/null | awk '/cluster/ {print $2; exit}')
        if [ -z "$_CLUSTER_ID_CACHE" ]; then
            error "Не удалось определить cluster-id. Проверьте: sudo -u usr1cv8 rac cluster list" "$1"
        fi
    fi
    echo "$_CLUSTER_ID_CACHE"
}

# Проверка свободного места (в килобайтах)
# Использование: check_free_space "/путь" 1048576  # 1 ГБ
check_free_space() {
    local path="$1"
    local min_kb="${2:-1048576}"  # 1 ГБ по умолчанию
    
    local free_kb
    free_kb=$(df -k "$path" 2>/dev/null | awk 'NR==2 {print $4}')
    
    if [ -z "$free_kb" ] || [ "$free_kb" -lt "$min_kb" ]; then
        error "Недостаточно места на $path: свободно ${free_kb}K, требуется минимум ${min_kb}K" "$3"
    fi
}
