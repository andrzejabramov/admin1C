#!/bin/bash
# stop_ras.sh — останавливает RAS на порту 1545
# Возвращает: 0 = успех, 1 = ошибка

set -e

RAS_PORT=1545

# Получаем PID процесса, слушающего порт 1545
get_ras_pid() {
    sudo ss -tulnp 2>/dev/null | \
        grep -E ":[[:space:]]*${RAS_PORT}[^0-9]" | \
        grep -oP 'pid=\K[0-9]+' | \
        head -n1
}

# Основная логика
PID=$(get_ras_pid)

if [ -z "$PID" ]; then
    echo "[$(date)] RAS не запущен (порт ${RAS_PORT} свободен)" >&2
    exit 0
fi

echo "[$(date)] Остановка RAS (PID=$PID)..." >&2

# SIGTERM
sudo kill "$PID" 2>/dev/null || true
sleep 2

# Проверка
if ! kill -0 "$PID" 2>/dev/null; then
    echo "[$(date)] RAS остановлен" >&2
    exit 0
fi

# SIGKILL
echo "[$(date)] Принудительная остановка RAS (PID=$PID)..." >&2
sudo kill -9 "$PID" 2>/dev/null || true
sleep 2

# Финальная проверка
if [ -z "$(get_ras_pid)" ]; then
    echo "[$(date)] RAS остановлен (принудительно)" >&2
    exit 0
else
    echo "[$(date)] ОШИБКА: не удалось остановить RAS (PID=$PID)" >&2
    exit 1
fi
