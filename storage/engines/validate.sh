#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/config/storage.sh"
[[ ! -f "$CONFIG" ]] && { echo "error=Конфиг $CONFIG не найден" >&2; exit 1; }
source "$CONFIG"

errors=()
warnings=()

if [[ ! -d "$BACKUP_DIR" ]]; then
  errors+=("Каталог $BACKUP_DIR не существует")
else
  if ! mountpoint -q "$BACKUP_DIR" 2>/dev/null; then
    warnings+=("Каталог $BACKUP_DIR не является точкой монтирования")
  fi
  
  if ! sudo -n -u usr1cv8 test -r "$BACKUP_DIR" 2>/dev/null; then
    warnings+=("Нет прав чтения для usr1cv8 в $BACKUP_DIR")
  fi
  
  ib_list=$(find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d ! -name "lost+found" 2>/dev/null || true)
  ib_count=$(echo "$ib_list" | grep -c '^' || echo "0")
  if [[ "$ib_count" -eq 0 ]]; then
    warnings+=("Не найдено каталогов информационных баз в $BACKUP_DIR")
  fi
  
  zero_list=$(find "$BACKUP_DIR" -type f \( -name "*.dump" -o -name "*.dt" -o -name "*.sql.gz" -o -name "backup.dump" -o -name "backup.sql*" \) -size 0 2>/dev/null || true)
  zero_size=$(echo "$zero_list" | grep -c '^' || echo "0")
  if [[ "$zero_size" -gt 0 ]]; then
    warnings+=("Найдено $zero_size файлов нулевого размера")
  fi
fi

echo "valid=$( [[ ${#errors[@]} -eq 0 ]] && echo "true" || echo "false" )"
echo "error_count=${#errors[@]}"
echo "warning_count=${#warnings[@]}"

for err in "${errors[@]}"; do echo "error=$err"; done
for warn in "${warnings[@]}"; do echo "warning=$warn"; done