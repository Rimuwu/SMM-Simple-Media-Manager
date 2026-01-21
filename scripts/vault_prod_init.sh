#!/bin/sh
set -e

# Запускаем Vault в фоне
vault server -config=/vault/config/vault.hcl &
VAULT_PID=$!

# Ждем запуска Vault
sleep 3

export VAULT_ADDR='http://127.0.0.1:8200'

# Проверяем инициализирован ли Vault через API
INIT_STATUS=$(vault status -format=json 2>/dev/null | grep -o '"initialized":\s*[a-z]*' | cut -d':' -f2 | tr -d ' ')

if [ "$INIT_STATUS" != "true" ]; then
    echo "🔧 Initializing Vault for the first time..."
    
    # Инициализация с 1 ключом и порогом 1
    vault operator init -key-shares=1 -key-threshold=1 -format=json > /tmp/vault-init.json
    
    # Извлекаем unseal key и root token через awk
    UNSEAL_KEY=$(awk -F'"' '/"unseal_keys_b64"/{f=1;next} f&&/"/{print $2;exit}' /tmp/vault-init.json)
    ROOT_TOKEN=$(awk -F'"' '/"root_token"/{print $4}' /tmp/vault-init.json)
    
    echo "DEBUG: UNSEAL_KEY: $UNSEAL_KEY"
    echo "DEBUG: ROOT_TOKEN: $ROOT_TOKEN"
    
    # Сохраняем в host-систему
    echo "$UNSEAL_KEY" > /vault/secrets/vault_unseal_key.txt
    echo "$ROOT_TOKEN" > /vault/secrets/vault_token.txt
    chmod 600 /vault/secrets/vault_unseal_key.txt /vault/secrets/vault_token.txt
    
    # Unseal Vault (передаем ключ как аргумент)
    vault operator unseal "$UNSEAL_KEY"
    
    # Авторизуемся и включаем KV v2
    vault login "$ROOT_TOKEN"
    vault secrets enable -version=2 -path=secret kv || true
    
    echo "✅ Vault initialized! Keys saved to ./secrets/"
    echo "   Root Token: $ROOT_TOKEN"
    echo "   Unseal Key: $UNSEAL_KEY"
else
    echo "🔓 Unsealing existing Vault..."
    
    # Читаем unseal key из файла
    if [ -f "/vault/secrets/vault_unseal_key.txt" ]; then
        UNSEAL_KEY=$(cat /vault/secrets/vault_unseal_key.txt)
        vault operator unseal "$UNSEAL_KEY"
        echo "✅ Vault unsealed successfully!"
    else
        echo "❌ Error: Unseal key not found!"
        kill $VAULT_PID
        exit 1
    fi
fi

# Ждем завершения процесса Vault
wait $VAULT_PID
