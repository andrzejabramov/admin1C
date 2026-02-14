#!/bin/bash
LICENSES_DIR="/var/1C/licenses"
TOTAL_USERS=0
TOTAL_SERVERS=0

for lic_file in "$LICENSES_DIR"/*.lic; do
    [ -f "$lic_file" ] || continue
    
    type_line=$(grep "Тип лицензии" "$lic_file" 2>/dev/null | head -1)
    users_line=$(grep "Количество пользователей" "$lic_file" 2>/dev/null | head -1)
    
    TYPE=$(echo "$type_line" | awk -F': ' '{print $2}' | tr -d '\r\n' || echo "")
    USERS=$(echo "$users_line" | awk -F': ' '{print $2}' | tr -d '\r\n' || echo "0")
    
    if [[ "$TYPE" == *"сервер"* ]]; then
        TOTAL_SERVERS=$((TOTAL_SERVERS + 1))
    else
        TOTAL_USERS=$((TOTAL_USERS + USERS))
    fi
done

ACTIVE_SESSIONS=$(pgrep -u usr1cv8 rphost 2>/dev/null | wc -l || echo "0")

echo "TOTAL_USERS=$TOTAL_USERS"
echo "TOTAL_SERVERS=$TOTAL_SERVERS"
echo "ACTIVE_SESSIONS=$ACTIVE_SESSIONS"
