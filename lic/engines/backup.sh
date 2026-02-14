#!/bin/bash
# lic/engines/backup.sh — Резервная копия лицензий
set -euo pipefail

LICENSES_DIR="/var/1C/licenses"
BACKUP_ROOT="/home/usr1cv8/backups/licenses"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_ROOT/$TIMESTAMP"

mkdir -p "$BACKUP_PATH"
cp "$LICENSES_DIR"/*.lic "$BACKUP_PATH/" 2>/dev/null || true

echo "BACKUP_PATH=$BACKUP_PATH"
echo "BACKUP_COUNT=$(ls -1 "$BACKUP_PATH"/*.lic 2>/dev/null | wc -l || echo "0")"