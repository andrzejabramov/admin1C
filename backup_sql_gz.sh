#!/bin/bash
source /opt/1cv8/scripts/.version

RAC="/opt/1cv8/x86_64/${VERSION}/rac"
CLUSTER_ID="60191967-9ef6-4a40-9d45-321bc9ca9e2f"
RAS_HOST="localhost:1545"
BACKUP_DIR="/var/backups/1c/sql_gz"
PG_HOST="10.129.0.27"
PG_USER="postgres"
PG_PASSFILE="/home/usr1cv8/.pgpass"
IB_LIST_FILE="/opt/1cv8/scripts/ib_list.conf"

if [ "$1" = "--auto" ]; then
    AUTO_MODE=1
else
    AUTO_MODE=0
fi

mkdir -p "$BACKUP_DIR"
echo "[$(date)] Начало резервного копирования (формат .sql.gz)..."

# Получаем пары UUID<tab>Имя
FULL_IB_PAIRS=$($RAC "$RAS_HOST" infobase summary list --cluster="$CLUSTER_ID" | awk '
    /^infobase : / { ib = $3 }
    /^name     : / { 
        gsub(/^"|"$/, "", $3); 
        print ib "\t" $3 
    }'
)

if [ -z "$FULL_IB_PAIRS" ]; then
    echo "[$(date)] ОШИБКА: не удалось получить список ИБ." >&2
    exit 1
fi

if [ "$AUTO_MODE" -eq 1 ]; then
    echo "[$(date)] Режим: АВТОМАТИЧЕСКИЙ (все ИБ)"
    BACKUP_LIST="$FULL_IB_PAIRS"
else
    if [ ! -f "$IB_LIST_FILE" ]; then
        echo "[$(date)] ОШИБКА: файл $IB_LIST_FILE не найден." >&2
        exit 1
    fi

    mapfile -t LINES < <(grep -v '^[[:space:]]*#' "$IB_LIST_FILE" | grep -v '^[[:space:]]*$')
    if [ ${#LINES[@]} -eq 0 ]; then
        echo "[$(date)] ОШИБКА: в $IB_LIST_FILE нет ни 'ALL', ни имён ИБ." >&2
        echo "       Укажите 'ALL' или перечислите ИБ (точно как в кластере)." >&2
        exit 1
    fi

    CLEAN_LINES=()
    for line in "${LINES[@]}"; do
        trimmed=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        if [ -n "$trimmed" ]; then
            CLEAN_LINES+=("$trimmed")
        fi
    done

    HAS_ALL=0
    REQUESTED_IBS=()
    for item in "${CLEAN_LINES[@]}"; do
        if [[ "$item" == "ALL" ]]; then
            HAS_ALL=1
        else
            REQUESTED_IBS+=("$item")
        fi
    done

    if [ "$HAS_ALL" -eq 1 ]; then
        BACKUP_LIST="$FULL_IB_PAIRS"
    else
        EXISTING_NAMES=()
        while IFS=$'\t' read -r uuid name; do
            [ -n "$name" ] && EXISTING_NAMES+=("$name")
        done <<< "$FULL_IB_PAIRS"

        FOUND_IBS=()
        MISSING_IBS=()
        for req in "${REQUESTED_IBS[@]}"; do
            FOUND=0
            for exist in "${EXISTING_NAMES[@]}"; do
                if [ "$req" = "$exist" ]; then
                    FOUND=1
                    FOUND_IBS+=("$req")
                    break
                fi
            done
            if [ "$FOUND" -eq 0 ]; then
                MISSING_IBS+=("$req")
            fi
        done

        if [ ${#MISSING_IBS[@]} -gt 0 ]; then
            echo "[$(date)] ОШИБКА: следующие ИБ не найдены (регистр важен!):" >&2
            for ib in "${MISSING_IBS[@]}"; do
                echo "  - '$ib'" >&2
            done
            echo "       Доступные ИБ (копируйте точно):" >&2
            printf '  - %s\n' "${EXISTING_NAMES[@]}" >&2
            exit 1
        fi

        BACKUP_LIST=""
        while IFS=$'\t' read -r uuid name; do
            for target in "${FOUND_IBS[@]}"; do
                if [ "$name" = "$target" ]; then
                    BACKUP_LIST+="$uuid$name"$'\n'
                    break
                fi
            done
        done <<< "$FULL_IB_PAIRS"
    fi
fi

# Выполняем бэкап с проверкой ошибок
while IFS=$'\t' read -r uuid name; do
    [ -z "$name" ] && continue
    DUMP_FILE="$BACKUP_DIR/${name}.sql.gz"
    echo "  → $name"
    if ! PGPASSFILE="$PG_PASSFILE" pg_dump -h "$PG_HOST" -U "$PG_USER" -d "$name" -Fp | gzip -9 > "$DUMP_FILE"; then
        echo "[$(date)] ОШИБКА: не удалось создать бэкап для '$name'" >&2
        exit 1
    fi
done <<< "$BACKUP_LIST"

echo "[$(date)] Завершено. Файлы в $BACKUP_DIR"
