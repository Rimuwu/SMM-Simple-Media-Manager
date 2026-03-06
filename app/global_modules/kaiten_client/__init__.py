"""
Kaiten API Client Library

Простой и удобный клиент для работы с Kaiten API.
Предоставляет все необходимые методы для управления карточками, тегами, досками и другими сущностями.

Пример использования:
```python
import asyncio
from kaiten_client import KaitenClient

async def main():
    async with KaitenClient("your-token") as client:
        # Получение карточек
        cards = await client.get_cards()
        
        # Создание карточки
        card = await client.create_card(
            title="Новая задача",
            column_id=123,
            description="Описание задачи"
        )
        
        # Создание тега
        tag = await client.create_tag(name="Важный", space_id=1, color="#ff0000")

asyncio.run(main())
```
"""

from .kaiten_client import KaitenClient
from .config import KaitenConfig
from .exceptions import KaitenApiError, KaitenNotFoundError, KaitenValidationError

__version__ = "2.0.0"
__author__ = "Rimuwu"

__all__ = [
    "KaitenClient",
    "KaitenConfig", 
    "KaitenApiError",
    "KaitenNotFoundError",
    "KaitenValidationError"
]