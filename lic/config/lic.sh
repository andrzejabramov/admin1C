# lic/config/lic.sh
# Конфигурация домена лицензий

LICENSES_DIR="/var/1C/licenses"
RING_PATH="/opt/1C/1CE/components/1c-enterprise-ring-0.19.2+6-x86_64/ring"
BACKUP_ROOT="/home/usr1cv8/backups/licenses"

# Критически важно для работы ring
export JAVA_HOME="/usr/lib/jvm/java-8-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"