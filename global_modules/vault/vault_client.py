import os
import hvac


class VaultClient:
    def __init__(self, vault_addr=None, vault_token=None):
        self.vault_addr = vault_addr or os.getenv('VAULT_ADDR', 'http://vault:8200')
        self.vault_token = vault_token or os.getenv('VAULT_TOKEN')
        
        if not self.vault_token:
            raise ValueError("VAULT_TOKEN not set")
        
        self.client = hvac.Client(url=self.vault_addr, token=self.vault_token)
        
        if not self.client.is_authenticated():
            raise Exception("Failed to authenticate with Vault")
    
    def get(self, key, default=None):
        """Получить значение из Vault"""
        try:
            secret = self.client.secrets.kv.v2.read_secret_version(
                path='smm',
                mount_point='secret'
            )
            return secret['data']['data'].get(key, default)
        except Exception as e:
            print(f"Warning: Failed to read from Vault: {e}")
            return default


# Глобальный клиент Vault (инициализируется лениво)
_vault_client = None


def _get_vault_client():
    """Получить или создать глобальный клиент Vault"""
    global _vault_client
    if _vault_client is None:
        try:
            _vault_client = VaultClient()
        except Exception as e:
            print(f"Warning: Failed to initialize Vault client: {e}")
            _vault_client = False  # Отмечаем как неудачную попытку
    return _vault_client if _vault_client else None


def vault_getenv(key, default=None):
    """
    Получить переменную окружения из Vault или fallback на os.getenv
    
    Использование:
        from vault.vault_client import vault_getenv as getenv
        db_password = getenv('POSTGRES_PASSWORD')
    """
    # Сначала пробуем Vault
    client = _get_vault_client()
    if client:
        value = client.get(key, default=None)
        if value is not None:
            return value
    
    # Fallback на os.getenv
    return os.getenv(key, default)
