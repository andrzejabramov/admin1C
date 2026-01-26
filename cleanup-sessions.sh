#!/bin/bash
source /opt/1cv8/scripts/.version

CLUSTER_ID="60191967-9ef6-4a40-9d45-321bc9ca9e2f"
RAC_PATH="/opt/1cv8/x86_64/${VERSION}/rac"
USER_1C="usr1cv8"
INACTIVE_TIMEOUT_MIN=60
RAS_HOST="localhost:1545"
LOG_FILE="/var/log/1c-session-cleanup.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

if [ ! -x "$RAC_PATH" ]; then
    log "ERROR: rac not found at $RAC_PATH"
    exit 1
fi

SESSIONS_RAW=$(sudo -u "$USER_1C" "$RAC_PATH" "$RAS_HOST" session list --cluster="$CLUSTER_ID" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$SESSIONS_RAW" ]; then
    log "ERROR: failed to get session list"
    exit 1
fi

echo "$SESSIONS_RAW" | while IFS= read -r line; do
    if [[ $line == session* ]]; then
        SESSION_ID=$(echo "$line" | awk '{print $3}')
        continue
    fi
    if [[ $line == last-active-at* ]]; then
        LAST_ACTIVE=$(echo "$line" | cut -d' ' -f3-)
        if [ -z "$LAST_ACTIVE" ] || [[ $LAST_ACTIVE == *"not defined"* ]]; then
            continue
        fi
        LAST_TS=$(date -d "$LAST_ACTIVE" +%s 2>/dev/null)
        NOW_TS=$(date +%s)
        DIFF_MIN=$(( (NOW_TS - LAST_TS) / 60 ))
        if [ $? -eq 0 ] && [ $DIFF_MIN -gt $INACTIVE_TIMEOUT_MIN ]; then
            log "TERMINATING session $SESSION_ID (inactive for ${DIFF_MIN} min)"
            sudo -u "$USER_1C" "$RAC_PATH" "$RAS_HOST" session terminate --cluster="$CLUSTER_ID" "$SESSION_ID" >/dev/null 2>&1
        fi
    fi
done

log "Cleanup completed"
