#!/bin/bash
# lic/engines/license_detail.sh — Извлечение деталей лицензии через grep/awk
# Аргумент: регистрационный номер (с или без суффикса G0)

set -euo pipefail

LICENSES_DIR="/var/1C/licenses"
REGNUM="$1"

# Нормализуем номер: добавляем G0 если его нет
if [[ ! "$REGNUM" =~ G0$ ]]; then
    REGNUM="${REGNUM}G0"
fi

# Ищем файл через grep
FOUND_FILE=""
for lic_file in "$LICENSES_DIR"/*.lic; do
    [ -f "$lic_file" ] || continue
    if grep -q "$REGNUM" "$lic_file" 2>/dev/null; then
        FOUND_FILE="$lic_file"
        break
    fi
done

if [ -z "$FOUND_FILE" ]; then
    echo "error=Лицензия $REGNUM не найдена" >&2
    exit 1
fi

# Извлекаем поля из файла (последние 30 строк — там метаданные)
tail -n 30 "$FOUND_FILE" | while IFS= read -r line; do
    line_clean=$(echo "$line" | tr -d '\r')
    
    if [[ "$line_clean" == *"Регистрационный номер:"* ]]; then
        echo "Регистрационный номер=$(echo "$line_clean" | awk -F': ' '{print $2}' | xargs)"
    elif [[ "$line_clean" == *"Тип лицензии:"* ]]; then
        echo "Тип лицензии=$(echo "$line_clean" | awk -F': ' '{print $2}' | xargs)"
    elif [[ "$line_clean" == *"Количество пользователей:"* ]]; then
        echo "Количество пользователей=$(echo "$line_clean" | awk -F': ' '{print $2}' | xargs)"
    elif [[ "$line_clean" == *"Наименование продукта:"* ]]; then
        echo "Наименование продукта=$(echo "$line_clean" | awk -F': ' '{print $2}' | xargs)"
    elif [[ "$line_clean" == *"Срок действия:"* ]]; then
        echo "Срок действия=$(echo "$line_clean" | awk -F': ' '{print $2}' | xargs)"
    fi
done
