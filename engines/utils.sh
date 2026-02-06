#!/bin/bash
# engines/utils.sh — общие утилиты для всех движков
# ВНИМАНИЕ: библиотечные функции НЕ вызывают exit — только возвращают коды ошибок

# Конфигурация путей логов
SSL_LOG="/var/log/1c-admin/ssl.log"
BACKUP_LOG="/var/log/1c-admin/backup.log"
SESSIONS_LOG="/var/log/1c-admin/sessions.log"

# ==============================================================================
# Создание директории логов (вызывается один раз при инициализации)
# ==============================================================================
init_logs() {
    local log_dir="/var/log/1c-admin"
    sudo mkdir -p "$log_dir" 2>/dev/null || true
    sudo chown usr1cv8:grp1cv8 "$log_dir" 2>/dev/null || true
    sudo chmod 755 "$log_dir" 2>/dev/null || true
}

# ==============================================================================
# Универсальное логирование
# Использование: log "сообщение" "$лог_файл"
# ==============================================================================
log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    local log_file="${2:-/dev/null}"
    
    # Вывод в терминал (только если лог-файл не /dev/null)
    if [[ "$log_file" != "/dev/null" ]]; then
        echo "$msg" >&2
    fi
    
    # Запись в лог-файл
    if [[ -w "$log_file" ]] 2>/dev/null; then
        echo "$msg" | sudo tee -a "$log_file" > /dev/null 2>&1 || true
    elif [[ "$log_file" != "/dev/null" ]]; then
        # Если нет прав на запись — пытаемся через sudo
        echo "$msg" | sudo tee -a "$log_file" > /dev/null 2>&1 || true
    fi
}

# ==============================================================================
# Логирование ошибки БЕЗ выхода из скрипта
# Возвращает код 1 для удобства: if ! log_error "..."; then return 1; fi
# ==============================================================================
log_error() {
    local msg="❌ ОШИБКА: $1"
    local log_file="${2:-/dev/null}"
    log "$msg" "$log_file"
    return 1
}

# ==============================================================================
# Получение cluster-id (кэшируется для повторных вызовов)
# Возврат: 0 — успех, выводит cluster-id; 1 — ошибка
# ==============================================================================
get_cluster_id_safe() {
    if [ -z "${_CLUSTER_ID_CACHE:-}" ]; then
        _CLUSTER_ID_CACHE=$(sudo -u usr1cv8 rac cluster list 2>/dev/null | awk '/cluster/ {print $2; exit}')
        if [ -z "$_CLUSTER_ID_CACHE" ]; then
            log_error "Не удалось определить cluster-id. Проверьте: sudo -u usr1cv8 rac cluster list" "$1"
            return 1
        fi
    fi
    echo "$_CLUSTER_ID_CACHE"
    return 0
}

# ==============================================================================
# Проверка свободного места (в килобайтах)
# Использование: check_free_space "/путь" 1048576  # 1 ГБ
# Возврат: 0 — достаточно места; 1 — недостаточно
# ==============================================================================
check_free_space() {
    local path="$1"
    local min_kb="${2:-1048576}"  # 1 ГБ по умолчанию
    local log_file="${3:-/dev/null}"
    
    local free_kb
    free_kb=$(df -k "$path" 2>/dev/null | awk 'NR==2 {print $4}')
    
    if [ -z "$free_kb" ] || [ "$free_kb" -lt "$min_kb" ]; then
        log_error "Недостаточно места на $path: свободно ${free_kb}K, требуется минимум ${min_kb}K" "$log_file"
        return 1
    fi
    return 0
}

# ==============================================================================
# Проверка существования ИБ в кластере 1С
# Аргументы:
#   $1 — имя ИБ (может содержать пробелы по краям)
#   $2 — путь к лог-файлу (опционально)
# Возврат:
#   0 — ИБ существует, выводит очищенное имя ИБ на stdout
#   126 — пустое имя ИБ
#   127 — ИБ не найдена
#   1 — кластер недоступен или системная ошибка
# ==============================================================================
validate_ib_exists() {
    local ib_name_raw="$1"
    local log_file="${2:-/dev/null}"
    local ib_name

    # Обрезаем пробелы (защита от копипаста с пробелами)
    ib_name="$(echo "$ib_name_raw" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

    # Проверка пустого имени
    if [[ -z "$ib_name" ]]; then
        log_error "Имя информационной базы не указано" "$log_file"
        return 126
    fi

    # Получаем cluster-id один раз (кэшируется в get_cluster_id_safe)
    local cluster_id
    cluster_id=$(get_cluster_id_safe "$log_file") || return 1

    # Получаем список ИБ из кластера
    local ib_list
    ib_list=$(sudo -u usr1cv8 rac infobase list --cluster="$cluster_id" 2>/dev/null)

    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log_error "Кластер 1С недоступен (код $exit_code). Проверьте: systemctl status ragent" "$log_file"
        return 1
    fi

    # Ищем точное совпадение по имени (регистронезависимо)
    if ! echo "$ib_list" | grep -qi "name=$ib_name"; then
        log_error "ИБ '$ib_name' не найдена в кластере $cluster_id" "$log_file"
        
        # Выводим список доступных ИБ (макс. 5 для краткости в логе)
        local count=0
        while IFS= read -r line; do
            [[ -z "$line" ]] && continue
            local name
            name=$(echo "$line" | grep -oP 'name=\K[^,]+' 2>/dev/null || echo "безымянная")
            log "   • $name" "$log_file"
            ((count++))
            [[ $count -ge 5 ]] && break
        done < <(echo "$ib_list" | grep -E "^infobase")
        
        local total_count
        total_count=$(echo "$ib_list" | grep -c "^infobase" 2>/dev/null || echo "0")
        if [[ $total_count -gt 5 ]]; then
            log "   ... и ещё $((total_count - 5)) ИБ (полный список: sudo -u usr1cv8 rac infobase list --cluster=$cluster_id)" "$log_file"
        fi
        
        return 127
    fi

    # Возвращаем очищенное имя для дальнейшего использования
    echo "$ib_name"
    return 0
}