"""
Единый упрощенный клиент для работы с Kaiten API.
Предоставляет простой интерфейс без необходимости создавать специальные типы данных.
"""

from typing import Optional, List, Dict, Any, Union
import logging
import aiohttp
from datetime import datetime

from .config import KaitenConfig, KaitenCredentials
from .exceptions import KaitenApiError, KaitenNotFoundError, KaitenValidationError


logger = logging.getLogger(__name__)


class KaitenClient:
    """
    Единый упрощенный клиент для Kaiten API.
    
    Пример использования:
    ```python
    import asyncio
    
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
            tag = await client.create_tag(name="Важный", color="#ff0000")
    
    asyncio.run(main())
    ```
    """
    
    def __init__(self, token: str, domain: str = "api"):
        """
        Инициализация клиента.
        
        Args:
            token: API токен
            base_url: Базовый URL API
        """
        self.token = token
        self.domain = domain
        self.session: Optional[aiohttp.ClientSession] = None

        logger.info("Kaiten client initialized")

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=KaitenConfig.DEFAULT_TIMEOUT),
            headers={
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход."""
        if self.session:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Выполняет HTTP запрос к API."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        url = KaitenConfig.get_base_url(self.domain) + endpoint

        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 404:
                    raise KaitenNotFoundError(f"Resource not found: {endpoint}")
                elif response.status == 422:
                    error_data = await response.json()
                    raise KaitenValidationError(f"Validation error: {error_data}")
                elif response.status >= 400:
                    error_data = await response.text()
                    raise KaitenApiError(f"API error {response.status}: {error_data}")
                
                if response.status == 204:  # No Content
                    return None
                
                return await response.json()
        
        except aiohttp.ClientError as e:
            raise KaitenApiError(f"HTTP client error: {e}")
    
    # === КАРТОЧКИ ===
    
    async def get_cards(self, 
                        board_id: Optional[int] = None, **filters) -> List[Dict[str, Any]]:
        """
        Получает список карточек.
        
        Args:
            board_id: ID доски (если указан, ищет карточки в конкретной доске)
            **filters: Фильтры (assignee_id, state, priority и т.д.)
        
        Returns:
            Список карточек
        """
        if board_id:
            endpoint = f'{KaitenConfig.ENDPOINT_CARDS}?board_id={board_id}'
        else:
            endpoint = KaitenConfig.ENDPOINT_CARDS
        
        response = await self._request('GET', endpoint, params=filters)
        return response if isinstance(response, list) else response.get('items', [])
    
    async def get_card(self, card_id: int) -> Dict[str, Any]:
        """Получает карточку по ID."""
        return await self._request('GET', f'{KaitenConfig.ENDPOINT_CARDS}/{card_id}')

    async def create_card(
        self,
        title: str,
        column_id: int,
        description: Optional[str] = None,
        board_id: Optional[int] = None,
        assignee_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        priority: Optional[str] = None,
        due_date: Optional[str] = None,
        tags: Optional[List[int]] = None,
        parent_id: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Создает новую карточку.
        
        Args:
            title: Название карточки
            column_id: ID колонки
            description: Описание карточки
            board_id: ID доски
            assignee_id: ID исполнителя
            owner_id: ID владельца
            priority: Приоритет (low, normal, high, critical)
            due_date: Срок выполнения (ISO формат)
            tags: Список ID тегов
            parent_id: ID родительской карточки
            **kwargs: Дополнительные поля
        
        Returns:
            Созданная карточка
        """
        data = {
            'title': title,
            'column_id': column_id,
            **kwargs
        }
        
        # Добавляем опциональные поля
        for field, value in {
            'description': description,
            'board_id': board_id,
            'assignee_id': assignee_id,
            'owner_id': owner_id,
            'priority': priority,
            'due_date': due_date,
            'tags': tags,
            'parent_id': parent_id
        }.items():
            if value is not None:
                data[field] = value
        
        return await self._request('POST', KaitenConfig.ENDPOINT_CARDS, json=data)
    
    async def update_card(self, card_id: int, **fields) -> Dict[str, Any]:
        """
        Обновляет карточку.
        
        Args:
            card_id: ID карточки
            **fields: Поля для обновления (title, description, column_id и т.д.)
        
        Returns:
            Обновленная карточка
        """
        return await self._request('PATCH', f'{KaitenConfig.ENDPOINT_CARDS}/{card_id}', json=fields)

    async def delete_card(self, card_id: int) -> bool:
        """Удаляет карточку."""
        await self._request('DELETE', f'{KaitenConfig.ENDPOINT_CARDS}/{card_id}')
        return True
    
    async def move_card(self, card_id: int, column_id: int) -> Dict[str, Any]:
        """Перемещает карточку в другую колонку."""
        return await self.update_card(card_id, column_id=column_id)
    
    # === КОММЕНТАРИИ ===
    
    async def get_card_comments(self, card_id: int) -> List[Dict[str, Any]]:
        """Получает комментарии карточки."""
        endpoint = KaitenConfig.ENDPOINT_CARD_COMMENTS.format(card_id=card_id)
        response = await self._request('GET', endpoint)
        return response if isinstance(response, list) else response.get('items', [])
    
    async def add_comment(self, card_id: int, text: str) -> Dict[str, Any]:
        """Добавляет комментарий к карточке."""
        data = {'text': text}
        endpoint = KaitenConfig.ENDPOINT_CARD_COMMENTS.format(card_id=card_id)
        return await self._request('POST', endpoint, json=data)
    
    async def update_comment(self, card_id: int, 
                             comment_id: int, text: str) -> Dict[str, Any]:
        """Обновляет комментарий."""
        data = {'text': text}
        endpoint = KaitenConfig.ENDPOINT_CARD_COMMENTS.format(card_id=card_id)
        return await self._request('PATCH', f'{endpoint}/{comment_id}', json=data)

    async def delete_comment(self, card_id: int, 
                             comment_id: int) -> bool:
        """Удаляет комментарий."""
        endpoint = KaitenConfig.ENDPOINT_CARD_COMMENTS.format(card_id=card_id)
        await self._request('DELETE', f'{endpoint}/{comment_id}')
        return True
    
    # === УЧАСТНИКИ КАРТОЧКИ ===
    
    async def get_card_members(self, card_id: int) -> List[Dict[str, Any]]:
        """Получает участников карточки."""
        endpoint = KaitenConfig.ENDPOINT_CARD_MEMBERS.format(card_id=card_id)
        response = await self._request('GET', endpoint)
        return response if isinstance(response, list) else response.get('items', [])
    
    async def add_card_member(self, card_id: int, user_id: int) -> Dict[str, Any]:
        """Добавляет участника к карточке."""
        data = {'user_id': user_id}
        endpoint = KaitenConfig.ENDPOINT_CARD_MEMBERS.format(card_id=card_id)
        return await self._request('POST', endpoint, json=data)
    
    async def remove_card_member(self, card_id: int, user_id: int) -> bool:
        """Удаляет участника из карточки."""
        endpoint = KaitenConfig.ENDPOINT_CARD_MEMBERS.format(card_id=card_id)
        await self._request('DELETE', f'{endpoint}/{user_id}')
        return True
    
    # === ФАЙЛЫ ===
    
    async def get_card_files(self, card_id: int) -> List[Dict[str, Any]]:
        """Получает файлы карточки."""
        endpoint = KaitenConfig.ENDPOINT_CARD_FILES.format(card_id=card_id)
        response = await self._request('GET', endpoint)
        return response if isinstance(response, list) else response.get('items', [])
    
    async def upload_file(self, card_id: int, file_path: str, file_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Загружает файл к карточке.
        
        Args:
            card_id: ID карточки
            file_path: Путь к файлу
            file_name: Имя файла (если отличается от file_path)
        
        Returns:
            Информация о загруженном файле
        """
        import aiofiles
        from pathlib import Path
        
        if not file_name:
            file_name = Path(file_path).name
        
        async with aiofiles.open(file_path, 'rb') as f:
            file_data = await f.read()
        
        # Для загрузки файлов используем multipart/form-data
        data = aiohttp.FormData()
        data.add_field('file', file_data, filename=file_name)
        data.add_field('card_id', str(card_id))
        
        # Временно меняем заголовки для загрузки файлов
        headers = {'Authorization': f'Bearer {self.token}'}
        url = f"{KaitenConfig.get_base_url(self.domain)}/{KaitenConfig.ENDPOINT_CARD_FILES.format(card_id=card_id)}"
        
        async with self.session.post(url, data=data, headers=headers) as response:
            if response.status >= 400:
                error_data = await response.text()
                raise KaitenApiError(f"File upload error {response.status}: {error_data}")
            return await response.json()

    async def delete_file(self, card_id: int,
                          file_id: int) -> bool:
        """Удаляет файл."""
        endpoint = KaitenConfig.ENDPOINT_FILES.format(card_id=card_id)
        await self._request('DELETE', f'{endpoint}/{file_id}')
        return True
    
    # === ТЕГИ ===
    
    async def get_tags(self) -> List[Dict[str, Any]]:
        """Получает список тегов в пространстве."""
        response = await self._request('GET', KaitenConfig.ENDPOINT_TAGS)
        return response if isinstance(response, list) else response.get('items', [])
    
    async def get_tag(self, tag_id: int) -> Dict[str, Any]:
        """Получает тег по ID."""
        return await self._request('GET', f'{KaitenConfig.ENDPOINT_TAGS}/{tag_id}')
    
    async def create_tag(
        self,
        name: str,
        color: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создает новый тег.
        
        Args:
            name: Название тега
            space_id: ID пространства
            color: Цвет тега (hex формат, например #ff0000)
        
        Returns:
            Созданный тег
        """
        data = {'name': name}
        if color:
            data['color'] = color
        
        return await self._request('POST', KaitenConfig.ENDPOINT_TAGS, json=data)
    
    async def update_tag(
        self,
        tag_id: int,
        name: Optional[str] = None,
        color: Optional[str] = None
    ) -> Dict[str, Any]:
        """Обновляет тег."""
        data = {}
        if name is not None:
            data['name'] = name
        if color is not None:
            data['color'] = color
        
        return await self._request('PATCH', 
                                   f'{KaitenConfig.ENDPOINT_TAGS}/{tag_id}', json=data)
    
    async def delete_tag(self, tag_id: int) -> bool:
        """Удаляет тег."""
        await self._request('DELETE', f'{KaitenConfig.ENDPOINT_TAGS}/{tag_id}')
        return True
    
    # === ПРОСТРАНСТВА ===
    
    async def get_spaces(self) -> List[Dict[str, Any]]:
        """Получает список пространств."""
        response = await self._request('GET', KaitenConfig.ENDPOINT_SPACES)
        return response if isinstance(response, list) else response.get('items', [])
    
    async def get_space(self, space_id: int) -> Dict[str, Any]:
        """Получает пространство по ID."""
        return await self._request('GET', f'{KaitenConfig.ENDPOINT_SPACES}/{space_id}')
    
    async def create_space(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создает новое пространство.
        
        Args:
            name: Название пространства
            description: Описание пространства
        
        Returns:
            Созданное пространство
        """
        data = {'name': name}
        if description:
            data['description'] = description
        
        return await self._request('POST', KaitenConfig.ENDPOINT_SPACES, json=data)
    
    async def update_space(self, space_id: int, **fields) -> Dict[str, Any]:
        """Обновляет пространство."""
        return await self._request('PATCH', f'{KaitenConfig.ENDPOINT_SPACES}/{space_id}', json=fields)
    
    async def delete_space(self, space_id: int) -> bool:
        """Удаляет пространство."""
        await self._request('DELETE', f'{KaitenConfig.ENDPOINT_SPACES}/{space_id}')
        return True
    
    # === ДОСКИ ===
    
    async def get_boards(self, space_id: int) -> List[Dict[str, Any]]:
        """Получает список досок в пространстве."""
        endpoint = KaitenConfig.ENDPOINT_BOARDS.format(space_id=space_id)
        response = await self._request('GET', endpoint)
        return response if isinstance(response, list) else response.get('items', [])
    
    async def get_board(self, board_id: int) -> Dict[str, Any]:
        """Получает доску по ID."""
        return await self._request('GET', f'/boards/{board_id}')
    
    async def create_board(
        self,
        title: str,
        space_id: int,
        description: Optional[str] = None,
        board_type: str = "kanban"
    ) -> Dict[str, Any]:
        """
        Создает новую доску.
        
        Args:
            title: Название доски
            space_id: ID пространства
            description: Описание доски
            board_type: Тип доски (kanban, scrum)
        
        Returns:
            Созданная доска
        """
        data = {
            'title': title,
            'board_type': board_type
        }
        if description:
            data['description'] = description
        
        endpoint = KaitenConfig.ENDPOINT_BOARDS.format(space_id=space_id)
        return await self._request('POST', endpoint, json=data)
    
    async def update_board(self, space_id: int, 
                           board_id: int, **fields) -> Dict[str, Any]:
        """Обновляет доску."""
        endpoint = KaitenConfig.ENDPOINT_BOARDS.format(space_id=space_id)
        return await self._request('PATCH', f'{endpoint}/{board_id}', json=fields)
    
    async def delete_board(self, space_id: int, 
                           board_id: int) -> bool:
        """Удаляет доску."""
        endpoint = KaitenConfig.ENDPOINT_BOARDS.format(space_id=space_id)
        await self._request('DELETE', f'{endpoint}/{board_id}')
        return True
    
    # === КОЛОНКИ ===
    
    async def get_columns(self, board_id: int) -> List[Dict[str, Any]]:
        """Получает колонки доски."""
        endpoint = KaitenConfig.ENDPOINT_COLUMNS.format(board_id=board_id)
        response = await self._request('GET', endpoint)
        return response if isinstance(response, list) else response.get('items', [])
    
    async def get_column(self, board_id: int, 
                         column_id: int) -> Dict[str, Any]:
        """Получает колонку по ID.
           МОЖЕТ НЕ РАБОТАТЬ!
        """
        endpoint = KaitenConfig.ENDPOINT_COLUMNS.format(board_id=board_id)
        return await self._request('GET', f'{endpoint}/{column_id}')
    
    async def create_column(
        self,
        title: str,
        board_id: int,
        position: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Создает новую колонку.
        
        Args:
            title: Название колонки
            board_id: ID доски
            position: Позиция колонки
        
        Returns:
            Созданная колонка
        """
        data = {'title': title}
        if position is not None:
            data['position'] = position
        
        endpoint = KaitenConfig.ENDPOINT_COLUMNS.format(board_id=board_id)
        return await self._request('POST', endpoint, json=data)
    
    async def update_column(self, board_id: int, 
                            column_id: int, **fields) -> Dict[str, Any]:
        """Обновляет колонку."""
        endpoint = KaitenConfig.ENDPOINT_COLUMNS.format(board_id=board_id)
        return await self._request('PATCH', f'{endpoint}/{column_id}', json=fields)
    
    async def delete_column(self, board_id: int,
                            column_id: int) -> bool:
        """Удаляет колонку."""
        endpoint = KaitenConfig.ENDPOINT_COLUMNS.format(board_id=board_id)
        await self._request('DELETE', f'{endpoint}/{column_id}')
        return True
