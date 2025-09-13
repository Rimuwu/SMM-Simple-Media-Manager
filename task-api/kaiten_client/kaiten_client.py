"""
Единый упрощенный клиент для работы с Kaiten API.
Предоставляет простой интерфейс без необходимости создавать специальные типы данных.
"""

import asyncio
from typing import Optional, List, Dict, Any, Union
import logging
import aiohttp
from datetime import datetime

from .config import KaitenConfig, KaitenCredentials
from .exceptions import KaitenApiError, KaitenNotFoundError, KaitenValidationError
from .models import Space, Board, Column, Lane, Card, Tag, Comment, Member, File


logger = logging.getLogger(__name__)


class KaitenClient:
    """
    Единый упрощенный клиент для Kaiten API.
    
    Пример использования:
    ```python
    import asyncio
    
    async def main():
        async with KaitenClient("your-token") as client:
            # Получение пространств
            spaces = await client.get_spaces()
            space = spaces[0]
            
            # Получение досок через пространство
            boards = await space.get_boards()
            board = boards[0]
            
            # Получение колонок через доску
            columns = await board.get_columns()
            column = columns[0]
            
            # Создание карточки через колонку
            card = await column.create_card(
                title="Новая задача",
                description="Описание задачи"
            )
            
            # Добавление комментария к карточке
            comment = await card.add_comment("Первый комментарий")
            
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
        self._request_times: List[float] = []

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

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        """Выполняет HTTP запрос к API с поддержкой повторов и лимитом запросов в секунду."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        # --- Лимит запросов в секунду ---
        now = asyncio.get_event_loop().time()
        # Удаляем устаревшие таймштампы
        self._request_times = [t for t in self._request_times if now - t < 1.0]
        if len(self._request_times) >= KaitenConfig.LIMIT_PER_SEC:
            sleep_time = 1.0 - (now - self._request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            now = asyncio.get_event_loop().time()
            self._request_times = [t for t in self._request_times if now - t < 1.0]
        self._request_times.append(now)
        # --- Конец лимита ---

        url = KaitenConfig.get_base_url(self.domain) + endpoint
        retries = KaitenConfig.MAX_RETRIES
        delay = KaitenConfig.RETRY_DELAY
        
        if params:
            for key, value in params.items():
                url += f"{'&' if '?' in url else '?'}{key}={value}"

        for attempt in range(1, retries + 1):
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
                if attempt < retries:
                    logger.warning(f"HTTP client error: {e}. Retrying {attempt}/{retries} after {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    raise KaitenApiError(f"HTTP client error after {retries} retries: {e}")
    # === КАРТОЧКИ ===
    
    async def get_cards(self, 
                        board_id: Optional[int] = None,
                        # Фильтры по датам (ISO 8601 формат)
                        created_before: Optional[str] = None,
                        created_after: Optional[str] = None,
                        updated_before: Optional[str] = None,
                        updated_after: Optional[str] = None,
                        first_moved_in_progress_after: Optional[str] = None,
                        first_moved_in_progress_before: Optional[str] = None,
                        last_moved_to_done_at_after: Optional[str] = None,
                        last_moved_to_done_at_before: Optional[str] = None,
                        due_date_after: Optional[str] = None,
                        due_date_before: Optional[str] = None,
                        # Фильтры по содержимому
                        query: Optional[str] = None,
                        tag: Optional[str] = None,
                        tag_ids: Optional[str] = None,
                        type_ids: Optional[str] = None,
                        # Фильтры исключения
                        exclude_board_ids: Optional[str] = None,
                        exclude_lane_ids: Optional[str] = None,
                        exclude_column_ids: Optional[str] = None,
                        exclude_owner_ids: Optional[str] = None,
                        exclude_card_ids: Optional[str] = None,
                        # Фильтры включения по ID
                        column_ids: Optional[str] = None,
                        member_ids: Optional[str] = None,
                        owner_ids: Optional[str] = None,
                        responsible_ids: Optional[str] = None,
                        organizations_ids: Optional[str] = None,
                        # Фильтры по состоянию
                        states: Optional[str] = None,  # 1-queued, 2-inProgress, 3-done
                        external_id: Optional[str] = None,
                        # Дополнительные параметры
                        additional_card_fields: Optional[str] = None,  # например: 'description'
                        search_fields: Optional[str] = None,
                        # Основные фильтры
                        space_id: Optional[int] = None,
                        column_id: Optional[int] = None,
                        lane_id: Optional[int] = None,
                        condition: Optional[int] = None,  # 1 - on board, 2 - archived
                        type_id: Optional[int] = None,
                        responsible_id: Optional[int] = None,
                        owner_id: Optional[int] = None,
                        # Булевые фильтры
                        archived: Optional[bool] = None,
                        asap: Optional[bool] = None,
                        overdue: Optional[bool] = None,
                        done_on_time: Optional[bool] = None,
                        with_due_date: Optional[bool] = None,
                        is_request: Optional[bool] = None,
                        # Пагинация и сортировка
                        limit: Optional[int] = None,  # max 100
                        offset: Optional[int] = None,
                        order_space_id: Optional[int] = None,
                        order_by: Optional[str] = None,
                        order_direction: Optional[str] = None,  # 'asc' или 'desc'
                        # Продвинутые фильтры
                        filter_: Optional[str] = None,  # base64 encoded filter
                        **extra_filters) -> List[Card]:
        """
        Получает список карточек с расширенной фильтрацией.
        
        Args:
            board_id: ID доски (если указан, ищет карточки в конкретной доске)
            # Фильтры по датам (ISO 8601 формат)
            created_before: Создано до даты
            created_after: Создано после даты
            updated_before: Обновлено до даты
            updated_after: Обновлено после даты
            first_moved_in_progress_after: Первое перемещение в работу после даты
            first_moved_in_progress_before: Первое перемещение в работу до даты
            last_moved_to_done_at_after: Последнее перемещение в выполненные после даты
            last_moved_to_done_at_before: Последнее перемещение в выполненные до даты
            due_date_after: Срок выполнения после даты
            due_date_before: Срок выполнения до даты
            # Фильтры по содержимому
            query: Текстовый поиск в карточках
            tag: Поиск по тегу
            tag_ids: Поиск по ID тегов (через запятую)
            type_ids: Поиск по ID типов (через запятую)
            # Фильтры исключения
            exclude_board_ids: Исключить ID досок (через запятую)
            exclude_lane_ids: Исключить ID дорожек (через запятую)
            exclude_column_ids: Исключить ID колонок (через запятую)
            exclude_owner_ids: Исключить ID владельцев (через запятую)
            exclude_card_ids: Исключить ID карточек (через запятую)
            # Фильтры включения по ID
            column_ids: Поиск по ID колонок (через запятую)
            member_ids: Поиск по ID участников (через запятую)
            owner_ids: Поиск по ID владельцев (через запятую)
            responsible_ids: Поиск по ID ответственных (через запятую)
            organizations_ids: Поиск по ID организаций (через запятую)
            # Фильтры по состоянию
            states: Поиск по состояниям (через запятую): 1-queued, 2-inProgress, 3-done
            external_id: Поиск по внешнему ID
            # Дополнительные параметры
            additional_card_fields: Дополнительные поля карточек (через запятую), например: 'description'
            search_fields: Поля для поиска
            # Основные фильтры
            space_id: Фильтр по ID пространства
            column_id: Фильтр по ID колонки
            lane_id: Фильтр по ID дорожки
            condition: Фильтр по состоянию: 1 - на доске, 2 - архивная
            type_id: Фильтр по ID типа
            responsible_id: Фильтр по ID ответственного
            owner_id: Фильтр по ID владельца
            # Булевые фильтры
            archived: Фильтр архивных карточек
            asap: Маркер ASAP
            overdue: Фильтр по просроченным
            done_on_time: Фильтр по выполненным вовремя
            with_due_date: Фильтр по карточкам с установленным сроком
            is_request: Поиск запросов
            # Пагинация и сортировка
            limit: Максимальное количество карточек в ответе (макс 100)
            offset: Количество записей для пропуска
            order_space_id: Сортировка по ID пространства
            order_by: Поля для сортировки (через запятую)
            order_direction: Направление сортировки 'asc' или 'desc' (через запятую)
            # Продвинутые фильтры
            filter_: Фильтр по условиям и/или в формате base64
            **extra_filters: Дополнительные фильтры
        
        Returns:
            Список карточек
        """
        # Формируем параметры запроса
        params = {}
        
        # Добавляем board_id в параметры если указан
        if board_id:
            params['board_id'] = board_id
        
        # Добавляем все остальные параметры если они не None
        all_params = {
            'created_before': created_before,
            'created_after': created_after,
            'updated_before': updated_before,
            'updated_after': updated_after,
            'first_moved_in_progress_after': first_moved_in_progress_after,
            'first_moved_in_progress_before': first_moved_in_progress_before,
            'last_moved_to_done_at_after': last_moved_to_done_at_after,
            'last_moved_to_done_at_before': last_moved_to_done_at_before,
            'due_date_after': due_date_after,
            'due_date_before': due_date_before,
            'query': query,
            'tag': tag,
            'tag_ids': tag_ids,
            'type_ids': type_ids,
            'exclude_board_ids': exclude_board_ids,
            'exclude_lane_ids': exclude_lane_ids,
            'exclude_column_ids': exclude_column_ids,
            'exclude_owner_ids': exclude_owner_ids,
            'exclude_card_ids': exclude_card_ids,
            'column_ids': column_ids,
            'member_ids': member_ids,
            'owner_ids': owner_ids,
            'responsible_ids': responsible_ids,
            'organizations_ids': organizations_ids,
            'states': states,
            'external_id': external_id,
            'additional_card_fields': additional_card_fields,
            'search_fields': search_fields,
            'space_id': space_id,
            'column_id': column_id,
            'lane_id': lane_id,
            'condition': condition,
            'type_id': type_id,
            'responsible_id': responsible_id,
            'owner_id': owner_id,
            'archived': archived,
            'asap': asap,
            'overdue': overdue,
            'done_on_time': done_on_time,
            'with_due_date': with_due_date,
            'is_request': is_request,
            'limit': limit,
            'offset': offset,
            'order_space_id': order_space_id,
            'order_by': order_by,
            'order_direction': order_direction,
            'filter': filter_,
            **extra_filters
        }
        
        # Добавляем только не-None параметры
        for key, value in all_params.items():
            if value is not None:
                params[key] = value

        response = await self._request('GET', KaitenConfig.ENDPOINT_CARDS, params=params)
        cards_data = response if isinstance(response, list) else response.get('items', [])
        return [Card(self, card_data) for card_data in cards_data]
    
    async def get_card(self, card_id: int) -> Card:
        """Получает карточку по ID."""
        data = await self._request('GET', f'{KaitenConfig.ENDPOINT_CARDS}/{card_id}')
        return Card(self, data)

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
    ) -> Card:
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
        
        card_data = await self._request('POST', KaitenConfig.ENDPOINT_CARDS, json=data)
        return Card(self, card_data)
    
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
    
    async def move_card(self, card_id: int, column_id: int) -> Card:
        """Перемещает карточку в другую колонку."""
        data = await self.update_card(card_id, column_id=column_id)
        return Card(self, data)
    
    # === КОММЕНТАРИИ ===
    
    async def get_card_comments(self, card_id: int) -> List[Comment]:
        """Получает комментарии карточки."""
        endpoint = KaitenConfig.ENDPOINT_CARD_COMMENTS.format(card_id=card_id)
        response = await self._request('GET', endpoint)
        comments_data = response if isinstance(response, list) else response.get('items', [])
        return [Comment(self, comment_data) for comment_data in comments_data]
    
    async def add_comment(self, card_id: int, text: str) -> Comment:
        """Добавляет комментарий к карточке."""
        data = {'text': text}
        endpoint = KaitenConfig.ENDPOINT_CARD_COMMENTS.format(card_id=card_id)
        comment_data = await self._request('POST', endpoint, json=data)
        return Comment(self, comment_data)
    
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
    
    async def get_card_members(self, card_id: int) -> List[Member]:
        """Получает участников карточки."""
        endpoint = KaitenConfig.ENDPOINT_CARD_MEMBERS.format(card_id=card_id)
        response = await self._request('GET', endpoint)
        members_data = response if isinstance(response, list) else response.get('items', [])
        return [Member(self, member_data) for member_data in members_data]
    
    async def add_card_member(self, card_id: int, user_id: int) -> Member:
        """Добавляет участника к карточке."""
        data = {'user_id': user_id}
        endpoint = KaitenConfig.ENDPOINT_CARD_MEMBERS.format(card_id=card_id)
        member_data = await self._request('POST', endpoint, json=data)
        return Member(self, member_data)
    
    async def remove_card_member(self, card_id: int, user_id: int) -> bool:
        """Удаляет участника из карточки."""
        endpoint = KaitenConfig.ENDPOINT_CARD_MEMBERS.format(card_id=card_id)
        await self._request('DELETE', f'{endpoint}/{user_id}')
        return True
    
    # === ФАЙЛЫ ===
    
    async def get_card_files(self, card_id: int) -> List[File]:
        """Получает файлы карточки."""
        endpoint = KaitenConfig.ENDPOINT_CARD_FILES.format(card_id=card_id)
        response = await self._request('GET', endpoint)
        files_data = response if isinstance(response, list) else response.get('items', [])
        return [File(self, file_data) for file_data in files_data]
    
    async def upload_file(self, card_id: int, file_path: str, file_name: Optional[str] = None) -> File:
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
            result_data = await response.json()
            return File(self, result_data)

    async def delete_file(self, card_id: int,
                          file_id: int) -> bool:
        """Удаляет файл."""
        endpoint = KaitenConfig.ENDPOINT_FILES.format(card_id=card_id)
        await self._request('DELETE', f'{endpoint}/{file_id}')
        return True
    
    # === ТЕГИ ===
    
    async def get_tags(self) -> List[Tag]:
        """Получает список тегов в пространстве."""
        response = await self._request('GET', KaitenConfig.ENDPOINT_TAGS)
        tags_data = response if isinstance(response, list) else response.get('items', [])
        return [Tag(self, tag_data) for tag_data in tags_data]
    
    async def get_tag(self, tag_id: int) -> Tag:
        """Получает тег по ID."""
        data = await self._request('GET', f'{KaitenConfig.ENDPOINT_TAGS}/{tag_id}')
        return Tag(self, data)
    
    async def create_tag(
        self,
        name: str,
        color: Optional[str] = None
    ) -> Tag:
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
        
        tag_data = await self._request('POST', KaitenConfig.ENDPOINT_TAGS, json=data)
        return Tag(self, tag_data)
    
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
    
    async def get_spaces(self) -> List[Space]:
        """Получает список пространств."""
        response = await self._request('GET', KaitenConfig.ENDPOINT_SPACES)
        spaces_data = response if isinstance(response, list) else response.get('items', [])
        return [Space(self, space_data) for space_data in spaces_data]
    
    async def get_space(self, space_id: int) -> Space:
        """Получает пространство по ID."""
        data = await self._request('GET', f'{KaitenConfig.ENDPOINT_SPACES}/{space_id}')
        return Space(self, data)
    
    async def create_space(
        self,
        name: str,
        description: Optional[str] = None
    ) -> Space:
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
        
        space_data = await self._request('POST', KaitenConfig.ENDPOINT_SPACES, json=data)
        return Space(self, space_data)
    
    async def update_space(self, space_id: int, **fields) -> Dict[str, Any]:
        """Обновляет пространство."""
        return await self._request('PATCH', f'{KaitenConfig.ENDPOINT_SPACES}/{space_id}', json=fields)
    
    async def delete_space(self, space_id: int) -> bool:
        """Удаляет пространство."""
        await self._request('DELETE', f'{KaitenConfig.ENDPOINT_SPACES}/{space_id}')
        return True
    
    # === ДОСКИ ===
    
    async def get_boards(self, space_id: int) -> List[Board]:
        """Получает список досок в пространстве."""
        endpoint = KaitenConfig.ENDPOINT_BOARDS.format(space_id=space_id)
        response = await self._request('GET', endpoint)
        boards_data = response if isinstance(response, list) else response.get('items', [])
        return [Board(self, board_data) for board_data in boards_data]
    
    async def get_board(self, board_id: int) -> Board:
        """Получает доску по ID."""
        data = await self._request('GET', f'/boards/{board_id}')
        return Board(self, data)
    
    async def create_board(
        self,
        title: str,
        space_id: int,
        description: Optional[str] = None,
        board_type: str = "kanban"
    ) -> Board:
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
        board_data = await self._request('POST', endpoint, json=data)
        return Board(self, board_data)
    
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
    
    async def get_columns(self, board_id: int) -> List[Column]:
        """Получает колонки доски."""
        endpoint = KaitenConfig.ENDPOINT_COLUMNS.format(board_id=board_id)
        response = await self._request('GET', endpoint)
        columns_data = response if isinstance(response, list) else response.get('items', [])
        return [Column(self, column_data) for column_data in columns_data]
    
    async def get_column(self, board_id: int, 
                         column_id: int) -> Column:
        """Получает колонку по ID.
           МОЖЕТ НЕ РАБОТАТЬ!
        """
        endpoint = KaitenConfig.ENDPOINT_COLUMNS.format(board_id=board_id)
        data = await self._request('GET', f'{endpoint}/{column_id}')
        return Column(self, data)
    
    async def create_column(
        self,
        title: str,
        board_id: int,
        position: Optional[int] = None
    ) -> Column:
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
        column_data = await self._request('POST', endpoint, json=data)
        return Column(self, column_data)
    
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
    
    # === ДОРОЖКИ ===
    
    async def get_lanes(self, board_id: int) -> List[Lane]:
        """
        Получает список дорожек доски.
        
        Args:
            board_id: ID доски
        
        Returns:
            Список дорожек
        """
        endpoint = KaitenConfig.ENDPOINT_LANES.format(board_id=board_id)
        response = await self._request('GET', endpoint)
        lanes_data = response if isinstance(response, list) else response.get('items', [])
        return [Lane(self, lane_data) for lane_data in lanes_data]
    
    async def get_lane(self, board_id: int, lane_id: int) -> Lane:
        """
        Получает дорожку по ID.
        
        Args:
            board_id: ID доски
            lane_id: ID дорожки
        
        Returns:
            Дорожка
        """
        endpoint = KaitenConfig.ENDPOINT_LANES.format(board_id=board_id)
        data = await self._request('GET', f'{endpoint}/{lane_id}')
        return Lane(self, data)
    
    async def create_lane(
        self,
        title: str,
        board_id: int,
        sort_order: Optional[float] = None,
        row_count: Optional[int] = None,
        wip_limit: Optional[int] = None,
        default_card_type_id: Optional[int] = None,
        wip_limit_type: Optional[int] = None,
        external_id: Optional[str] = None,
        default_tags: Optional[str] = None,
        last_moved_warning_after_days: Optional[int] = None,
        last_moved_warning_after_hours: Optional[int] = None,
        last_moved_warning_after_minutes: Optional[int] = None,
        condition: Optional[int] = None,
        **kwargs
    ) -> Lane:
        """
        Создает новую дорожку в доске.
        
        Args:
            title: Название дорожки
            board_id: ID доски
            sort_order: Позиция
            row_count: Высота
            wip_limit: Рекомендуемый лимит для колонки
            default_card_type_id: Тип карточки по умолчанию
            wip_limit_type: Тип WIP лимита (1 – количество карточек, 2 – размер карточек)
            external_id: Внешний идентификатор
            default_tags: Теги по умолчанию
            last_moved_warning_after_days: Предупреждение на устаревших карточках (дни)
            last_moved_warning_after_hours: Предупреждение на устаревших карточках (часы)
            last_moved_warning_after_minutes: Предупреждение на устаревших карточках (минуты)
            condition: Состояние (1 - активная, 2 - архивная, 3 - удаленная)
            **kwargs: Дополнительные поля
        
        Returns:
            Созданная дорожка
        """
        data = {
            'title': title,
            **kwargs
        }
        
        # Добавляем опциональные поля
        for field, value in {
            'sort_order': sort_order,
            'row_count': row_count,
            'wip_limit': wip_limit,
            'default_card_type_id': default_card_type_id,
            'wip_limit_type': wip_limit_type,
            'external_id': external_id,
            'default_tags': default_tags,
            'last_moved_warning_after_days': last_moved_warning_after_days,
            'last_moved_warning_after_hours': last_moved_warning_after_hours,
            'last_moved_warning_after_minutes': last_moved_warning_after_minutes,
            'condition': condition
        }.items():
            if value is not None:
                data[field] = value
        
        endpoint = KaitenConfig.ENDPOINT_LANES.format(board_id=board_id)
        lane_data = await self._request('POST', endpoint, json=data)
        return Lane(self, lane_data)
    
    async def update_lane(self, board_id: int, 
                          lane_id: int, **fields) -> Dict[str, Any]:
        """
        Обновляет дорожку.
        
        Args:
            board_id: ID доски
            lane_id: ID дорожки
            **fields: Поля для обновления
        
        Returns:
            Обновленная дорожка
        """
        endpoint = KaitenConfig.ENDPOINT_LANES.format(board_id=board_id)
        return await self._request('PATCH', f'{endpoint}/{lane_id}', json=fields)
    
    async def delete_lane(self, board_id: int, lane_id: int) -> bool:
        """
        Удаляет дорожку.
        
        Args:
            board_id: ID доски
            lane_id: ID дорожки
        
        Returns:
            True если удаление прошло успешно
        """
        endpoint = KaitenConfig.ENDPOINT_LANES.format(board_id=board_id)
        await self._request('DELETE', f'{endpoint}/{lane_id}')
        return True
