import os, sys, hvac

vault_addr = os.getenv("VAULT_ADDR") or input("Введите VAULT_ADDR (по умолчанию http://127.0.0.1:8200): ") or "http://127.0.0.1:8200"
vault_token = os.getenv("VAULT_TOKEN") or input("Введите VAULT_TOKEN (по умолчанию myroot): ") or "myroot"

# Подключение
client = hvac.Client(url=vault_addr, token=vault_token)
if not client.is_authenticated():
    print("❌ Ошибка аутентификации")
    sys.exit(1)

# Загрузка .env
env_vars = {}
with open("./.env", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if value:
                env_vars[key] = value

# Импорт
client.secrets.kv.v2.create_or_update_secret(
    path="smm",
    secret=env_vars,
    mount_point="secret"
)

print(f"✓ Импортировано {len(env_vars)} переменных в Vault")
for key in sorted(env_vars.keys()):
    print(f"  • {key}")
