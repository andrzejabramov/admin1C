#!/bin/bash
CLOUD_REMOTE="mailru"
CLOUD_PATH="1c_backups"
LOCAL_DIR="/var/backups/1c"

echo "[$(date)] Начало отправки в облако..."
rclone copy "$LOCAL_DIR" "$CLOUD_REMOTE:$CLOUD_PATH/" --log-file=/var/log/rclone_1c.log
echo "[$(date)] Отправка завершена."
