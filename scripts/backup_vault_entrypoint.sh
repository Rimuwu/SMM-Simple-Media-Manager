#!/bin/sh
# Entrypoint для backup с загрузкой переменных из Vault

export VAULT_ADDR=${VAULT_ADDR:-http://vault:8200}

# Читаем токен из Docker secret
if [ -f "/run/secrets/vault_token" ]; then
    export VAULT_TOKEN=$(cat /run/secrets/vault_token)
    echo "🔐 Backup: Токен загружен из Docker secret"
else
    echo "❌ Backup: Vault token не найден!"
    exit 1
fi

echo "🔐 Backup: Загрузка переменных из Vault..."

# Установка необходимых пакетов
apk add --no-cache python3 py3-pip

# Установка hvac
pip3 install hvac --break-system-packages -q

# Загрузка переменных из Vault и экспорт
eval "$(python3 << 'EOF'
import os, sys, hvac

try:
    client = hvac.Client(
        url=os.getenv("VAULT_ADDR"), 
        token=os.getenv("VAULT_TOKEN")
    )
    
    if not client.is_authenticated():
        print("echo '❌ Не удалось аутентифицироваться в Vault'", file=sys.stderr)
        sys.exit(1)
    
    response = client.secrets.kv.v2.read_secret_version(
        path="smm", 
        mount_point="secret",
        raise_on_deleted_version=False
    )
    secrets = response["data"]["data"]
    
    # Экспортируем переменные для backup
    for key, value in secrets.items():
        if key in ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]:
            print(f"export {key}='{value}'")
    
    print("echo '✓ Backup переменные загружены из Vault'", file=sys.stderr)
    
except Exception as e:
    print(f"echo '❌ Ошибка загрузки из Vault: {e}'", file=sys.stderr)
    sys.exit(1)
EOF
)"

if [ $? -ne 0 ]; then
    echo "❌ Не удалось загрузить переменные из Vault"
    exit 1
fi

echo "💾 Запуск backup сервиса..."

# Запуск backup в цикле
while true; do
    python3 /backup_postgres.py
    echo "⏰ Следующий backup через 24 часа..."
    sleep 86400
done
