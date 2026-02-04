#!/bin/bash
# engines/db_config.sh — конфигурация подключения к СУБД
# Скопируйте в db_config.sh и укажите реальные параметры
# ⚠️ Этот файл НЕ должен попадать в Git (добавлен в .gitignore)

# Параметры подключения к PostgreSQL
export PG_HOST="10.129.0.27"      # IP-адрес сервера БД
export PG_PORT="5432"             # Порт PostgreSQL
export PG_USER="postgres"         # Пользователь БД
export PGPASS_FILE="/home/usr1cv8/.pgpass"  # Путь к файлу паролей
export BACKUP_ROOT="/var/backups/1c"        # Корень для хранения бэкапов

# SSH-доступ к серверу БД
export SSH_KEY="/opt/1cv8/.ssh/id_ed25519_backup"
export SSH_USER="andrey"

# Путь к .pgpass НА СЕРВЕРЕ БД
export REMOTE_PGPASS="/home/andrey/.pgpass"
