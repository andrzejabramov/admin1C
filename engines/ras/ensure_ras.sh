#!/bin/bash
# ensure_ras.sh — гарантирует запуск RAS на порту 1545
# Возвращает: 0 = успех, 1 = ошибка

set -e

source /opt/1cv8/scripts/.version
RAS_BIN="/opt/1cv8/x86_64/${VERSION}/ras"
RAS_PORT=1545
RAS_USER="usr1cv8"
TIMEOUT=5

# Получаем PID процесса ras на порту
get_ras_pid() {
    sudo ss -tulnp 2>/dev/null | \
        grep -E ":[[:space:]]*${RAS_PORT}[^0-9]" | \
        grep -oP 'pid=\K[0-9]+' | \
        head -n1
}

# Проверка: запущен ли именно наш ras?
is_ras_running() {
    PID=$(get_ras_pid)
    if [ -n "$PID" ]; then
        CMDLINE=$(sudo cat /proc/${PID}/cmdline 2>/dev/null | tr '\0' ' ' || echo "")
        echo "$CMDLINE" | grep -q "$(basename $RAS_BIN)" 2>/dev/null
        return $?
    fi
    return 1
}

# Запуск RAS
start_ras() {
    echo "[$(date)] Запуск RAS на порту ${RAS_PORT}..." >&2
    
    # Если порт занят — останавливаем старый процесс
    if ! is_ras_running && [ -n "$(get_ras_pid)" ]; then
        echo "[$(date)] Порт ${RAS_PORT} занят чужим процессом — останавливаем..." >&2
        /opt/1cv8/scripts/engines/ras/stop_ras.sh >/dev/null 2>&1 || true
        sleep 2
    fi
    
    # Запуск
    sudo -u "$RAS_USER" HOME=/home/"$RAS_USER" LANG=ru_RU.UTF-8 \
        "$RAS_BIN" cluster --port="$RAS_PORT" >/dev/null 2>&1 &
    
    sleep 1
    
    # Ожидание
    for i in $(seq 1 $TIMEOUT); do
        if is_ras_running; then
            echo "[$(date)] RAS запущен" >&2
            return 0
        fi
        sleep 1
    done
    
    echo "[$(date)] ОШИБКА: RAS не запустился за ${TIMEOUT} секунд" >&2
    return 1
}

# Основная логика
if is_ras_running; then
    echo "[$(date)] RAS уже запущен" >&2
    exit 0
else
    start_ras || exit 1
    exit 0
fi
