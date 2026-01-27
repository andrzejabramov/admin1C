#!/bin/bash
# engines/ssl.sh — безопасная обёртка для управления SSL-сертификатами
# Автоматически определяет правильный путь к сертификату через certbot

set -e

DOMAIN="${SSL_DOMAIN:-bases.atotx.ru}"
LOG_FILE="/var/log/1c-admin/ssl.log"

# Создаём директорию для логов
sudo mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
sudo chown usr1cv8:grp1cv8 "$(dirname "$LOG_FILE")" 2>/dev/null || true

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [SSL] $1"
    echo "$msg" >&2  # Лог в stderr, чтобы не мешать выводу пути
    echo "$msg" | sudo tee -a "$LOG_FILE" > /dev/null
}

error() {
    log "❌ ОШИБКА: $1"
    exit 1
}

# Автоматическое определение пути к сертификату (возвращает ТОЛЬКО путь в stdout)
find_cert_path() {
    # Способ 1: через вывод certbot certificates
    local cert_name
    cert_name=$(sudo certbot certificates 2>/dev/null | \
        grep -B2 "Domains:.*$DOMAIN" | \
        grep "Certificate Name:" | \
        head -1 | \
        sed 's/.*Certificate Name: //; s/ *$//')
    
    if [ -n "$cert_name" ]; then
        local path="/etc/letsencrypt/live/$cert_name"
        if sudo test -d "$path"; then
            echo "$path"
            return 0
        fi
    fi
    
    # Способ 2: прямой поиск в /etc/letsencrypt/live/
    local candidates
    candidates=$(sudo find /etc/letsencrypt/live/ -maxdepth 1 -type d -name "*$DOMAIN*" 2>/dev/null | head -1)
    
    if [ -n "$candidates" ] && sudo test -d "$candidates"; then
        echo "$candidates"
        return 0
    fi
    
    return 1
}

check_expiry() {
    local cert_path
    cert_path=$(find_cert_path) || error "Сертификат для домена $DOMAIN не найден. Проверьте: sudo certbot certificates"
    
    log "Найден сертификат: $(basename "$cert_path")"
    
    local cert_file="$cert_path/fullchain.pem"
    if ! sudo test -f "$cert_file"; then
        error "Файл сертификата не найден: $cert_file"
    fi
    
    # Читаем дату окончания через sudo
    local end_date_str
    end_date_str=$(sudo openssl x509 -enddate -noout -in "$cert_file" 2>/dev/null | cut -d= -f2)
    [ -n "$end_date_str" ] || error "Не удалось прочитать дату окончания сертификата"
    
    # Конвертируем дату
    local end_date
    if date -d "$end_date_str" +%s >/dev/null 2>&1; then
        end_date=$(date -d "$end_date_str" +%s)
    else
        end_date=$(date -j -f "%b %d %T %Y %Z" "$end_date_str" +%s 2>/dev/null || echo "0")
    fi
    
    [ "$end_date" != "0" ] || error "Не удалось распарсить дату: $end_date_str"
    
    local now=$(date +%s)
    local days_left=$(( (end_date - now) / 86400 ))
    
    log "Сертификат действителен до: $end_date_str"
    log "Осталось дней: $days_left"
    
    if [ $days_left -lt 0 ]; then
        log "⚠️ СЕРТИФИКАТ ПРОСРОЧЕН!"
        exit 1
    elif [ $days_left -lt 30 ]; then
        log "⚠️ Внимание: сертификат истекает через $days_left дней!"
        exit 1
    else
        log "✅ Сертификат действителен"
        exit 0
    fi
}

status() {
    log "Статус сертификатов:"
    sudo certbot certificates 2>&1
}

renew() {
    local dry_run="${1:-}"
    
    log "Запуск обновления сертификата для $DOMAIN..."
    
    if [ -z "$dry_run" ]; then
        log "Тестовое обновление (--dry-run)..."
        if ! sudo certbot renew --quiet --dry-run 2>&1 | while IFS= read -r line; do log "$line"; done; then
            error "Тестовое обновление не удалось"
        fi
        log "✅ Тестовое обновление успешно"
    fi
    
    if [ -z "$dry_run" ]; then
        log "Реальное обновление..."
        if sudo certbot renew --quiet 2>&1 | while IFS= read -r line; do log "$line"; done; then
            log "✅ Сертификат обновлён"
        else
            error "Ошибка реального обновления"
        fi
    else
        log "⚠️ Пропускаем реальное обновление (режим --dry-run)"
        exit 0
    fi
    
    log "Перезагрузка Apache..."
    if sudo systemctl reload apache2 2>&1 | while IFS= read -r line; do log "$line"; done; then
        log "✅ Apache перезагружен"
    else
        error "Ошибка перезагрузки Apache"
    fi
}

case "$1" in
    check) check_expiry ;;
    status) status ;;
    renew)
        if [ "$2" = "--dry-run" ]; then
            renew "--dry-run"
        else
            renew
        fi
        ;;
    *) 
        echo "Использование: $0 {check|status|renew [--dry-run]}" >&2
        exit 1
        ;;
esac
