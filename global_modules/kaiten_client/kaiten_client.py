"""
Единый упрощенный клиент для работы с Kaiten API.
Предоставляет простой интерфейс без необходимости создавать специальные типы данных.
"""

import asyncio
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING
import logging
import aiohttp
from datetime import datetime

from .config import KaitenConfig, KaitenCredentials
from .exceptions import KaitenApiError, KaitenNotFoundError, KaitenValidationError
from .models import Space, Board, Column, Lane, Card, Tag, Comment, Member, File, Property, Checklist, ChecklistItem

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


class KaitenClient:
    """
    Единый упрощенный клиент для Kaiten API.
    
    Поддерживает два способа использования:
    
    1. С контекстным менеджером (рекомендуется):
    ```python
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
        finally:
            # Обязательно закрываем сессию
            await client.close()
    ```
    """
    
    def __init__(self, token: str, domain: str = "api"):
        """
        Инициализация клиента.
        
        Args:
            token: API токен
            domain: Домен менеджера
        """
        self.token = token
        self.domain = domain
        self.session: Optional[aiohttp.ClientSession] = None
        self._request_times: List[float] = []
        self.config = KaitenCredentials(
            domain=domain, token=token)
        self._is_initialized = False

        logger.info("Kaiten client initialized")

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход."""
        await self.close()
    
    async def initialize(self):
        """
        Инициализирует клиент и создает сессию.
        Вызывается автоматически при использовании async with или вручную.
        """
        if not self._is_initialized:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=KaitenConfig.DEFAULT_TIMEOUT),
                headers=self.config.get_headers()
            )
            self._is_initialized = True
            logger.info("Kaiten client session initialized")
    
    async def close(self):
        """
        Закрывает сессию клиента.
        Вызывается автоматически при выходе из async with или вручную.
        """
        if self.session and self._is_initialized:
            await self.session.close()
            self.session = None
            self._is_initialized = False
            logger.info("Kaiten client session closed")

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        """Выполняет HTTP запрос к API с поддержкой повторов и лимитом запросов в секунду."""
        # Автоматически инициализируем клиент если он не инициализирован
        if not self._is_initialized:
            await self.initialize()
        
        if not self.session:
            raise RuntimeError("Client session not available. Call initialize() first or use 'async with' context manager.")

        # --- Лимит запросов в секунду ---
        now = asyncio.get_event_loop().time()
        # Удаляем устаревшие таймштампы
        self._request_times = [t for t in self._request_times if now - t < 1.0]
        
        while len(self._request_times) >= KaitenConfig.LIMIT_PER_SEC:
            oldest_request_time = min(self._request_times)
            sleep_time = 1.0 - (now - oldest_request_time)
            if sleep_time > 0:
                logger.debug(f"Rate limit reached, sleeping for {sleep_time:.3f} seconds")
                await asyncio.sleep(sleep_time)

            now = asyncio.get_event_loop().time()
            self._request_times = [t for t in self._request_times if now - t < 1.0]

        self._request_times.append(now)

        url = KaitenConfig.get_base_url(self.domain) + endpoint
        retries = KaitenConfig.MAX_RETRIES
        delay = KaitenConfig.RETRY_DELAY
        
        if params:
            for key, value in params.items():
                url += f"{'&' if '?' in url else '?'}{key}={value}"

        for attempt in range(1, retries + 1):
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 429:
                        # Специальная обработка для 429 ошибки
                        retry_after = response.headers.get('Retry-After', '1')
                        try:
                            retry_delay = float(retry_after)
                        except ValueError:
                            retry_delay = 1.0
                        
                        logger.warning(f"Rate limit hit (429), waiting {retry_delay} seconds before retry {attempt}/{retries}")
                        await asyncio.sleep(retry_delay)
                        
                        # Очищаем историю запросов после получения 429
                        self._request_times = []
                        
                        if attempt < retries:
                            continue
                        else:
                            raise KaitenApiError(f"Rate limit exceeded after {retries} retries")
                    
                    elif response.status == 404:
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
    
    async def get_card(self, card_id: int, additional_fields: Optional[str] = None) -> Card:
        """
        Получает карточку по ID.
        
        Args:
            card_id: ID карточки
            additional_fields: Дополнительные поля для включения (например, 'description,checklists')
        
        Returns:
            Объект карточки
        """
        params = {}
        if additional_fields:
            params['additional_card_fields'] = additional_fields
        
        data = await self._request('GET', f'{KaitenConfig.ENDPOINT_CARDS}/{card_id}', params=params)
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
        headers = self.config.get_upload_headers()
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
        data = {'title': name}
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
    
    # === ПОЛЬЗОВАТЕЛИ ПРОСТРАНСТВА ===
    
    async def get_space_users(
        self,
        space_id: int,
        include_inherited_access: Optional[bool] = None,
        inactive: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает список пользователей пространства.
        
        Args:
            space_id: ID пространства
            include_inherited_access: Включить пользователей с унаследованным доступом
            inactive: Включить только неактивных пользователей компании
        
        Returns:
            Список пользователей
        """
        params = {}
        
        if include_inherited_access is not None:
            params['include_inherited_access'] = include_inherited_access
        if inactive is not None:
            params['inactive'] = inactive
        
        endpoint = f'{KaitenConfig.ENDPOINT_SPACES}/{space_id}/users'
        response = await self._request('GET', endpoint, params=params)
        return response if isinstance(response, list) else response.get('items', [])
    
    # === ПОЛЬЗОВАТЕЛИ КОМПАНИИ ===
    
    async def get_company_users(
        self,
        invites_only: Optional[bool] = None,
        with_transfer_access_status: Optional[bool] = None,
        for_members_section: Optional[bool] = None,
        owner_only: Optional[bool] = None,
        only_paid: Optional[bool] = None,
        only_records_count: Optional[bool] = None,
        only_virtual: Optional[bool] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        query: Optional[str] = None,
        access_type_permissions: Optional[str] = None,
        sd_access_type: Optional[str] = None,
        take_licence: Optional[str] = None,
        temporarily_inactive_status: Optional[str] = None,
        group_ids: Optional[List[int]] = None,
        permissions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает список пользователей компании с фильтрацией.
        Для использования этого метода требуется доступ к административному разделу "Members".
        
        Args:
            invites_only: Фильтр для возврата только приглашений
            with_transfer_access_status: Добавить данные о процессе передачи прав пользователя
            for_members_section: Возвращает пользователей для административного раздела "Members" с постраничным выводом
            owner_only: Возвращает только владельца компании
            only_paid: Возвращает только пользователей с платным доступом
            only_records_count: Возвращает только количество пользователей (работает только с for_members_section или only_virtual)
            only_virtual: Возвращает только виртуальных пользователей с постраничным выводом
            offset: Количество записей для пропуска (работает только с for_members_section или only_virtual)
            limit: Максимальное количество пользователей в ответе (по умолчанию 100, работает только с for_members_section или only_virtual)
            query: Фильтр по email и full_name (работает только с for_members_section)
            access_type_permissions: Фильтр по доступу к Kaiten (работает только с for_members_section)
            sd_access_type: Фильтр по доступу к Service Desk (работает только с for_members_section)
            take_licence: Фильтр по пользователям, потребляющим лицензию (работает только с for_members_section)
            temporarily_inactive_status: Фильтр по временно неактивным пользователям (работает только с for_members_section)
            group_ids: Фильтр по ID групп (работает только с for_members_section)
            permissions: Фильтр по правам доступа, предоставленным пользователям (работает только с for_members_section)
        
        Returns:
            Список пользователей компании
        """
        params = {}
        
        if invites_only is not None:
            params['invitesOnly'] = invites_only
        if with_transfer_access_status is not None:
            params['withTransferAccessStatus'] = with_transfer_access_status
        if for_members_section is not None:
            params['for_members_section'] = for_members_section
        if owner_only is not None:
            params['owner_only'] = owner_only
        if only_paid is not None:
            params['only_paid'] = only_paid
        if only_records_count is not None:
            params['only_records_count'] = only_records_count
        if only_virtual is not None:
            params['only_virtual'] = only_virtual
        if offset is not None:
            params['offset'] = offset
        if limit is not None:
            params['limit'] = limit
        if query is not None:
            params['query'] = query
        if access_type_permissions is not None:
            params['access_type_permissions'] = access_type_permissions
        if sd_access_type is not None:
            params['sd_access_type'] = sd_access_type
        if take_licence is not None:
            params['take_licence'] = take_licence
        if temporarily_inactive_status is not None:
            params['temporarily_inactive_status'] = temporarily_inactive_status
        if group_ids is not None:
            params['group_ids'] = ','.join(map(str, group_ids))
        if permissions is not None:
            params['permissions'] = ','.join(permissions)
        
        endpoint = '/company/users'
        response = await self._request('GET', endpoint, params=params)
        return response if isinstance(response, list) else response.get('items', [])
    
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
        columns: Optional[List[Dict[str, Any]]] = None,
        lanes: Optional[List[Dict[str, Any]]] = None
    ) -> Board:
        """
        Создает новую доску.
        
        Args:
            title: Название доски
            space_id: ID пространства
            description: Описание доски
            board_type: Тип доски (kanban, scrum)
            columns: Список колонок для создания доски (title, type - required)
        
        Returns:
            Созданная доска
        """
        data = {
            'title': title,
            'columns': columns or [],
            'lanes': lanes or []
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

    # Методы для работы с пользовательскими свойствами
    async def get_custom_properties(self) -> List[Property]:
        """Получает список всех пользовательских свойств.
        
        Returns:
            List[Property]: Список объектов Property
        """
        data = await self._request("GET", KaitenConfig.ENDPOINT_CUSTOM_PROPERTIES)
        return [Property(client=self, data=item) for item in data]
    
    async def get_custom_property(self, property_id: int) -> Property:
        """Получает пользовательское свойство по ID.
        
        Args:
            property_id: ID свойства
            
        Returns:
            Property: Объект Property
        """
        data = await self._request("GET", f"{KaitenConfig.ENDPOINT_CUSTOM_PROPERTIES}/{property_id}")
        return Property(client=self, data=data)
    
    async def create_custom_property(
        self,
        name: str,
        property_type: str,
        show_on_facade: bool = False,
        multiline: bool = False,
        vote_variant: Optional[str] = None,
        values_type: Optional[str] = None,
        colorful: bool = False,
        multi_select: bool = False,
        data: Optional[Dict] = None,
        formula: Optional[str] = None,
        color: Optional[str] = None,
        fields_settings: Optional[List[Dict]] = None
    ) -> Property:
        """Создаёт новое пользовательское свойство.
        
        Args:
            name: Название свойства
            property_type: Тип свойства
            show_on_facade: Показывать на фасаде
            multiline: Многострочное поле
            vote_variant: Вариант голосования
            values_type: Тип значений
            colorful: Цветное свойство
            multi_select: Множественный выбор
            data: Дополнительные данные
            formula: Формула для вычисляемых полей
            color: Цвет свойства
            fields_settings: Настройки полей
            
        Returns:
            Property: Созданный объект Property
        """
        payload = {
            "name": name,
            "type": property_type,
            "show_on_facade": show_on_facade,
            "multiline": multiline,
            "vote_variant": vote_variant,
            "values_type": values_type,
            "colorful": colorful,
            "multi_select": multi_select,
            "data": data,
            "formula": formula,
            "color": color,
            "fields_settings": fields_settings
        }
        
        # Удаляем None значения
        payload = {k: v for k, v in payload.items() if v is not None}
        
        data = await self._request("POST", KaitenConfig.ENDPOINT_CUSTOM_PROPERTIES, json=payload)
        return Property(client=self, data=data)
    
    async def update_custom_property(
        self,
        property_id: int,
        name: Optional[str] = None,
        show_on_facade: Optional[bool] = None,
        multiline: Optional[bool] = None,
        vote_variant: Optional[str] = None,
        values_type: Optional[str] = None,
        colorful: Optional[bool] = None,
        multi_select: Optional[bool] = None,
        data: Optional[Dict] = None,
        formula: Optional[str] = None,
        color: Optional[str] = None,
        fields_settings: Optional[List[Dict]] = None
    ) -> Property:
        """Обновляет пользовательское свойство.
        
        Args:
            property_id: ID свойства
            name: Название свойства
            show_on_facade: Показывать на фасаде
            multiline: Многострочное поле
            vote_variant: Вариант голосования
            values_type: Тип значений
            colorful: Цветное свойство
            multi_select: Множественный выбор
            data: Дополнительные данные
            formula: Формула для вычисляемых полей
            color: Цвет свойства
            fields_settings: Настройки полей
            
        Returns:
            Property: Обновлённый объект Property
        """
        payload = {}
        if name is not None:
            payload["name"] = name
        if show_on_facade is not None:
            payload["show_on_facade"] = show_on_facade
        if multiline is not None:
            payload["multiline"] = multiline
        if vote_variant is not None:
            payload["vote_variant"] = vote_variant
        if values_type is not None:
            payload["values_type"] = values_type
        if colorful is not None:
            payload["colorful"] = colorful
        if multi_select is not None:
            payload["multi_select"] = multi_select
        if data is not None:
            payload["data"] = data
        if formula is not None:
            payload["formula"] = formula
        if color is not None:
            payload["color"] = color
        if fields_settings is not None:
            payload["fields_settings"] = fields_settings
        
        data = await self._request("PATCH", f"{KaitenConfig.ENDPOINT_CUSTOM_PROPERTIES}/{property_id}", json=payload)
        return Property(client=self, data=data)
    
    async def delete_custom_property(self, property_id: int) -> bool:
        """Удаляет пользовательское свойство.
        
        Args:
            property_id: ID свойства
            
        Returns:
            bool: True если удаление прошло успешно
        """
        await self._request("DELETE", f"{KaitenConfig.ENDPOINT_CUSTOM_PROPERTIES}/{property_id}")
        return True

    # === ЗНАЧЕНИЯ ВЫБОРА КАСТОМНЫХ СВОЙСТВ ===
    
    async def get_property_select_values(
        self,
        property_id: int,
        v2_select_search: Optional[bool] = None,
        query: Optional[str] = None,
        order_by: Optional[str] = None,
        ids: Optional[List[int]] = None,
        conditions: Optional[List[str]] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает список значений выбора для кастомного свойства.
        
        Args:
            property_id: ID кастомного свойства
            v2_select_search: Включает дополнительную фильтрацию
            query: Фильтр по значению выбора (работает только если v2_select_search=True)
            order_by: Поле для сортировки (работает только если v2_select_search=True)
            ids: Массив ID для фильтрации (работает только если v2_select_search=True)
            conditions: Массив условий для фильтрации (работает только если v2_select_search=True)
            offset: Количество записей для пропуска (работает только если v2_select_search=True)
            limit: Максимальное количество значений в ответе (работает только если v2_select_search=True)
        
        Returns:
            Список значений выбора
        """
        params = {}
        
        if v2_select_search is not None:
            params['v2_select_search'] = v2_select_search
        if query is not None:
            params['query'] = query
        if order_by is not None:
            params['order_by'] = order_by
        if ids is not None:
            params['ids'] = ','.join(map(str, ids))
        if conditions is not None:
            params['conditions'] = ','.join(conditions)
        if offset is not None:
            params['offset'] = offset
        if limit is not None:
            params['limit'] = limit
        
        endpoint = f"{KaitenConfig.ENDPOINT_CUSTOM_PROPERTIES}/{property_id}/select-values"
        response = await self._request('GET', endpoint, params=params)
        return response if isinstance(response, list) else response.get('items', [])
    
    async def get_property_select_value(
        self,
        property_id: int,
        value_id: int
    ) -> Dict[str, Any]:
        """
        Получает значение выбора кастомного свойства по ID.
        
        Args:
            property_id: ID кастомного свойства
            value_id: ID значения выбора
        
        Returns:
            Значение выбора
        """
        endpoint = f"{KaitenConfig.ENDPOINT_CUSTOM_PROPERTIES}/{property_id}/select-values/{value_id}"
        return await self._request('GET', endpoint)
    
    async def create_property_select_value(
        self,
        property_id: int,
        value: str,
        color: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Создаёт новое значение выбора для кастомного свойства.
        
        Args:
            property_id: ID кастомного свойства
            value: Значение выбора (от 1 до 128 символов)
            color: Цвет значения выбора (None для значения без цвета)
        
        Returns:
            Созданное значение выбора
        """
        data = {'value': value}
        
        if color is not None:
            data['color'] = color
        
        endpoint = f"{KaitenConfig.ENDPOINT_CUSTOM_PROPERTIES}/{property_id}/select-values"
        return await self._request('POST', endpoint, json=data)
    
    async def update_property_select_value(
        self,
        property_id: int,
        value_id: int,
        value: Optional[str] = None,
        color: Optional[int] = None,
        condition: Optional[str] = None,
        sort_order: Optional[float] = None,
        deleted: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Обновляет значение выбора кастомного свойства.
        
        Args:
            property_id: ID кастомного свойства
            value_id: ID значения выбора
            value: Новое значение (от 1 до 128 символов)
            color: Новый цвет (None для удаления цвета)
            condition: Условие значения выбора ('active' или 'inactive')
            sort_order: Позиция (минимум 0)
            deleted: Условие удаления значения выбора
        
        Returns:
            Обновлённое значение выбора
        """
        data = {}
        
        if value is not None:
            data['value'] = value
        if color is not None:
            data['color'] = color
        if condition is not None:
            data['condition'] = condition
        if sort_order is not None:
            data['sort_order'] = sort_order
        if deleted is not None:
            data['deleted'] = deleted
        
        endpoint = f"{KaitenConfig.ENDPOINT_CUSTOM_PROPERTIES}/{property_id}/select-values/{value_id}"
        return await self._request('PATCH', endpoint, json=data)
    
    async def delete_property_select_value(
        self,
        property_id: int,
        value_id: int
    ) -> Dict[str, Any]:
        """
        Удаляет значение выбора кастомного свойства.
        
        Args:
            property_id: ID кастомного свойства
            value_id: ID значения выбора
        
        Returns:
            Удалённое значение выбора
        """
        endpoint = f"{KaitenConfig.ENDPOINT_CUSTOM_PROPERTIES}/{property_id}/select-values/{value_id}"
        return await self._request('DELETE', endpoint)

    # === КАСТОМНЫЕ СВОЙСТВА КАРТОЧЕК ===
    
    async def get_card_properties_values(self, card_id: int) -> Dict[str, Any]:
        """
        Получает значения кастомных свойств карточки.
        
        Args:
            card_id: ID карточки
        
        Returns:
            Dict с значениями кастомных свойств
        """
        # Используем карточку с дополнительными полями для получения кастомных свойств
        params = {'additional_card_fields': 'properties'}
        card_data = await self._request('GET', f'{KaitenConfig.ENDPOINT_CARDS}/{card_id}', params=params)
        
        # Возвращаем только кастомные свойства
        return card_data.get('properties', {})
    
    async def set_card_property_value(
        self, 
        card_id: int, 
        property_id: int, 
        value: Any
    ) -> Dict[str, Any]:
        """
        Устанавливает значение кастомного свойства карточки через обновление карточки.
        
        Args:
            card_id: ID карточки
            property_id: ID кастомного свойства
            value: Значение для установки
        
        Returns:
            Dict с результатом операции
        """
        # В Kaiten API кастомные свойства обновляются через обновление карточки
        # с форматом id_{propertyId}:value
        return await self.update_card(card_id, 
                        properties={
                            f"id_{property_id}": value}
                        )
    
    async def update_card_property_value(
        self, 
        card_id: int, 
        property_id: int, 
        value: Any
    ) -> Dict[str, Any]:
        """
        Обновляет значение кастомного свойства карточки.
        Алиас для set_card_property_value.
        
        Args:
            card_id: ID карточки
            property_id: ID кастомного свойства
            value: Новое значение
        
        Returns:
            Dict с результатом операции
        """
        return await self.set_card_property_value(card_id, property_id, value)
    
    async def delete_card_property_value(self, card_id: int, property_id: int) -> bool:
        """
        Удаляет значение кастомного свойства карточки.
        
        Args:
            card_id: ID карточки
            property_id: ID кастомного свойства
        
        Returns:
            True если удаление прошло успешно
        """
        # Удаление = установка значения в null
        await self.set_card_property_value(card_id, 
                                           property_id, None)
        return True

    # === ЧЕКИСТЫ ===
    
    async def get_card_checklists(self, card_id: int) -> List[Checklist]:
        """
        Получает все чек-листы карточки.
        
        Поскольку в API Kaiten нет прямого эндпоинта для получения всех чек-листов карточки,
        мы получаем карточку с дополнительными полями и извлекаем чек-листы из её данных.
        
        Args:
            card_id: ID карточки
        
        Returns:
            Список чек-листов карточки
        """
        # Получаем карточку с дополнительными полями, включая чек-листы
        params = {'additional_card_fields': 'checklists'}
        card_data = await self._request('GET', f'{KaitenConfig.ENDPOINT_CARDS}/{card_id}', params=params)
        
        # Извлекаем чек-листы из данных карточки
        checklists_data = card_data.get('checklists', [])
        
        # Добавляем card_id к каждому чек-листу
        for checklist_data in checklists_data:
            checklist_data['card_id'] = card_id
        
        return [Checklist(self, checklist_data) for checklist_data in checklists_data]
    
    async def get_checklist(self, card_id: int, checklist_id: int) -> Checklist:
        """
        Получает чек-лист по ID.
        
        Args:
            card_id: ID карточки
            checklist_id: ID чек-листа
        
        Returns:
            Объект чек-листа
        """
        endpoint = KaitenConfig.ENDPOINT_CARD_CHECKLISTS.format(card_id=card_id)
        data = await self._request('GET', f'{endpoint}/{checklist_id}')
        data['card_id'] = card_id
        return Checklist(self, data)
    
    async def create_checklist(
        self,
        card_id: int,
        name: str,
        sort_order: Optional[float] = None,
        items_source_checklist_id: Optional[int] = None,
        exclude_item_ids: Optional[List[int]] = None,
        source_share_id: Optional[int] = None
    ) -> Checklist:
        """
        Создает новый чек-лист в карточке.
        
        Args:
            card_id: ID карточки
            name: Название чек-листа
            sort_order: Позиция чек-листа
            items_source_checklist_id: ID чек-листа для копирования элементов
            exclude_item_ids: ID элементов для исключения при копировании
            source_share_id: ID шаблона чек-листа
        
        Returns:
            Созданный чек-лист
        """
        data = {'name': name}
        
        if sort_order is not None:
            data['sort_order'] = sort_order
        if items_source_checklist_id is not None:
            data['items_source_checklist_id'] = items_source_checklist_id
        if exclude_item_ids is not None:
            data['exclude_item_ids'] = exclude_item_ids
        if source_share_id is not None:
            data['source_share_id'] = source_share_id
        
        endpoint = KaitenConfig.ENDPOINT_CARD_CHECKLISTS.format(card_id=card_id)
        checklist_data = await self._request('POST', endpoint, json=data)
        checklist_data['card_id'] = card_id
        return Checklist(self, checklist_data)
    
    async def update_checklist(
        self,
        card_id: int,
        checklist_id: int,
        name: Optional[str] = None,
        sort_order: Optional[float] = None,
        move_to_card_id: Optional[int] = None
    ) -> Checklist:
        """
        Обновляет чек-лист.
        
        Args:
            card_id: ID карточки
            checklist_id: ID чек-листа
            name: Новое название
            sort_order: Новая позиция
            move_to_card_id: ID карточки для перемещения чек-листа
        
        Returns:
            Обновленный чек-лист
        """
        data = {}
        if name is not None:
            data['name'] = name
        if sort_order is not None:
            data['sort_order'] = sort_order
        if move_to_card_id is not None:
            data['card_id'] = move_to_card_id
        
        endpoint = KaitenConfig.ENDPOINT_CARD_CHECKLISTS.format(card_id=card_id)
        checklist_data = await self._request('PATCH', f'{endpoint}/{checklist_id}', json=data)
        checklist_data['card_id'] = move_to_card_id if move_to_card_id else card_id
        return Checklist(self, checklist_data)
    
    async def delete_checklist(self, card_id: int, checklist_id: int) -> bool:
        """
        Удаляет чек-лист из карточки.
        
        Args:
            card_id: ID карточки
            checklist_id: ID чек-листа
        
        Returns:
            True если удаление прошло успешно
        """
        endpoint = KaitenConfig.ENDPOINT_CARD_CHECKLISTS.format(card_id=card_id)
        await self._request('DELETE', f'{endpoint}/{checklist_id}')
        return True
    
    # === ЭЛЕМЕНТЫ ЧЕКИСТОВ ===
    
    async def add_checklist_item(
        self,
        card_id: int,
        checklist_id: int,
        text: str,
        sort_order: Optional[float] = None,
        checked: Optional[bool] = None,
        due_date: Optional[str] = None,
        responsible_id: Optional[int] = None
    ) -> ChecklistItem:
        """
        Добавляет элемент в чек-лист.
        
        Args:
            card_id: ID карточки
            checklist_id: ID чек-листа
            text: Текст элемента
            sort_order: Позиция элемента
            checked: Состояние элемента (отмечен/не отмечен)
            due_date: Срок выполнения в формате YYYY-MM-DD
            responsible_id: ID ответственного пользователя
        
        Returns:
            Созданный элемент чек-листа
        """
        data = {'text': text}
        
        if sort_order is not None:
            data['sort_order'] = sort_order
        if checked is not None:
            data['checked'] = checked
        if due_date is not None:
            data['due_date'] = due_date
        if responsible_id is not None:
            data['responsible_id'] = responsible_id
        
        endpoint = KaitenConfig.ENDPOINT_CHECKLIST_ITEMS.format(
            card_id=card_id, 
            checklist_id=checklist_id
        )
        item_data = await self._request('POST', endpoint, json=data)
        
        # Добавляем контекстную информацию
        item_data['card_id'] = card_id
        item_data['checklist_id'] = checklist_id
        
        return ChecklistItem(self, item_data)
    
    async def update_checklist_item(
        self,
        card_id: int,
        checklist_id: int,
        item_id: int,
        text: Optional[str] = None,
        sort_order: Optional[float] = None,
        checklist_id_new: Optional[int] = None,
        checked: Optional[bool] = None,
        due_date: Optional[str] = None,
        responsible_id: Optional[int] = None
    ) -> ChecklistItem:
        """
        Обновляет элемент чек-листа.
        
        Args:
            card_id: ID карточки
            checklist_id: ID чек-листа
            item_id: ID элемента
            text: Новый текст элемента
            sort_order: Новая позиция элемента
            checklist_id_new: ID нового чек-листа для перемещения
            checked: Новое состояние элемента
            due_date: Новый срок выполнения
            responsible_id: ID нового ответственного (None для удаления)
        
        Returns:
            Обновленный элемент чек-листа
        """
        data = {}
        if text is not None:
            data['text'] = text
        if sort_order is not None:
            data['sort_order'] = sort_order
        if checklist_id_new is not None:
            data['checklist_id'] = checklist_id_new
        if checked is not None:
            data['checked'] = checked
        if due_date is not None:
            data['due_date'] = due_date
        if responsible_id is not None:
            data['responsible_id'] = responsible_id
        
        endpoint = KaitenConfig.ENDPOINT_CHECKLIST_ITEMS.format(
            card_id=card_id, 
            checklist_id=checklist_id
        )
        item_data = await self._request('PATCH', f'{endpoint}/{item_id}', json=data)
        
        # Добавляем контекстную информацию
        item_data['card_id'] = card_id
        item_data['checklist_id'] = checklist_id_new if checklist_id_new else checklist_id
        
        return ChecklistItem(self, item_data)
    
    async def delete_checklist_item(
        self,
        card_id: int,
        checklist_id: int,
        item_id: int
    ) -> bool:
        """
        Удаляет элемент из чек-листа.
        
        Args:
            card_id: ID карточки
            checklist_id: ID чек-листа
            item_id: ID элемента
        
        Returns:
            True если удаление прошло успешно
        """
        endpoint = KaitenConfig.ENDPOINT_CHECKLIST_ITEMS.format(
            card_id=card_id, 
            checklist_id=checklist_id
        )
        await self._request('DELETE', f'{endpoint}/{item_id}')
        return True
