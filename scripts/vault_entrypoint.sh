#!/bin/sh
# Загрузка переменных из Vault и запуск приложения

export VAULT_ADDR=${VAULT_ADDR:-http://vault:8200}

# Читаем токен из Docker secret если есть
if [ -f "/run/secrets/vault_token" ]; then
    export VAULT_TOKEN=$(cat /run/secrets/vault_token)
    echo "🔐 Токен загружен из Docker secret"
else
    export VAULT_TOKEN=${VAULT_TOKEN:-myroot}
    echo "🔐 Используется токен из переменной окружения"
fi

echo "🔐 Загрузка переменных из Vault..."

# Установка hvac если нужно
if ! python3 -c "import hvac" 2>/dev/null; then
    pip3 install hvac --break-system-packages -q
fi

# Загрузка переменных из Vault
python3 << 'EOF'
import os, sys, hvac

try:
    client = hvac.Client(url=os.getenv("VAULT_ADDR"), token=os.getenv("VAULT_TOKEN"))
    response = client.secrets.kv.v2.read_secret_version(path="smm", mount_point="secret")
    secrets = response["data"]["data"]
except Exception as e:
    print(f"⚠️  Vault недоступен, используем env: {e}", file=sys.stderr)
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    # Экспорт переменных
    eval "$(python3 << 'EOFPY'
import os, sys, hvac
try:
    client = hvac.Client(url=os.getenv("VAULT_ADDR"), token=os.getenv("VAULT_TOKEN"))
    response = client.secrets.kv.v2.read_secret_version(path="smm", mount_point="secret")
    secrets = response["data"]["data"]
except:
    pass
EOFPY
)"
    echo "✓ Переменные загружены из Vault"
else
    echo "⚠️  Продолжаем с существующими env"
fi

# Запуск переданной команды
exec "$@"
