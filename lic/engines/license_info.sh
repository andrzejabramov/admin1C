#!/bin/bash
# lic/engines/license_info.sh — Детализация лицензии через ring

set -euo pipefail

# Загрузка конфигурации
CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../config" && pwd)"
. "$CONFIG_DIR/lic.sh" || exit 1

if [ ! -x "$RING_PATH" ]; then
    echo "error=ring не найден: $RING_PATH" >&2
    exit 1
fi

if [ $# -ne 1 ]; then
    echo "error=Использование: $0 <регистрационный_номер>" >&2
    exit 1
fi

REGNUM="$1"
"$RING_PATH" license info --name "$REGNUM" 2>/dev/null