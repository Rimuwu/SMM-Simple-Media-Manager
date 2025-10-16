"""
Конфигурационные настройки для Kaiten API клиента.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class KaitenConfig:
    """Конфигурация для Kaiten API клиента."""
    
    # API Settings
    BASE_URL: str = "https://api.kaiten.ru"
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds
    DEFAULT_TIMEOUT = 30  # seconds
    API_VERSION = "v1"

    # Rate Limiting (согласно документации Kaiten)
    LIMIT_PER_SEC = 3

    # API Endpoints
    # Основные ресурсы
    ENDPOINT_SPACES: str = "/spaces"
    ENDPOINT_BOARDS: str = "/spaces/{space_id}/boards"
    ENDPOINT_COLUMNS: str = "/boards/{board_id}/columns"
    ENDPOINT_LANES: str = "/boards/{board_id}/lanes"
    ENDPOINT_CARDS: str = "/cards"
    ENDPOINT_TAGS: str = "/tags"
    ENDPOINT_USERS: str = "/users"
    ENDPOINT_CURRENT_USER: str = "/users/current"
    
    # Карточки и связанные ресурсы
    ENDPOINT_CARD_COMMENTS: str = "/cards/{card_id}/comments"
    ENDPOINT_CARD_FILES: str = "/cards/{card_id}/files"
    ENDPOINT_CARD_MEMBERS: str = "/cards/{card_id}/members"
    ENDPOINT_CARD_CHILDREN: str = "/cards/{card_id}/children"
    ENDPOINT_CARD_TIME_LOGS: str = "/cards/{card_id}/time-logs"
    ENDPOINT_CARD_CHECKLISTS: str = "/cards/{card_id}/checklists"
    
    # Чеклисты
    ENDPOINT_CHECKLISTS: str = "/checklists"
    ENDPOINT_CHECKLIST_ITEMS: str = "/cards/{card_id}/checklists/{checklist_id}/items"
    
    # Файлы
    ENDPOINT_FILES: str = "/files"
    
    # Типы карточек
    ENDPOINT_CARD_TYPES: str = "/card-types"
    
    # Пользовательские свойства
    ENDPOINT_CUSTOM_PROPERTIES: str = "/company/custom-properties"

    @staticmethod
    def get_base_url(domain: str) -> str:
        """Формирует базовый URL для API."""
        if not domain:
            raise ValueError("Domain не может быть пустым")
        
        # Убираем возможные протоколы и слеши
        domain = domain.strip().replace("https://", "").replace("http://", "").rstrip("/")
        
        # Добавляем .kaiten.ru если это не полный домен
        if not domain.endswith(".kaiten.ru"):
            domain = f"{domain}.kaiten.ru"
        
        return f"https://{domain}/api/{KaitenConfig.API_VERSION}"


class KaitenCredentials:
    """Управление учетными данными для Kaiten API."""
    
    def __init__(self, domain: str, token: str):
        if not domain or not domain.strip():
            raise ValueError("Domain обязателен")
        if not token or not token.strip():
            raise ValueError("API token обязателен")
        
        self._domain = domain.strip()
        self._token = token.strip()
    
    @property
    def domain(self) -> str:
        return self._domain
    
    @property
    def token(self) -> str:
        return self._token
    
    @property
    def base_url(self) -> str:
        return KaitenConfig.get_base_url(self._domain)
    
    def get_headers(self) -> dict:
        """Возвращает заголовки для HTTP запросов."""
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._token}',
        }
    
    def get_upload_headers(self) -> dict:
        """Возвращает заголовки для загрузки файлов."""
        return {
            'Authorization': f'Bearer {self._token}',
        }