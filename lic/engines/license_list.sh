#!/bin/bash
LICENSES_DIR="/var/1C/licenses"

if [ ! -d "$LICENSES_DIR" ]; then
    echo "error=Каталог лицензий не найден: $LICENSES_DIR" >&2
    exit 1
fi

echo -e "regnum\tfilename\ttype\tusers\tstatus"

for lic_file in "$LICENSES_DIR"/*.lic; do
    [ -f "$lic_file" ] || continue
    
    filename=$(basename "$lic_file")
    
    regnum_line=$(grep "Регистрационный номер" "$lic_file" 2>/dev/null | head -1)
    type_line=$(grep "Тип лицензии" "$lic_file" 2>/dev/null | head -1)
    users_line=$(grep "Количество пользователей" "$lic_file" 2>/dev/null | head -1)
    
    regnum=$(echo "$regnum_line" | awk -F': ' '{print $2}' | tr -d '\r\n' || echo "неизвестно")
    type=$(echo "$type_line" | awk -F': ' '{print $2}' | tr -d '\r\n' || echo "неизвестно")
    users=$(echo "$users_line" | awk -F': ' '{print $2}' | tr -d '\r\n' || echo "0")
    
    regnum="${regnum%G0}"
    
    echo -e "$regnum\t$filename\t$type\t$users\tактивна"
done
